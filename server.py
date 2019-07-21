
from data import Datahandler
from portfolio import Portfolio
from strategy import Strategy
from broker import Broker
from bitmex import Bitmex
from time import sleep
import logging
import queue
import datetime


class Server:
    """Server routes system events amongst various components via a queue in
    an event handling loop. The queue is cleared once per minute.

    Event loop lifecycle:
        1. Market event created by Datahander and placed in event queue.
        2. Market event consumed by Strategy object.
        3. Strategy creates a Signal event and places it in event queque.
        4. Signal events consumed by Portfolio.
        5. Portfolio creates Order event from Signal, places it in queue.
        6. Broker executes Order events, creates Fill event post-transaction.
        7. Portfolio consumes Fill event, updates values.
        8. Repeat 1-7 until queue empty.
        9. Sleep until next 1 minute bar close,
       10. Repeat. """

    def __init__(self):
        self.logger = self.setup_logger()
        self.exchanges = self.load_exchanges()
        self.events = queue.Queue(0)
        self.timestep = 60
        self.data = Datahandler(self.exchanges, self.events, self.logger)
        self.broker = Broker(self.exchanges, self.events, self.logger)
        self.portfolio = Portfolio(self.events, self.logger)
        self.strategy = Strategy(self.events, self.logger)
        self.live_trading = False   # set True for live execution
        self.run()

    def run(self):
        # set component flags for live or historic data feeds
        if self.live_trading:
            self.data.set_live_trading(self.live_trading)
            self.broker.set_live_trading(self.live_trading)
        # event-handling loop
        while True:
            self.data.update_market_data()
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

            # sleep until 1 second before the next minute starts
            now = datetime.datetime.utcnow().second
            delay = 60 - now - 1
            sleep(delay)

    def setup_logger(self):
        """Create and configure logger to output to terminal"""

        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        ch = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        return logger

    def load_exchanges(self):
        """Create and return a list of all exchange objects"""

        exchanges = []
        exchanges.append(Bitmex(self.logger))
        return exchanges
