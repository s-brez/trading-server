"""
trading-server is a multi-asset, multi-strategy, event-driven execution
and backtesting platform (OEMS) for trading common markets.

Copyright (C) 2020  Sam Breznikar <sam@sdbgroup.io>

Licensed under GNU General Public License 3.0 or later.

Some rights reserved. See LICENSE.md, AUTHORS.md.
"""

from pymongo import MongoClient, errors
from multiprocessing import Process
from portfolio import Portfolio
from strategy import Strategy
from threading import Thread
from data import Datahandler
from broker import Broker
from bitmex import Bitmex
from time import sleep
import pymongo
import time
import logging
import queue
import datetime


class Server:
    """
    Server routes system events amongst worker components via a queue in
    an event handling loop. The queue is processed at the start of each minute.

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

    # Mins between recurring data diagnostics.
    DIAG_DELAY = 45

    def __init__(self):

        # Set False for forward testing.
        self.live_trading = True

        self.log_level = logging.DEBUG
        self.logger = self.setup_logger()

        self.exchanges = self.load_exchanges(self.logger)

        # Database.
        self.db_client = MongoClient(
            self.DB_URL,
            serverSelectionTimeoutMS=self.DB_TIMEOUT_MS)

        # Price data database.
        self.db_prices = self.db_client[self.DB_PRICES]

        # Non-price data database.
        self.db_other = self.db_client[self.DB_OTHER]

        self.check_db_connection()

        # Main event queue.
        self.events = queue.Queue(0)

        # Producer/consumer worker classes.
        self.data = Datahandler(self.exchanges, self.logger, self.db_prices,
                                self.db_client)

        self.strategy = Strategy(self.exchanges, self.logger, self.db_prices,
                                 self.db_other, self.db_client)

        self.portfolio = Portfolio(self.exchanges, self.logger, self.db_other,
                                   self.db_client, self.strategy.models)

        self.broker = Broker(self.exchanges, self.logger, self.portfolio,
                             self.db_other, self.db_client, self.live_trading)

        # Processing performance tracking variables.
        self.start_processing = None
        self.end_processing = None
        self.cycle_count = 0

        self.run()

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

                    # Parse and queue market data (new Market Events).
                    self.events = self.data.update_market_data(self.events)

                    # Market data is ready, route events to worker classes.
                    self.clear_event_queue()

                    # Run diagnostics at 3 and 7 mins to be sure missed
                    # bars are rectified before ongoing system operation.
                    if (self.cycle_count == 2 or self.cycle_count == 5):
                        thread = Thread(
                            target=lambda: self.data.run_data_diagnostics(0))
                        thread.daemon = True
                        thread.start()

                    # Check data integrity periodically thereafter.
                    if (self.cycle_count % self.DIAG_DELAY == 0):
                        thread = Thread(
                            target=lambda: self.data.run_data_diagnostics(0))
                        thread.daemon = True
                        thread.start()

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
                self.logger.debug(
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
                        self.logger.debug("Processing signal event.")
                        self.portfolio.new_signal(self.events, event)

                    # Order placement and Fill Event generation.
                    elif event.type == "ORDER":
                        self.logger.debug("Processing order event.")
                        self.broker.new_order(self.events, event)

                    # Final portolio update.
                    elif event.type == "FILL":
                        self.logger.debug("Processing fill event.")
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
            datefmt="%Y-%m-%d %H:%M:%S")
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        # Supress requests/urlib3/connectionpool messages as
        # logging.DEBUG produces messages with each https request.
        logging.getLogger("urllib3").propagate = False
        requests_log = logging.getLogger("requests")
        requests_log.addHandler(logging.NullHandler())
        requests_log.propagate = False

        return logger

    def load_exchanges(self, logger):
        """
        Create and return list of all exchange object.

        Args:
            None.

        Returns:
            exchanges: list of exchange objects.

        Raises:
            None.
        """

        exchanges = []
        exchanges.append(Bitmex(logger))
        self.logger.debug("Initialised exchanges.")

        return exchanges

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

    def check_db_connection(self):
        """
        Raise exception if DB connection not active.

        Args:
            None.

        Returns:
            None.

        Raises:
            Database connection failure error.
        """

        try:
            time.sleep(self.DB_TIMEOUT_MS)
            self.db_client.server_info()
            self.logger.debug(
                "Connected to " + self.DB_PRICES + " at " +
                self.DB_URL + ".")
        except errors.ServerSelectionTimeoutError as e:
            self.logger.debug(
                "Failed to connect to " + self.DB_PRICES + " at " +
                self.DB_URL + ".")
            raise Exception()

        # TODO: Create indexing if not present.
