from event import MarketEvent
from pymongo import MongoClient
import queue
import time


class Datahandler:
    """Datahandler wraps exchange data and locally stored data with Market
    events and adds it to the event queue as each timeframe period elapses.

    Market events are created from either live or stored data (depending on
    if backtesting or live trading) and pushed to the event queue for the
    Strategy object to consume."""

    DB_URL = 'mongodb://127.0.0.1:27017/'
    DB_NAME = 'asset_price_master'

    def __init__(self, exchanges, logger):
        self.exchanges = exchanges
        self.logger = logger
        self.live_trading = False
        self.total_instruments = self.get_total_instruments()
        self.bars_save_to_db = queue.Queue(0)

        # db connection
        self.db_client = MongoClient(self.DB_URL)
        self.db = self.db_client[self.DB_NAME]
        self.db_collections = self.get_db_colls(self.db)
        self.check_db_connection()

        # processing performance variables
        self.parse_count = 0
        self.total_parse_time = 0
        self.mean_parse_time = 0
        self.std_dev_parse_time = 0
        self.var_parse_time = 0

    def update_market_data(self, events):
        """Push new market events to the event queue"""

        if self.live_trading:
            market_data = self.get_new_data()
        else:
            market_data = self.get_historic_data()

        for event in market_data:
            events.put(event)

        return events

    def get_new_data(self):
        """Parse all new tick data, then return a list of market events
        (new bars) for all symbols from all exchanges for the just-elapsed
        time period. Add new bar data to queue for storage in DB, after
        currenct processing cycle completes."""

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

    def save_new_bars_to_db(self):
        """Save bars in queue to database. """

        count = 0
        while True:
            try:
                bar = self.bars_save_to_db.get(False)
            except queue.Empty:
                self.logger.debug(
                    "Saved " + str(count) + " new bars to " +
                    self.DB_NAME + ".")
                break
            else:
                if bar is not None:
                    count += 1
                    # store bar in relevant db collection
                    self.db_collections[bar.exchange].insert_one(bar.get_bar())
                # finished all jobs in queue
                self.bars_save_to_db.task_done()

    def backfill_missing_data(self):
        """Fetch and store missing bars for the period betwwen the last
        locally-stored timestamp in db, and the current timestampo of live
        streaming data."""
        

    def set_live_trading(self, live_trading):
        """Set true or false live execution flag"""

        self.live_trading = live_trading

    def get_total_instruments(self):
        """Return total number of monitored instruments."""

        total = 0
        for exchange in self.exchanges:
            total += len(exchange.symbols)
        return total

    def track_performance(self, duration):
        """Track tick processing times and other performance statistics."""

        self.parse_count += 1
        self.total_parse_time += duration
        self.mean_parse_time = self.total_parse_time / self.parse_count

    def get_db_colls(self, db):
        """Return dict containing MongoClient collection objects for
        each exchange. Collections store all rpice data for all instruments
        on that exchange. E.g {"BitMEX" : bitmex_coll_object }"""

        return {i.get_name(): db[i.get_name()] for i in self.exchanges}

    def check_db_connection(self):
        """Raise exception if DB failed to connect."""
        if self.db:
            self.logger.debug(
                "Connected to " + self.DB_NAME + " at " +
                self.DB_URL + ".")
        if not self.db:
            self.logger.debug(
                "Failed to connect to " + self.DB_NAME + " at " +
                self.DB_URL + ".")
            raise Exception()
