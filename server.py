
from data import Datahandler
from portfolio import Portfolio
from strategy import Strategy
from broker import Broker
from bitmex import Bitmex
from concurrent.futures import ThreadPoolExecutor
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

        self.logger = self.setup_logger()
        if self.live_trading:
            self.exchanges = self.load_exchanges(self.logger)
        self.events = queue.Queue(0)
        self.data = Datahandler(self.exchanges, self.events, self.logger)
        self.broker = Broker(self.exchanges, self.events, self.logger)
        self.portfolio = Portfolio(self.events, self.logger)
        self.strategy = Strategy(self.events, self.logger)
        self.run()

    def run(self):
        """Main event handling loop"""

        # set subclass flags for live or backtesting
        if self.live_trading:
            self.data.set_live_trading(self.live_trading)
            self.broker.set_live_trading(self.live_trading)

        count = 0
        sleep(self.seconds_til_next_minute())

        while True:
            # when live trading, update data in first second of each minute
            if self.live_trading:
                if datetime.datetime.utcnow().second <= 1:
                    # only update data after at least one minute of
                    # data has been collected
                    if count >= 1:
                        self.data.update_market_data()
                        self.clear_event_queue()
                # wait until the next minute begins
                self.seconds_til_next_minute()

            # if backtesting, update date and process events immediately
            elif not self.live_trading:
                self.data.update_market_data()
                self.clear_event_queue()

    def clear_event_queue(self):
        while True:
            if not self.events.empty():
                event = self.events.get_nowait()
            elif self.events.empty():
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

    def setup_logger(self):
        """Create and configure logger"""

        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
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
        return exchanges

    def seconds_til_next_minute(self):
        """ Return number of seconds to next minute."""
        now = datetime.datetime.utcnow().second
        delay = 60 - now
        return delay
