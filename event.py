from dateutil import parser
from datetime import datetime


class Event(object):
    """Base class for various system events."""


class MarketEvent(Event):
    """Wrapper for new market data. Consumed by Strategy object to
    produce Signal events."""

    DTFMT = '%Y-%m-%d %H:%M:%S'

    def __init__(self, exchange, bar):
        self.type = 'MARKET'
        self.exchange = exchange
        self.bar = bar

    def __str__(self):
        return "MarketEvent - Exchange: %s, Symbol: %s, TS: %s, Close: %s" % (
            self.exchange, self.bar['symbol'],
            self.get_datetime(), self.bar['close'])

    def get_bar(self):
        return self.bar

    def get_exchange(self):
        return self.exchange

    def get_datetime(self):
        return datetime.fromtimestamp(
            self.bar['timestamp']).strftime(self.DTFMT),


class SignalEvent(Event):
    """A trade signal. Consumed by Portfolio to produce Order events."""

    def __init__(self, symbol, datetime, signal_type):
        self.type = 'SIGNAL'
        self.symbol = symbol            # ticker
        self.datetime = datetime
        self.signal_type = signal_type  # LONG, SHORT


class OrderEvent(Event):
    """Contains order details to be sent to a broker/exchange."""

    def __init__(self, symbol, exchange, order_type, quantity, direction):
        self.type = 'ORDER'
        self.symbol = symbol            # instrument ticker
        self.exchange = exchange        # source exchange
        self.order_type = order_type    # MKT, LMT, SMKT, SLMT
        self.quantity = quantity        # positive integer
        self.direction = direction      # BUY or SELL

    def __str__(self):
        return "OrderEvent - Symbol: %s, Type: %s, Qty: %s, Direction: %s" % (
            self.symbol, self.order_type, self.quantity, self.direction)


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
