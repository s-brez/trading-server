"""
trading-server is a multi-asset, multi-strategy, event-driven execution
and backtesting platform (OEMS) for trading common markets.

Copyright (C) 2020  Sam Breznikar <sam@sdbgroup.io>

Licensed under GNU General Public License 3.0 or later.

Some rights reserved. See LICENSE.md, AUTHORS.md.
"""

from pymongo import MongoClient, errors
from threading import Thread
from time import sleep
import subprocess
import datetime
import logging
import time
import queue

from messaging_clients import Telegram
from portfolio import Portfolio
from strategy import Strategy
from broker import Broker
from bitmex import Bitmex
from data import Datahandler


class Server:
    """
    Server routes system events amongst worker components via a queue in
    an event handling loop. Objects in queue processed at start of each minute.

    Event loop lifecycle:
        1. A new minute begins - Tick data is parsed into 1 min bars.
        2. Datahander wraps new bars and other data in Market Events.
        3. Datahandler pushes Market Events into event queue.
        4. Market Events are consumed by Strategy object.
        5. Strategy creates a Signal event and places it in event queque.
        6. Signal events consumed by Portfolio.
        7. Portfolio creates Order event from Signal, places it in queue.
        8. Broker executes Order events, creates Fill event post-transaction.
        9. Portfolio consumes Fill event, updates values.
       10. Repeat 1-9 until queue empty.
       11. Strategy prepares data for the next minutes calculuations.
       12. Sleep until current minute elapses."""

    DB_URL = 'mongodb://127.0.0.1:27017/'
    DB_PRICES = 'asset_price_master'
    DB_OTHER = 'holdings_trades_signals_master'
    DB_TIMEOUT_MS = 10

    VENUES = ["Binance", "BitMEX"]
    DB_OTHER_COLLS = ['trades', 'portfolio', 'signals']

    # Mins between recurring data diagnostics.
    DIAG_DELAY = 45

    def __init__(self):

        # Set False for forward testing.
        self.live_trading = True

        self.log_level = logging.INFO
        self.logger = self.setup_logger()

        # Check DB state OK before connecting to any exchanges
        self.db_client = MongoClient(
            self.DB_URL,
            serverSelectionTimeoutMS=self.DB_TIMEOUT_MS)
        self.db_prices = self.db_client[self.DB_PRICES]
        self.db_other = self.db_client[self.DB_OTHER]
        self.check_db(self.VENUES)

        self.exchanges = self.exchange_wrappers(self.logger, self.VENUES)
        self.telegram = Telegram(self.logger)

        # Main event queue.
        self.events = queue.Queue(0)

        # Producer/consumer worker classes.
        self.data = Datahandler(self.exchanges, self.logger, self.db_prices,
                                self.db_client)

        self.strategy = Strategy(self.exchanges, self.logger, self.db_prices,
                                 self.db_other, self.db_client)

        self.portfolio = Portfolio(self.exchanges, self.logger, self.db_other,
                                   self.db_client, self.strategy.models,
                                   self.telegram)

        self.broker = Broker(self.exchanges, self.logger, self.portfolio,
                             self.db_other, self.db_client, self.live_trading,
                             self.telegram)

        # Start flask api in separate process
        p = subprocess.Popen(["python", "api.py"])
        self.logger.info("Started flask API.")

        # Processing performance tracking variables.
        self.start_processing = None
        self.end_processing = None
        self.cycle_count = 0

    def run(self):
        """
        Core event handling loop.
        """

        self.data.live_trading = self.live_trading
        self.broker.live_trading = self.live_trading

        # Check data is current, repair if necessary before live trading.
        # No need to do so if backtesting, just use existing stored data.
        if self.live_trading:
            self.data.run_data_diagnostics(1)

        self.cycle_count = 0

        sleep(self.seconds_til_next_minute())

        while True:
            if self.live_trading:

                # Only update data after at least one minute of new data
                # has been collected, plus datahandler and strategy ready.
                if self.cycle_count >= 1 and self.data.ready:
                    self.start_processing = time.time()

                    # Fetch and queue events for processing.
                    self.events = self.broker.check_fills(self.events)
                    self.events = self.data.update_market_data(self.events)
                    self.clear_event_queue()

                    # Run diagnostics at 3 and 7 mins to be sure missed
                    # bars are rectified before ongoing system operation.
                    # if (self.cycle_count == 2 or self.cycle_count == 5):
                    #     thread = Thread(
                    #         target=lambda: self.data.run_data_diagnostics(0))
                    #     thread.daemon = True
                    #     thread.start()

                    # Check data integrity periodically thereafter.
                    # if (self.cycle_count % self.DIAG_DELAY == 0):
                    #     thread = Thread(
                    #         target=lambda: self.data.run_data_diagnostics(0))
                    #     thread.daemon = True
                    #     thread.start()

                # Sleep til the next minute begins.
                sleep(self.seconds_til_next_minute())
                self.cycle_count += 1

            # Update data w/o delay when backtesting, no diagnostics.
            elif not self.live_trading:
                self.events = self.data.update_market_data(self.events)
                self.clear_event_queue()

    def clear_event_queue(self):
        """
        Routes events to worker classes for processing.
        """

        count = 0

        while True:

            try:
                # Get events from queue
                event = self.events.get(False)

            except queue.Empty:
                # Log processing performance stats
                self.end_processing = time.time()
                duration = round(
                    self.end_processing - self.start_processing, 5)
                self.logger.info(
                    "Processed " + str(count) + " events in " +
                    str(duration) + " seconds.")

                # Do non-time critical work now that events are processed.
                self.data.save_new_bars_to_db()
                self.strategy.trim_datasets()
                self.strategy.save_new_signals_to_db()
                self.portfolio.save_new_trades_to_db()

                break

            else:
                if event is not None:
                    count += 1

                    # Signal Event generation.
                    if event.type == "MARKET":
                        self.strategy.new_data(
                            self.events, event, self.cycle_count)
                        self.portfolio.update_price(self.events, event)

                    # Order Event generation.
                    elif event.type == "SIGNAL":
                        self.logger.info("Processing signal event.")
                        self.portfolio.new_signal(self.events, event)

                    # Order placement and Fill Event generation.
                    elif event.type == "ORDER":
                        self.logger.info("Processing order event.")

                        # Do order confirmation and placement in new thread as
                        # confirmation requires user input.
                        thread = Thread(target=lambda: self.broker.new_order(
                                self.events, event))
                        thread.daemon = True
                        thread.start()

                    # Final portolio update.
                    elif event.type == "FILL":
                        self.logger.info("Processing fill event.")
                        self.portfolio.new_fill(event)

                # Finished all jobs in queue.
                self.events.task_done()

    def setup_logger(self):
        """
        Create and configure logger.

        Args:
            None.

        Returns:
            logger: configured logger object.

        Raises:
            None.
        """

        logger = logging.getLogger()
        logger.setLevel(self.log_level)
        ch = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s:%(levelname)s:%(module)s - %(message)s",
            datefmt="%d-%m-%Y %H:%M:%S")
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        # Supress requests/urlib3/connectionpool/telegram messages as
        # logging.DEBUG produces messages with each https request.
        logging.getLogger("urllib3").propagate = False
        logging.getLogger("telegram").propagate = False
        logging.getLogger("connectionpool").propagate = False
        requests_log = logging.getLogger("requests")
        requests_log.addHandler(logging.NullHandler())
        requests_log.propagate = False

        return logger

    def exchange_wrappers(self, logger, op_venues):
        """
        Create and return a list of exchange wrappers.

        Args:
            op_venues: list of exchange/venue names to int.

        Returns:
            exchanges: list of exchange connector objects.

        Raises:
            None.
        """

        # TODO: load exchange wrappers from 'op_venues' list param

        venues = [Bitmex(logger)]
        self.logger.info("Initialised exchange connectors.")

        return venues

    def seconds_til_next_minute(self: int):
        """
        Args:
            None.

        Returns:
            Number of second to next minute (int).

        Raises:
            None.
        """

        now = datetime.datetime.utcnow().second
        delay = 60 - now
        return delay

    def check_db(self, op_venues):
        """
        Check DB connection, set up collections and indexing.

        Args:
            op_venues: list of operating venue names.

        Returns:
            None.

        Raises:
            Database connection failure error.
        """

        try:

            # If no exception, DBs exist
            time.sleep(self.DB_TIMEOUT_MS)
            self.db_client.server_info()
            self.logger.info("Connected to DB client at " + self.DB_URL + ".")

            price_colls = self.db_prices.list_collection_names()
            other_colls = self.db_other.list_collection_names()

            # Check price DB collections and indexing
            for venue_name in op_venues:
                if venue_name not in price_colls:

                    self.logger.info("Creating indexing for " + venue_name +
                                      " in " + self.DB_PRICES + ".")

                    self.db_prices[venue_name].create_index(
                        [('timestamp', 1), ('symbol', 1)],
                        name='timestamp_1_symbol_1',
                        **{'unique': True, 'background': False})

            # Check other DB collections and indexing
            for coll_name in self.DB_OTHER_COLLS:
                if coll_name not in other_colls:

                    self.logger.info("Creating indexing for " + coll_name +
                                      " in " + self.DB_OTHER + ".")

                    # No indexing required for other DB categories (yet)
                    # Add here if required later

        except errors.ServerSelectionTimeoutError as e:
            self.logger.info("Failed to connect to " + self.DB_PRICES +
                              " at " + self.DB_URL + ".")
            raise Exception()

    def db_indices(self):
        """
        Return index information as a list of dicts.

        """

        indices = []
        for venue_name in self.VENUES:
            for name, index_info in self.db_prices[venue_name].index_information().items():
                keys = index_info['key']
                del(index_info['ns'])
                del(index_info['v'])
                del(index_info['key'])
                indices.append({'db': self.DB_PRICES, 'collection': venue_name,
                                'keys': keys, 'info': index_info})

        for coll_name in self.DB_OTHER_COLLS:
            for name, index_info in self.db_prices[coll_name].index_information().items():
                keys = index_info['key']
                del(index_info['ns'])
                del(index_info['v'])
                del(index_info['key'])
                indices.append({'db': self.DB_OTHER, 'collection': coll_name,
                                'keys': keys, 'info': index_info})

        return indices
