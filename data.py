"""
trading-server is a multi-asset, multi-strategy, event-driven execution
and backtesting platform (OEMS) for trading common markets.

Copyright (C) 2020  Sam Breznikar <sam@sdbgroup.io>

Licensed under GNU General Public License 3.0 or later.

Some rights reserved. See LICENSE.md, AUTHORS.md.
"""

from event import MarketEvent
from itertools import groupby, count

from pymongo import MongoClient, errors
from itertools import groupby, count
from event import MarketEvent
import pymongo
import queue
import time
import json


class Datahandler:
    """
    Datahandler wraps exchange data and locally stored data with Market
    events and adds it to the event queue as each timeframe period elapses.

    Market events are created from either live or stored data (depending on
    if backtesting or live trading) and pushed to the event queue for the
    Strategy object to consume.
    """

    def __init__(self, exchanges, logger, db, db_client):
        self.exchanges = exchanges
        self.logger = logger
        self.db = db
        self.db_client = db_client
        self.db_collections = {
            i.get_name(): db[i.get_name()] for i in self.exchanges}
        self.live_trading = False
        self.ready = False
        self.total_instruments = self.get_total_instruments()
        self.bars_save_to_db = queue.Queue(0)

        # Data processing performance tracking variables.
        self.parse_count = 0
        self.total_parse_time = 0
        self.mean_parse_time = 0
        self.std_dev_parse_time = 0
        self.var_parse_time = 0

    def update_market_data(self, events):
        """
        Pushes new market events to the event queue.

        Args:
            events: empty event queue object.
        Returns:
            events: event queue object filled with new market events.
        Raises:
            None.
        """

        if self.live_trading:
            market_data = self.get_new_data()

        else:
            market_data = self.get_historic_data()

        for event in market_data:
            events.put(event)

        return events

    def get_new_data(self):
        """
        Return a list of market events (new bars) for all symbols from
        all exchanges for the just-elapsed time period. Add new bar data
        to queue for storage in DB, after current minutes cycle completes.

        Logs parse time for tick processing.

        Args:
            None.
        Returns:
            new_market_events: list containing new market events.
        Raises:
            None.
        """

        # Record tick parse performance.
        self.logger.debug("Started parsing new ticks.")
        start_parse = time.time()
        for exchange in self.exchanges:
            exchange.parse_ticks()
        end_parse = time.time()
        duration = round(end_parse - start_parse, 5)

        self.logger.debug(
            "Parsed " + str(self.total_instruments) +
            " instruments' ticks in " + str(duration) + " seconds.")
        self.track_tick_processing_performance(duration)

        # Wrap new 1 min bars in market events.
        new_market_events = []
        for exchange in self.exchanges:
            bars = exchange.get_new_bars()

            for symbol in exchange.get_symbols():

                for bar in bars[symbol]:
                    event = MarketEvent(exchange, bar)
                    new_market_events.append(event)

                    # Add bars to save-to-db-later queue.
                    # TODO: store bars concurrently in a separate process.
                    self.bars_save_to_db.put(event)

        return new_market_events

    def get_historic_data(self):
        """
        Return a list of market events (historic bars) from
        locally stored data. Used when backtesting.

        Args:
            None.
        Returns:
            historic_market_events: list containing historic market events.
        Raises:
            None.
        """

        historic_market_events = []

        # TODO: Needs completing.

        return historic_market_events

    def track_tick_processing_performance(self, duration):
        """
        Track tick processing time statistics.

        Args:
            duration: (float) seconds taken to process events.

        Returns:
            None.

        Raises:
            None.
        """

        self.parse_count += 1
        self.total_parse_time += duration
        self.mean_parse_time = self.total_parse_time / self.parse_count

    def run_data_diagnostics(self, output):
        """
        Check each symbol's stored data for completeness, repair/replace
        missing data as needed. Once complete, set ready flag to True.

        Args:
            output: if True, print verbose report. If false, do not print.
        Returns:
            None.
        Raises:
            None.
        """

        # Get a status report for each symbols stored data.
        reports = []
        self.logger.debug("Started data diagnostics.")
        for exchange in self.exchanges:
            for symbol in exchange.get_symbols():
                reports.append(self.data_status_report(
                    exchange, symbol, output))

        # Resolve discrepancies in stored data.
        self.logger.debug("Resolving missing data.")

        for report in reports:
            self.backfill_gaps(report)
            self.replace_null_bars(report)

        self.logger.debug("Data diagnostics complete.")
        self.ready = True

    def save_new_bars_to_db(self):
        """
        Save bars in storage queue to database.

        Args:
            None.
        Returns:
            None.
        Raises:
            pymongo.errors.DuplicateKeyError.
        """

        count = 0
        while True:

            try:
                bar = self.bars_save_to_db.get(False)

            except queue.Empty:
                self.logger.debug(
                    "Wrote " + str(count) + " new bars to database " +
                    str(self.db.name) + ".")
                break

            else:
                if bar is not None:
                    count += 1
                    # store bar in relevant db collection
                    try:
                        self.db_collections[
                            bar.exchange.get_name()].insert_one(bar.get_bar())

                    # Skip duplicates if they exist.
                    except pymongo.errors.DuplicateKeyError:
                        continue

                self.bars_save_to_db.task_done()

    def data_status_report(self, exchange, symbol, output=False):
        """
        Create a stored data completness report for the given instrment.

        Args:
            exchange: exchange object.
            symbol: instrument ticker code (string)
            output: if True, print verbose report. If false, do not print.

        Returns:
            report: dict showing state and completeness of given symbols
            stored data. Contains pertinent timestamps, periods of missing bars
            and other relevant info.

        Raises:
            None.
        """
        current_ts = exchange.previous_minute()
        max_bin_size = exchange.get_max_bin_size()
        result = self.db_collections[exchange.get_name()].find(
            {"symbol": symbol}).sort([("timestamp", pymongo.ASCENDING)])
        total_stored = (
            self.db_collections[exchange.get_name()].count_documents({
                "symbol": symbol}))
        origin_ts = exchange.get_origin_timestamp(symbol)

        # Handle case where there is no existing data (e.g fresh DB).
        if total_stored == 0:
            oldest_ts = current_ts
            newest_ts = current_ts
        else:
            oldest_ts = result[total_stored - 1]['timestamp']
            newest_ts = result[0]['timestamp']

        # Make timestamps sort-agnostic, in case of sorting mixups.
        if oldest_ts > newest_ts:
            oldest_ts, newest_ts = newest_ts, oldest_ts

        # Find gaps (missing bars) in stored data.
        actual = {doc['timestamp'] for doc in result}
        required = {i for i in range(origin_ts, current_ts + 60, 60)}
        gaps = required.difference(actual)

        # Find bars with all null values (if ws drop out, or no trades).
        result = self.db_collections[exchange.get_name()].find({"$and": [
            {"symbol": symbol},
            {"high": None},
            {"low": None},
            {"open": None},
            {"close": None},
            {"volume": 0}]})
        null_bars = [doc['timestamp'] for doc in result]

        if output:
            self.logger.info(
                "Exchange & instrument:......" +
                exchange.get_name() + ":" + str(symbol))
            self.logger.info(
                "Total required bars:........" + str(len(required)))
            self.logger.info(
                "Total locally stored bars:.." + str(total_stored))
            self.logger.info(
                    "Total null-value bars:......" + str(len(null_bars)))
            self.logger.info(
                "Total missing bars:........." + str(len(gaps)))

        return {
            "exchange": exchange,
            "symbol": symbol,
            "origin_ts": origin_ts,
            "oldest_ts": oldest_ts,
            "newest_ts": newest_ts,
            "current_ts": current_ts,
            "max_bin_size": max_bin_size,
            "total_stored": total_stored,
            "total_needed": len(required),
            "gaps": list(gaps),
            "null_bars": null_bars}

    def backfill_gaps(self, report):
        """
        Get and store small bins of missing bars. Intended to be called
        as a data QA measure for patching missing locally saved data incurred
        from server downtime.

        Args:
            exchange: exchange object.
            symbol: instrument ticker code (string)
            output: if True, print verbose report. If false, do not print.

        Returns:
            report: dict showing state and completeness of given symbols
            stored data. Contains pertinent timestamps, periods of missing bars
            and other relevant info.

        Raises:
            Polling timeout error.
            pymongo.errors.DuplicateKeyError.
            Timestamp mismatch error.
        """

        # Sort timestamps into sequential bins (to reduce # of polls).
        poll_count = 1
        if len(report['gaps']) != 0:
            bins = [
                list(g) for k, g in groupby(
                    sorted(report['gaps']),
                    key=lambda n, c=count(0, 60): n - next(c))]

            # If any bins > max_bin_size, split them into smaller bins.
            bins = self.split_oversize_bins(bins, report['max_bin_size'])

            total_polls = str(len(bins))

            delay = 1.5  # Wait time before attmepting to re-poll after error.
            stagger = 2  # Delay co-efficient, increment with each failed poll.
            timeout = 10  # Number of times to repoll before exception raised.

            # Poll venue API for replacement bars.
            bars_to_store = []
            for i in bins:
                # Progress indicator.
                if poll_count:
                    self.logger.debug(
                        "Poll " + str(
                            poll_count) + " of " + total_polls + " " +
                        str(report['symbol']) + " " + str(
                            report['exchange'].get_name()))
                try:
                    bars = report['exchange'].get_bars_in_period(
                        report['symbol'], i[0], len(i))
                    for bar in bars:
                        bars_to_store.append(bar)
                    # Reset stagger to base after successful poll.
                    stagger = 2
                    time.sleep(stagger + 1)

                except Exception as e:
                    # Retry polling with an exponential delay.

                    for i in range(timeout):

                        try:
                            time.sleep(delay + 1)
                            bars = report['exchange'].get_bars_in_period(
                                report['symbol'], i[0], len(i))
                            for bar in bars:
                                bars_to_store.append(bar)
                            stagger = 2
                            break

                        except Exception as e:
                            delay *= stagger
                            if i == timeout - 1:
                                raise Exception("Polling timeout.")
                poll_count += 1

            # Sanity check, check that the retreived bars match gaps.
            # self.logger.debug("Verifying new data...")
            timestamps = [i['timestamp'] for i in bars_to_store]
            timestamps = sorted(timestamps)
            bars = sorted(report['gaps'])

            if timestamps == bars:
                query = {"symbol": report['symbol']}
                doc_count_before = (
                    self.db_collections[report[
                        'exchange'].get_name()].count_documents(query))
                # self.logger.debug("Storing new data...")

                for bar in bars_to_store:
                    try:
                        self.db_collections[
                            report['exchange'].get_name()].insert_one(bar)
                    except pymongo.errors.DuplicateKeyError:
                        # Skip duplicates that exist in DB.
                        self.logger.debug(
                            "Stored duplicate bars exist. Skipping.")
                        continue

                doc_count_after = (
                    self.db_collections[report[
                        'exchange'].get_name()].count_documents(query))

                doc_count = doc_count_after - doc_count_before

                self.logger.debug(
                    "Saved " + str(doc_count) + " missing " +
                    report['symbol'] + " bars.")
                return True

            else:
                # Dump the mismatched bars and timestamps to file if error.
                with open("bars.json", 'w', encoding='utf-8') as f1:
                    json.dump(bars, f, ensure_ascii=False, indent=4)
                with open("timestamps.json", 'w', encoding='utf-8') as f2:
                    json.dump(timestamps, f, ensure_ascii=False, indent=4)

                raise Exception(
                    "Fetched bars do not match missing timestamps.")
        else:
            # Return false if there is no missing data.
            self.logger.debug("No missing data.")
            return False

    def split_oversize_bins(self, original_bins, max_bin_size):
        """
        Splits oversize lists into smaller lists.

        Args:
            original_bins: list of lists (timestamps in bins)
            max_bin_size: int, maximum items per api respons (bin).

        Returns:
            bins: list of lists (timestamps in bins) containing
            the timestamps from orignal_bins, but split into bins
            not larger than max_bin_size.

        Raises:
            None.
        """

        bins = original_bins

        # Identify oversize bins and their positions in original list.
        to_split = []
        indices_to_remove = []
        for i in bins:
            if len(i) > max_bin_size:
                # Save the bins.
                to_split.append(bins.index(i))
                # Save the indices.
                indices_to_remove.append(bins.index(i))

        # Split into smaller bins.
        split_bins = []
        for i in to_split:
            new_bins = [(bins[i])[x:x+max_bin_size] for x in range(
                0, len((bins[i])), max_bin_size)]
            split_bins.append(new_bins)

        final_bins = []
        for i in split_bins:
            for j in i:
                final_bins.append(j)

        # Remove the oversize bins by their indices, add the smaller split bins
        for i in indices_to_remove:
            del bins[i]

        for i in final_bins:
            bins.append(i)

        return bins

    def replace_null_bars(self, report):
        """
        Replace null bars in db with newly fetched ones. Null bar means
        all OHLCV values are None or zero.

        Args:
            report: dict showing state and completeness of given symbols
            stored data. Contains pertinent timestamps, periods of missing bars
            and other relevant info.

        Returns:
            True if all null bars are successfully replaces, False if not.

        Raises:
            Polling timeout error.
            pymongo.errors.DuplicateKeyError.
            Timestamp mismatch error.
        """

        if len(report['null_bars']) != 0:
            # sort timestamps into sequential bins (to reduce polls)
            bins = [
                list(g) for k, g in groupby(
                    sorted(report['null_bars']),
                    key=lambda n, c=count(0, 60): n - next(c))]

            delay = 1  # wait time before attmepting to re-poll after error
            stagger = 2  # delay co-efficient
            timeout = 10  # number of times to repoll before exception raised.

            # poll exchange REST endpoint for missing bars
            bars_to_store = []
            for i in bins:
                try:
                    bars = report['exchange'].get_bars_in_period(
                        report['symbol'], i[0], len(i))
                    for bar in bars:
                        bars_to_store.append(bar)
                    stagger = 2  # reset stagger to base after successful poll
                    time.sleep(stagger)
                except Exception as e:
                    # retry poll with an exponential delay after each error
                    for i in range(timeout):
                        try:
                            time.sleep(delay)
                            bars = report['exchange'].get_bars_in_period(
                                report['symbol'], i[0], len(i))
                            for bar in bars:
                                bars_to_store.append(bar)
                            stagger = 2
                            break
                        except Exception as e:
                            delay *= stagger
                            if i == timeout - 1:
                                raise Exception("Polling timeout.")

            # sanity check, check that the retreived bars match gaps
            timestamps = [i['timestamp'] for i in bars_to_store]
            timestamps = sorted(timestamps)
            bars = sorted(report['null_bars'])
            if timestamps == bars:
                doc_count = 0
                for bar in bars_to_store:
                    try:
                        query = {"$and": [
                            {"symbol": bar['symbol']},
                            {"timestamp": bar['timestamp']}]}
                        new_values = {"$set": {
                            "open": bar['open'],
                            "high": bar['high'],
                            "low": bar['low'],
                            "close": bar['close'],
                            "volume": bar['volume']}}
                        self.db_collections[
                            report['exchange'].get_name()].update_one(
                                query, new_values)
                        doc_count += 1
                    except pymongo.errors.DuplicateKeyError:
                        continue  # skip duplicates if they exist
                doc_count_after = (
                    self.db_collections[report[
                        'exchange'].get_name()].count_documents(
                            {"symbol": report['symbol']}))
                self.logger.debug(
                    "Replaced " + str(doc_count) + " " + report['symbol'] +
                    " null bars.")
                return True
            else:
                raise Exception(
                    "Fetched bars do not match missing timestamps.")
                self.logger.debug(
                    "Bars length: " + str(len(bars)) +
                    " Timestamps length: " + str(len(timestamps)))
        else:
            return False

    def split_oversize_bins(self, original_bins, max_bin_size):
        """Given a list of lists (timestamp bins), if any top-level
        element length > max_bin_size, split that element into
        lists of max_bin_size, remove original element, replace with
        new smaller elements, then return the new modified list."""

        bins = original_bins

        # Identify oversize bins and their positions in original list.
        to_split = []
        indices_to_remove = []
        for i in bins:
            if len(i) > max_bin_size:
                # Save the bins.
                to_split.append(bins.index(i))
                # Save the indices.
                indices_to_remove.append(bins.index(i))

        # split into smaller bins
        split_bins = []
        for i in to_split:
            new_bins = [(bins[i])[x:x+max_bin_size] for x in range(
                0, len((bins[i])), max_bin_size)]
            split_bins.append(new_bins)

        final_bins = []
        for i in split_bins:
            for j in i:
                final_bins.append(j)

        # Remove the oversize bins by their indices, add the smaller split bins
        for i in indices_to_remove:
            del bins[i]

        for i in final_bins:
            bins.append(i)

        return bins

    def get_total_instruments(self):
        """
        Return total number of monitored instruments.

        Args:
            None.
        Returns:
            total: int, all instruments grand total.
        Raises:
            None.
        """

        total = 0
        for exchange in self.exchanges:
            total += len(exchange.symbols)

        return total

    def get_instrument_symbols(self):
        """
        Return a list containing all instrument symbols.

        Args:
            None.
        Returns:
            instruments: list of all instruments ticker codes.
        Raises:
            None.
        """
        instruments = []
        for exchange in self.exchanges:
            for symbol in exchange.get_symbols():
                instruments.append(
                    exchange.get_name() + "-" + symbol)

        return instruments

