from pymongo import MongoClient, errors
from itertools import groupby, count
from event import MarketEvent
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
        self.track_tick_processing_performance(duration)

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

    def track_tick_processing_performance(self, duration):
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
                reports.append(self.get_stored_data_status(
                    exchange, symbol, output))

        # resolve discrepancies in stored data
        self.logger.debug("Fetching missing data.")
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

    def get_stored_data_status(self, exchange, symbol, output=False):
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
        origin_ts = exchange.get_origin_timestamp(symbol)
        
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
            self.logger.info(
                "Exchange & instrument:.........." +
                exchange.get_name() + ":" + str(symbol))
            self.logger.info(
                "Total required bars:............" + str(len(required)))
            self.logger.info(
                "Total locally stored bars:......" + str(total_stored))
            self.logger.info(
                    "Total null-value bars:.........." + str(len(null_bars)))            
            self.logger.info(
                "Total missing bars:............." + str(len(gaps)))

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

    def backfill_bulk(self, report):
        """Get and store missing bars between origin and oldest timestamps.
        Use this once to get the bulk of historic data, then fill small gaps
        with backfill_gaps() intermittently intradaily or as required."""

        if report['origin_ts'] < report['oldest_ts']:

            # Determine poll sizing accounting for max_bin_size. Split
            # polling into a large batch of polls and then a final poll.
            required = int((report['oldest_ts'] - report['origin_ts']) / 60)
            final_poll_size = required % report['max_bin_size']
            total_polls_batch = int((
                (required - final_poll_size) / report['max_bin_size']))

            start = report['origin_ts']
            step = report['max_bin_size'] * 60

            delay = 1  # wait time before attmepting to re-poll after error
            stagger = 2  # delay co-efficient
            timeout = 10  # number of times to repoll before exception raised.

            # poll exchange REST endpoint for first bulk batch missing bars
            bars_to_store = []
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
        as a data QA measure for patching missing locally saved data incurred
        from server downtime."""

        # sort timestamps into sequential bins (to reduce # of polls)
        if len(report['gaps']) != 0:
            bins = [
                list(g) for k, g in groupby(
                    sorted(report['gaps']),
                    key=lambda n, c=count(0, 60): n - next(c))]

            # if any bins > max_bin_size, split them into smaller bins.
            # takes the old list
            bins = self.split_oversize_bins(bins, report['max_bin_size'])

            delay = 1  # wait time before attmepting to re-poll after error
            stagger = 2  # delay co-efficient
            timeout = 10  # number of times to repoll before exception raised.

            # poll exchange REST endpoint for replacement bars
            bars_to_store = []
            for i in bins:
                try:
                    bars = report['exchange'].get_bars_in_period(
                        report['symbol'], i[0], len(i))
                    for bar in bars:
                        bars_to_store.append(bar)
                    stagger = 2  # reset stagger to base after successful poll
                    time.sleep(stagger + 1)
                except Exception as e:
                    # retry polling with an exponential delay after each error
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
                        # Skip duplicates that exist in DB.
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
                raise Exception(
                    "Fetched bars do not match missing timestamps.")
        else:
            # Return false if there is no missing data.
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

    def set_live_trading(self, live_trading):
        """Set true or false live execution flag"""

        self.live_trading = live_trading

    def get_total_instruments(self):
        """Return total number of monitored instruments."""

        total = 0
        for exchange in self.exchanges:
            total += len(exchange.symbols)
        return total

    def get_instrument_symbols(self):
        """Return a list containing all instrument symbols."""

        instruments = []
        for exchange in self.exchanges:
            for symbol in exchange.get_symbols():
                instruments.append(
                    exchange.get_name() + "-" + symbol)
        return instruments