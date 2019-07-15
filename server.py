
from data import Datahandler
from portfolio import Portfolio
from strategy import Strategy
from broker import Broker
from bitmex import Bitmex
import logging
import queue
import time


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

    logger = object
    exchanges = []
    events = queue.Queue(0)
    timestep = 60
    data = Datahandler(exchanges, events, logger)
    broker = Broker(exchanges, events, logger)
    portfolio = Portfolio(events, logger)
    strategy = Strategy(events, logger)

    def __init__(self):
        self.logger = self.setup_logger()
        self.exchanges = self.load_exchanges()

    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! #

    live_trading = False                       # set True for live execution

    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! #

    if live_trading:
        data.set_live_trading(True)
        broker.set_live_trading(True)

    # event-handling loop
    while True:
        data.update_bars()
        while True:
            if not events.empty():
                event = events.get_nowait()
            elif events.empty():
                break
            else:
                if event is not None:
                    if event.type == "MARKET":
                        strategy.parse_signal(event)
                    elif event.type == "SIGNAL":
                        portfolio.update_signal(event)
                    elif event.type == "ORDER":
                        broker.place_order(event)
                    elif event.type == "FILL":
                        portfolio.update_fill(event)

        # TODO: sleep for exact time between queue cleared and next minute
        time.sleep(timestep)

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
