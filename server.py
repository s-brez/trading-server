from pymongo import MongoClient, errors
from portfolio import Portfolio
from strategy import Strategy
from threading import Thread
from data import Datahandler
from broker import Broker
from bitmex import Bitmex
from time import sleep
from ui import Shell
import datetime
import pymongo
import logging
import time
import queue


class Server:
    """Server routes system events amongst worker components via a queue in
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
    DB_NAME = 'asset_price_master'
    DB_TIMEOUT_MS = 10
    DIAG_DELAY = 30  # mins between diagnostics

    def __init__(self):
        self.live_trading = True   # set False for backtesting.
        self.log_level = logging.DEBUG
        self.logger = self.setup_logger()

        # Don't connect to live data feeds if backtesting.
        if self.live_trading:
            self.exchanges = self.load_exchanges(self.logger)

        # Connect to database.
        self.db_client = MongoClient(
            self.DB_URL,
            serverSelectionTimeoutMS=self.DB_TIMEOUT_MS)
        self.db = self.db_client[self.DB_NAME]
        self.check_db_connection()

        # Event queue and producer/consumer worker classes.
        self.events = queue.Queue(0)
        self.data = Datahandler(
            self.exchanges, self.logger, self.db, self.db_client)
        self.strategy = Strategy(
            self.exchanges, self.logger, self.db, self.db_client)
        self.portfolio = Portfolio(self.logger)
        self.broker = Broker(self.exchanges, self.logger)

        # UI.
        self.shell = Shell(
            self.logger,
            self.data,
            self.exchanges,
            self.strategy,
            self.portfolio,
            self.broker)

        # Processing performance variables.
        self.start_processing = None
        self.end_processing = None

        self.run()

    def run(self):
        """Core event handling loop."""

        self.data.set_live_trading(self.live_trading)
        self.broker.set_live_trading(self.live_trading)

        # Check data is current, repair if necessary before live trading.
        # No need to do so if backtesting, just use existing stored data.
        if self.live_trading:
            self.data.run_data_diagnostics(1)

        count = 0
        sleep(self.seconds_til_next_minute())
        while True:
            if self.live_trading:
                # Only update data after at least one minute of new data
                # has been collected, datahandler and strategy ready.
                if count >= 1 and self.data.ready:
                    self.start_processing = time.time()
                    self.logger.debug("Started processing events.")
                    # Parse and queue market data (new Market Events)
                    self.events = self.data.update_market_data(self.events)
                    # Data is ready, route events to worker classes
                    self.clear_event_queue()
                    # Check data integrity every 30 mins
                    if (count % self.DIAG_DELAY == 0):
                        thread = Thread(
                            target=self.data.run_data_diagnostics(0))
                        thread.start()
                # Sleep til the next minute begins
                sleep(self.seconds_til_next_minute())
                count += 1
            elif not self.live_trading:
                # Update data w/o delay when backtesting, don't run diagnostics
                self.events = self.data.update_market_data(self.events)
                self.clear_event_queue()

    def clear_event_queue(self):
        """Routes events to worker classes for processing."""

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
                # Store new data now that time-critical work is complete
                self.data.save_new_bars_to_db()
                break
            else:
                if event is not None:
                    count += 1
                    if event.type == "MARKET":
                        self.strategy.parse_data(event)
                    elif event.type == "SIGNAL":
                        self.portfolio.update_signal(event)
                    elif event.type == "ORDER":
                        self.broker.place_order(event)
                    elif event.type == "FILL":
                        self.portfolio.update_fill(event)
                # finished all jobs in queue
                self.events.task_done()

    def setup_logger(self):
        """Create and configure logger"""

        logger = logging.getLogger()
        logger.setLevel(self.log_level)
        log_file = logging.FileHandler('log.log', 'w+')
        formatter = logging.Formatter(
            "%(asctime)s:%(levelname)s:%(module)s - %(message)s")
        log_file.setFormatter(formatter)
        logger.addHandler(log_file)

        # supress requests/urlib3 messages as logging.DEBUG produces messages
        # with every single http request.
        logging.getLogger("urllib3").propagate = False
        requests_log = logging.getLogger("requests")
        requests_log.addHandler(logging.NullHandler())
        requests_log.propagate = False

        return logger

    def load_exchanges(self, logger):
        """Create and return list of all exchange objects"""

        exchanges = []
        exchanges.append(Bitmex(logger))
        self.logger.debug("Initialised exchanges.")
        return exchanges

    def seconds_til_next_minute(self):
        """ Return number of seconds to next minute."""

        now = datetime.datetime.utcnow().second
        delay = 60 - now
        return delay

    def check_db_connection(self):
        """Raise exception if DB connection not active."""

        try:
            time.sleep(self.DB_TIMEOUT_MS)
            self.db_client.server_info()
            self.logger.debug(
                "Connected to " + self.DB_NAME + " at " +
                self.DB_URL + ".")
        except errors.ServerSelectionTimeoutError as e:
            self.logger.debug(
                "Failed to connect to " + self.DB_NAME + " at " +
                self.DB_URL + ".")
            raise Exception()
