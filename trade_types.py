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
        self.trade_id = self.set_id(pymongo_db_object)
        self.active = False             # True/False.
        self.venue_count = 0            # Number of venues in use.
        self.instrument_count = 0       # Number of instruments in use.
        self.model = None               # Name of model that triggered trade.
        self.u_pnl = 0                  # Total unrealised pnl.
        self.r_pnl = 0                  # Total realised pnl.
        self.fees = 0                   # Total fees/commisions paid.
        self.exposure = None            # Percentage of capital at risk.

    def set_id(self, db):
        pass

    @abstractmethod
    def calculate_exposure(self):
        pass

    @abstractmethod
    def calculate_fees(self):
        pass


class SingleInstrumentTrade(Trade):
    """
    Models the state of a single-instrument, single venue trade.

    Used when trading a single instrument directionally, with take profit
    and stop loss orders.
    """

    def __init__(self):
        self.logger = logger
        self.type = "SingleInstrumentTrade"
        self.venue_count = 1
        self.instrument_count = 1
        self.venue                      # Exchange or broker traded with.
        self.symbol                     # Instrument ticker code.
        self.position                   # Position object, if positioned.
        self.open_orders                # List of active orders.
        self.filled_orders              # List of filled orders.


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
                 size, value, price, order_type, void_price, trail):
        self.logger = logger
        self.trade_id = trade_id        # Parent trade ID.
        self.position_id = p_id         # Related position ID.
        self.order_id = order_id        # Order ID as used by venue.
        self.direction = direction      # Long or short.
        self.size = size                # Size in local asset/contract.
        self.value = value              # USD value (size * USD xchange rate).
        self.price = price              # Order price.
        self.order_type = order_type    # Limit, market, stop-limit/market, etc
        self.void_price = void_price    # Order invalidation price.
        self.trail = trail              # True or False, only for stops.
