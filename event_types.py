"""
trading-server is a multi-asset, multi-strategy, event-driven execution
and backtesting platform (OEMS) for trading common markets.

Copyright (C) 2020  Sam Breznikar <sam@sdbgroup.io>

Licensed under GNU General Public License 3.0 or later.

Some rights reserved. See LICENSE.md, AUTHORS.md.
"""

from dateutil import parser
from datetime import datetime


class Event(object):
    """
    Base class for system events.
    """


class MarketEvent(Event):
    """
    Wrapper for new market data. Consumed by Strategy object to
    produce Signal events.
    """

    # Datetime object format string
    DTFMT = '%Y-%m-%d %H:%M'

    def __init__(self, exchange, bar):
        self.type = 'MARKET'
        self.exchange = exchange
        self.bar = bar

    def __str__(self):
        return str("MarketEvent - Exchange: " + self.exchange.get_name() +
                   " Symbol: " + self.bar['symbol'] + " TS: " +
                   self.get_datetime() + " Close: " + self.bar['close'])

    def get_bar(self):
        return self.bar

    def get_exchange(self):
        return self.exchange

    def get_datetime(self):
        return datetime.fromtimestamp(
            self.bar['timestamp']).strftime(self.DTFMT),


class SignalEvent(Event):
    """
    Entry signal. Consumed by Portfolio to produce Order events.
    """

    def __init__(self, symbol: str, entry_ts, direction: str, timeframe: str,
                 strategy: str, venue, entry_price: float, entry_type: str,
                 targets: list, stop_price: float, void_price: float,
                 trail: bool, note: str, ic=1):

        self.type = 'SIGNAL'
        self.entry_ts = entry_ts        # Entry bar timestamp.
        self.timeframe = timeframe      # Signal timeframe.
        self.strategy = strategy        # Signal strategy name.
        self.venue = venue              # Signal venue name.
        self.symbol = symbol            # Ticker code for instrument.
        self.direction = direction      # LONG or SHORT.
        self.entry_price = entry_price  # Trade entry price.
        self.entry_type = entry_type.upper()  # Order type for entry.
        self.targets = targets          # [(price target, int % to close)]
        self.stop_price = stop_price    # Stop-loss order price.
        self.void_price = void_price    # Invalidation price.
        self.instrument_count = ic      # # of instruments in use.
        self.trail = trail              # True or False for trailing stop.
        self.note = note                # Signal notes.

    def __str__(self):
        return str("Signal Event: " + self.direction + " Symbol: " +
                   self.symbol + " Entry price: " + str(self.entry_price) +
                   " Entry timestamp: " + str(self.entry_ts) + " Timeframe: " +
                   self.timeframe + " Strategy: " + self.strategy +
                   " Venue: " + self.venue.get_name() + " Order type: " +
                   self.entry_type + " Note: " + self.note)

    def get_signal_dict(self):
        return {
            'strategy': self.strategy,
            'venue': self.venue.get_name(),
            'symbol': self.symbol,
            'entry_timestamp': self.entry_ts,
            'direction': self.direction,
            'entry_price': self.entry_price,
            'entry_type': self.entry_type,
            'targets': self.targets,
            'stop_price': self.stop_price,
            'void_price': self.void_price,
            'instrument_count': self.instrument_count,
            'trail': self.trail,
            'note': self.note}

    def inverse_direction(self):
        """
        Return the opposite direction of 'direction' variable.
        """

        if self.direction.upper() == "LONG":
            return "SHORT"
        elif self.direction.upper() == "SHORT":
            return "LONG"


class OrderEvent(Event):
    """
    Contains trade details to be sent to a broker/exchange.
    """

    def __init__(self, order_dict):
        self.type = 'ORDER'
        self.order_dict = order_dict
        self.trade_id = order_dict['trade_id']
        self.order_id = order_dict['order_id']
        self.timestamp = order_dict['timestamp']
        self.avg_fill_price = order_dict['avg_fill_price']
        self.currency = order_dict['currency']
        self.venue_id = order_dict['venue_id']
        self.direction = order_dict['direction']
        self.size = order_dict['size']
        self.price = order_dict['price']
        self.order_type = order_dict['order_type']
        self.metatype = order_dict['metatype']
        self.void_price = order_dict['void_price']
        self.trail = order_dict['trail']
        self.reduce_only = order_dict['reduce_only']
        self.post_only = order_dict['post_only']
        self.batch_size = order_dict['batch_size']
        self.status = order_dict['status']

    def __str__(self):
        return str(" ")

    def get_order_dict(self):
        return self.order_dict


class FillEvent(Event):
    """
    Holds transaction data including fees/commissions, slippage, brokerage,
    actual fill price, timestamp, etc.
    """

    def __init__(self, order_conf):
        self.type = 'FILL'
        self.order_conf = order_conf

        # Use BitMEX taker fees as placeholder.
        self.fees = (order_conf['avg_fill_price'] / 100) * 0.075

    def __str__(self):
        return str(" ")

    def get_order_conf(self):
        return self.order_conf
