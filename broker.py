class Broker:
    """
    Broker consumes Order events, then executing orders and and places Fill
    events in the event queue post-transaction.
    """

    def __init__(self, exchanges, events, logger):
        self.exchanges = exchanges
        self.events = events
        self.logger = logger

    exchanges = []
    events = object
    logger = object

    def set_live_trading(self, live_trading):
        """
        Set true or false live execution flag
        """
        self.set_live_trading = live_trading
