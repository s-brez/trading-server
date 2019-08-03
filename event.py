class Event(object):
    """Base class for various system events."""


class MarketEvent(Event):
    """Models receival of new market data. Consumed by Strategy
    object to produce Signal events."""

    def __init__(self, exchange, bar):
        self.type = 'MARKET'
        self.exchange = exchange
        self.bar = bar


class SignalEvent(Event):
    """Models the Strategy object sending a trade signal. Consumed
    by Portfolio to produce Order events."""

    def __init__(self, symbol, datetime, signal_type):
        self.type = 'SIGNAL'
        self.symbol = symbol            # ticker
        self.datetime = datetime
        self.signal_type = signal_type  # LONG, SHORT


class OrderEvent(Event):
    """Models a complete order to be sent to a broker/exchange."""

    def __init__(self, symbol, exchange, order_type, quantity, direction):
        self.type = 'ORDER'
        self.symbol = symbol            # instrument ticker
        self.exchange = exchange        # source exchange
        self.order_type = order_type    # MKT, LMT, SMKT, SLMT
        self.quantity = quantity        # positive integer
        self.direction = direction      # BUY or SELL

    def print_order(self):
        print(
            "Order: Symbol=%s, Type=%s, Quantity=%s, Direction=%s" %
            (self.symbol, self.order_type, self.quantity, self.direction))


class FillEvent(Event):
    """Holds transaction data including fees/comissions, slippage, brokerage,
    actual fill price, timestamp, etc.
    """

    def __init__(self, timestamp, symbol, exchange, quantity,
                 direction, fill_cost, commission=None):
        self.type = 'FILL'
        self.timestamp = timestamp     # fill timestamp
        self.symbol = symbol           # instrument ticker
        self.exchange = exchange       # source exchange
        self.quantity = quantity       # position size in asset quantity
        self.direction = direction     # BUY or SELL
        self.fill_cost = fill_cost     # USD value of position

        # use BitMEX taker fees as placeholder
        if commission is None:
            self.commission = (fill_cost / 100) * 0.075
        else:
            self.commission = commission

    def calculate_commission(self):
        """
        TODO: model IC markets fee structuring for all instruments
        """
