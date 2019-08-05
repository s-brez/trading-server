from data import Datahandler
from portfolio import Portfolio
from strategy import Strategy
from broker import Broker
from bitmex import Bitmex
from exchange import Exchange # noqa
from concurrent.futures import ThreadPoolExecutor # noqa
from time import sleep
import logging
import queue
import datetime


class Server:
    """Server routes system events amongst various components via a queue in
    an event handling loop. The queue is processed each minute.

    Event loop lifecycle:
        1. A new minute begins - Exchanges parse tick data into 1 min bars.
        2. Datahander wraps new 1 min bars and other data in Market Events.
        3. Datahandler pushes Market Events into event queue.
        4. Market Events consumed by Strategy object.
        5. Strategy creates a Signal event and places it in event queque.
        6. Signal events consumed by Portfolio.
        7. Portfolio creates Order event from Signal, places it in queue.
        8. Broker executes Order events, creates Fill event post-transaction.
        9. Portfolio consumes Fill event, updates values.
       10. Repeat 1-9 until queue empty.
       11. Sleep until current minute elapses."""

    def __init__(self):

        # ********************************************************************
        self.live_trading = True   # set False for backtesting
        # ********************************************************************

        self.log_level = logging.DEBUG
        self.logger = self.setup_logger()

        # don't connect to live data feeds if backtesting
        if self.live_trading:
            self.exchanges = self.load_exchanges(self.logger)
        self.events = queue.Queue(0)
        # self.logger.debug(self.events)

        # worker classes
        self.data = Datahandler(self.exchanges, self.logger)
        self.broker = Broker(self.exchanges, self.events, self.logger)
        self.portfolio = Portfolio(self.events, self.logger)
        self.strategy = Strategy(self.events, self.logger)

        self.run()

    def run(self):
        """Core event handling routine."""

        self.logger.debug("Started event processing loop.")

        self.data.set_live_trading(self.live_trading)
        self.broker.set_live_trading(self.live_trading)

        count = 0
        sleep(self.seconds_til_next_minute())
        while True:
            # when live trading, update data in first second of each minute
            if self.live_trading:
                # only update data after at least one minute of
                # data has been collected
                if count >= 1:
                    self.events = self.data.update_market_data(self.events)
                    # self.logger.debug(self.events)
                    self.clear_event_queue()
                # wait until the next minute begins
                sleep(self.seconds_til_next_minute())
                count += 1
            # if backtesting, update date and process events immediately
            elif not self.live_trading:
                self.events = self.data.update_market_data(self.events)
                self.clear_event_queue()

    def clear_event_queue(self):
        """Route all new events to workers for processing."""

        while True:
            try:
                event = self.events.get(False)
            except queue.Empty:
                self.logger.debug("Event queue empty.")
                break
            else:
                if event is not None:
                    if event.type == "MARKET":
                        self.strategy.parse_data(event)
                    elif event.type == "SIGNAL":
                        self.portfolio.update_signal(event)
                    elif event.type == "ORDER":
                        self.broker.place_order(event)
                    elif event.type == "FILL":
                        self.portfolio.update_fill(event)
                self.events.task_done()

    def setup_logger(self):
        """Create and configure logger"""

        logger = logging.getLogger()
        logger.setLevel(self.log_level)
        ch = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s:%(levelname)s:%(module)s - %(message)s")
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        return logger

    def load_exchanges(self, logger):
        """Create and return a list of all exchange objects"""

        exchanges = []
        exchanges.append(Bitmex(logger))
        self.logger.debug("Initialised exchanges.")
        return exchanges

    def seconds_til_next_minute(self):
        """ Return number of seconds to next minute."""
        now = datetime.datetime.utcnow().second
        delay = 60 - now
        return delay
