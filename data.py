from event import MarketEvent
from itertools import groupby, count
from pymongo import MongoClient, errors
import pymongo
import queue
import time


class Datahandler:
    """Datahandler wraps exchange data and locally stored data with Market
    events and adds it to the event queue as each timeframe period elapses.

    Market events are created from either live or stored data (depending on
    if backtesting or live trading) and pushed to the event queue for the
    Strategy object to consume."""

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

        # processing performance variables
        self.parse_count = 0
        self.total_parse_time = 0
        self.mean_parse_time = 0
        self.std_dev_parse_time = 0
        self.var_parse_time = 0

    def update_market_data(self, events):
        """Push new market events to the event queue."""

        if self.live_trading:
            market_data = self.get_new_data()
        else:
            market_data = self.get_historic_data()

        for event in market_data:
            events.put(event)

        return events

    def get_new_data(self):
        """Return a list of market events (new bars) for all symbols from
        all exchanges for the just-elapsed time period. Add new bar data
        to queue for storage in DB, after current minutes cycle completes."""

        # record bar parse performance
        self.logger.debug("Started parsing new ticks.")
        start_parse = time.time()
        for exchange in self.exchanges:
            exchange.parse_ticks()
        end_parse = time.time()
        duration = round(end_parse - start_parse, 5)

        self.logger.debug(
            "Parsed " + str(self.total_instruments) +
            " instruments' ticks in " + str(duration) + " seconds.")
        self.track_performance(duration)

        # wrap new 1 min bars in market events
        new_market_events = []
        for exchange in self.exchanges:
            bars = exchange.get_new_bars()
            for symbol in exchange.get_symbols():
                for bar in bars[symbol]:
                    event = MarketEvent(exchange.get_name(), bar)
                    new_market_events.append(event)
                    # add bars to save-to-db-later queue
                    # TODO: store new bars concurrently with a processpool
                    self.bars_save_to_db.put(event)
        return new_market_events

    def get_historic_data(self):
        """Return a list of market events (historic bars) from
        locally stored data. Used when backtesting."""

        historic_market_events = []

        return historic_market_events

    def track_performance(self, duration):
        """Track tick processing times and other performance statistics."""

        self.parse_count += 1
        self.total_parse_time += duration
        self.mean_parse_time = self.total_parse_time / self.parse_count

    def run_data_diagnostics(self, output):
        """Check each symbol's stored data for completeness, repair/replace
        missing data as needed. Once complete, set ready flag to True.
        Output parameter set true to print report."""

        # get a status report for each symbols stored data
        reports = []
        self.logger.debug("Started diagnostics.")
        for exchange in self.exchanges:
            for symbol in exchange.get_symbols():
                time.sleep(2)
                reports.append(self.get_status(
                    exchange, symbol, output))

        # resolve discrepancies
        self.logger.debug("Resolving missing data.")
        for report in reports:
            time.sleep(2)
            self.backfill_gaps(report)
            self.replace_null_bars(report)

        self.logger.debug("Data up to date.")
        self.ready = True

    def save_new_bars_to_db(self):
        """Save bars in queue to database."""

        count = 0
        while True:
            try:
                bar = self.bars_save_to_db.get(False)
            except queue.Empty:
                self.logger.debug(
                    "Wrote " + str(count) + " new bars to " +
                    str(self.db.name) + ".")
                break
            else:
                if bar is not None:
                    count += 1
                    # store bar in relevant db collection
                    try:
                        self.db_collections[bar.exchange].insert_one(
                            bar.get_bar())
                    except pymongo.errors.DuplicateKeyError:
                        continue  # skip duplicates if they exist
                # finished all jobs in queue
                self.bars_save_to_db.task_done()

    def get_status(self, exchange, symbol, output=False):
        """ Return dict showing state and completeness of given symbols
        stored data. Contains pertinent timestamps, periods of missing bars and
        other relevant info."""

        current_ts = exchange.previous_minute()
        max_bin_size = exchange.get_max_bin_size()
        result = self.db_collections[exchange.get_name()].find(
            {"symbol": symbol}).sort([("timestamp", pymongo.ASCENDING)])
        total_stored = (
            self.db_collections[exchange.get_name()].count_documents({
                "symbol": symbol}))

        # handle case where there is no existing data (fresh DB)
        if total_stored == 0:
            oldest_ts = current_ts
            newest_ts = current_ts
        else:
            oldest_ts = result[total_stored - 1]['timestamp']
            newest_ts = result[0]['timestamp']

        # make timestamps sort-agnostic, in case of sorting mixups
        if oldest_ts > newest_ts:
            oldest_ts, newest_ts = newest_ts, oldest_ts

        # find gaps in stored data
        actual = {doc['timestamp'] for doc in result}  # actual
        required = {i for i in range(origin_ts, current_ts + 60, 60)}  # reqd
        gaps = required.difference(actual)  # find the difference

        # find bars with all null values (happens sometimes if ws's drop out)
        result = self.db_collections[exchange.get_name()].find({"$and": [
            {"symbol": symbol},
            {"high": None},
            {"low": None},
            {"open": None},
            {"close": None},
            {"volume": 0}]})
        null_bars = [doc['timestamp'] for doc in result]

        if output:
            print(
                "Exchange & instrument:..........",
                exchange.get_name() + ":", symbol)
            # print("Origin (on-exchange) timestamp:.", origin_ts)
            # print("Oldest locally stored timestamp:", oldest_ts)
            # print("Newest locally stored timestamp:", newest_ts)
            # print("Current timestamp:..............", current_ts)
            # print("Max bin size per REST poll:.....", max_bin_size)
            print("Total required bars:............", len(required))
            print("Total locally stored bars:......", total_stored)
            print("Total null-value bars:..........", len(null_bars))
            print("Total missing bars:.............", len(gaps))

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
            "null_bars": null_bars
        }

    def backfill_bulk(self, report):
        """Get and store missing bars between origin and oldest timestamps.
        Use this once to get the bulk of historic data, then fill small gaps
        with backfill_gaps() intermittently intradaily or as required."""

        if report['origin_ts'] < report['oldest_ts']:

            # Determine poll sizing and amounts accounting for max_bin_size.
            # Split polling into a large batch of polls and then a final poll.
            required = int((report['oldest_ts'] - report['origin_ts']) / 60)
            final_poll_size = required % report['max_bin_size']
            total_polls_batch = int((
                (required - final_poll_size) / report['max_bin_size']))

            # poll exchange REST endpoint for first bulk batch missing bars
            start = report['origin_ts']
            step = report['max_bin_size'] * 60
            bars_to_store = []
            delay = 1  # wait time before attmepting to re-poll after error
            stagger = 2  # error delay co-efficient
            timeout = 10
            for i in range(total_polls_batch):
                try:
                    bars = report['exchange'].get_bars_in_period(
                        report['symbol'], start, report['max_bin_size'])
                    for bar in bars:
                        bars_to_store.append(bar)
                    stagger = 2  # reset stagger to base after successful poll
                    start += step  # increment the starting poll timestamp
                    time.sleep(stagger + 1)
                except Exception as e:
                    # retry poll with an exponential delay after each error
                    for i in range(timeout):
                        try:
                            time.sleep(delay)
                            bars = (
                                report['exchange'].get_bars_in_period(
                                    report['symbol'], start,
                                    report['max_bin_size']))
                            for bar in bars:
                                bars_to_store.append(bar)
                            stagger = 2
                            start += step
                            break
                        except Exception as e:
                            delay *= stagger
                            if i == timeout - 1:
                                raise Exception("Polling timeout.")

            # finish with a single poll for final_poll_size number of bars
            for i in range(timeout):
                try:
                    time.sleep(delay)
                    final_bars = report['exchange'].get_bars_in_period(
                        report['symbol'], start, final_poll_size)
                    for bar in final_bars:
                        bars_to_store.append(bar)
                    stagger = 2
                    break
                except Exception as e:
                    # retry poll with an exponential delay after each error
                    delay *= stagger
                    if i == timeout - 1:
                        raise Exception("Polling timeout.")

            # store bars, count how many stores
            query = {"symbol": report['symbol']}
            doc_count_before = (
                self.db_collections[report[
                    'exchange'].get_name()].count_documents(query))
            for bar in bars_to_store:
                try:
                    self.db_collections[report['exchange']].insert_one(
                        bar, upsert=True)
                except pymongo.errors.DuplicateKeyError:
                    continue  # skip duplicates if they exist
            doc_count_after = (
                self.db_collections[report['exchange']].count_documents(query))
            doc_count = doc_count_after - doc_count_before
            self.logger.debug(
                "backfill_bulk() saved " + str(doc_count) + " bars.")
            return True
        return False

    def backfill_gaps(self, report):
        """ Get and store small bins of missing bars. Intended to be called
        multiple times daily as a QA measure for patching small amounts of
        bars missing from locally saved data."""

        if len(report['gaps']) != 0:
            # sort timestamps into sequential bins (to reduce polls)
            bins = [
                list(g) for k, g in groupby(
                    sorted(report['gaps']),
                    key=lambda n, c=count(0, 60): n - next(c))]

            # poll exchange REST endpoint for replacement bars
            bars_to_store = []
            timeout = 10
            delay = 1  # wait time before attmepting to re-poll after error
            for i in bins:
                try:
                    bars = report['exchange'].get_bars_in_period(
                        report['symbol'], i[0], len(i))
                    for bar in bars:
                        bars_to_store.append(bar)
                    stagger = 2  # reset stagger to base after successful poll
                    time.sleep(stagger + 1)
                except Exception as e:
                    # retry poll with an exponential delay after each error
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

            # Sanity check, check that the retreived bars match gaps
            timestamps = [i['timestamp'] for i in bars_to_store]
            timestamps = sorted(timestamps)
            bars = sorted(report['gaps'])
            if timestamps == bars:
                query = {"symbol": report['symbol']}
                doc_count_before = (
                    self.db_collections[report[
                        'exchange'].get_name()].count_documents(query))
                for bar in bars_to_store:
                    try:
                        self.db_collections[
                            report['exchange'].get_name()].insert_one(bar)
                    except pymongo.errors.DuplicateKeyError:
                        continue  # skip duplicates if they exist
                doc_count_after = (
                    self.db_collections[report[
                        'exchange'].get_name()].count_documents(query))
                doc_count = doc_count_after - doc_count_before
                self.logger.debug(
                    "Saved " + str(doc_count) + " missing " +
                    report['symbol'] + " bars.")
                return True
            else:
                raise Exception(
                    "Fetched bars do not match missing timestamps.")
        else:
            self.logger.debug("Data up to date.")
            return False

    def replace_null_bars(self, report):
        """ Replace null bars in db with newly fetched ones. Null bar means
        all OHLCV values are None or zero."""

        if len(report['null_bars']) != 0:
            # sort timestamps into sequential bins (to reduce polls)
            bins = [
                list(g) for k, g in groupby(
                    sorted(report['null_bars']),
                    key=lambda n, c=count(0, 60): n - next(c))]

            # poll exchange REST endpoint for missing bars
            bars_to_store = []
            delay = 2  # wait time before attmepting to re-poll after error
            timeout = 10
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
        else:
            self.logger.debug("Data up to date.")
            return False

    def set_live_trading(self, live_trading):
        """Set true or false live execution flag"""

        self.live_trading = live_trading

    def get_total_instruments(self):
        """Return total number of monitored instruments."""

        total = 0
        for exchange in self.exchanges:
            total += len(exchange.symbols)
        return total
