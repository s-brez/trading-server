"""
trading-server is a multi-asset, multi-strategy, event-driven trade execution
and backtesting platform (OEMS) for trading common markets.

Copyright (C) 2020  Sam Breznikar <sam@sdbgroup.io>
Copyright (C) 2020  Marc Goulding <gouldingmarc@gmail.com>

Licensed under GNU General Public License 3.0 or later.

Some rights reserved. See LICENSE.md, AUTHORS.md.
"""

from abc import ABC, abstractmethod


class Trade(ABC):
    """
    Trade parent class, different types of trade subclasses must inherit this.

    Trade subclasses are used to generalise a collective set of orders and
    positions that make up a trades management from start to finish.

    Child trade classes may be composed of positons and orders across one or
    multiple instruments and venues.
    """

    def __init__(self):
        super.__init__()
        self.trade_id = None            # Must be set before saving to DB.
        self.active = False             # True/False.
        self.venue_count = 0            # Number of venues in use.
        self.instrument_count = 0       # Number of instruments in use.
        self.model = None               # Name of model that triggered trade.
        self.u_pnl = 0                  # Total unrealised pnl.
        self.r_pnl = 0                  # Total realised pnl.
        self.fees = 0                   # Total fees/commisions paid.
        self.exposure = None            # Percentage of capital at risk.

    def set_id(self, db):
        """
        Set ID as the next-highest integer not in use by existing trades.
        """

        result = list(db['trades'].find({}).sort([("trade_id", -1)]))
        trade_id = (int(result[0]['trade_id']) + 1) if result else 1
        self.trade_id = trade_id

        return trade_id

    @abstractmethod
    def get_trade(self):
        """
        Return all trade variables as a dict for DB storage.
        """


class SingleInstrumentTrade(Trade):
    """
    Models the state of a single-instrument, single venue trade.

    Used when trading a single instrument directionally, with take profit
    and stop loss orders.
    """

    def __init__(self, logger, venue, symbol, position=None, open_orders=None,
                 filled_orders=None):
        self.logger = logger
        self.type = "SINGLE_INSTRUMENT"
        self.venue_count = 1
        self.instrument_count = 1
        self.venue = venue                  # Exchange or broker traded with.
        self.symbol = symbol                # Instrument ticker code.
        self.position = position            # Position object, if positioned.
        self.open_orders = open_orders      # List of active orders.
        self.filled_orders = filled_orders  # List of filled orders.

    def get_trade(self):
        return {
            'trade_id': self.trade_id,
            'type': self.type,
            'active': self.active,
            'venue_count': self.venue_count,
            'instrument_count': self.instrument_count,
            'model': self.model,
            'u_pnl': self.u_pnl,
            'r_pnl': self.r_pnl,
            'fees': self.fees,
            'exposure': self.exposure,
            'venue': self.venue,
            'symbol': self.symbol,
            'open_orders': self.open_orders,
            'filled_orders': self.filled}


class Position:
    """
    Models a single active position, as part of a parent trade.
    """

    def __init__(self, logger, trade_id, symbol, direction, leverage,
                 liquidation, size, value, entry_price):
        self.logger = logger
        self.trade_id = trade_id        # Parent trade ID.
        self.direction = direction      # Long or short.
        self.leverage = leverage        # Leverage in use.
        self.liquidation = liquidation  # Liquidation price.
        self.size = size                # Asset/contract demonination.
        self.value = value              # USD value (size * USD xchange rate).
        self.entry_price = entry_price  # Average entry price.


class Order:
    """
    Models a single active, untriggered order, as part of parent trade.
    """

    def __init__(self, logger, trade_id, position_id, order_id, direction,
                 size, price, order_type, void_price, trail,
                 reduce_only, post_only, status="UNFILLED"):
        self.logger = logger
        self.trade_id = trade_id        # Parent trade ID.
        self.position_id = p_id         # Related position ID.
        self.order_id = order_id        # Order ID as used by venue.
        self.direction = direction      # Long or short.
        self.size = size                # Size in local asset/contract.
        self.price = price              # Order price.
        self.order_type = order_type    # LIMIT MARKET STOP_LIMIT STOP_MARKET.
        self.void_price = void_price    # Order invalidation price.
        self.trail = trail              # True or False, only for stops.
        self.reduce_only = reduce_only  # True or False.
        self.post_only = post_only      # True of False.
        self.status = status            # FILLED, UNFILLED, PARTIAL.
