class Broker:
    """Broker consumes Order events, executes orders, then creates and places
    Fill events in the event queue post-transaction."""

    def __init__(self, exchanges, logger):
        self.exchanges = exchanges
        self.logger = logger

    def set_live_trading(self, live_trading):
        self.set_live_trading = live_trading
