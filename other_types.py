"""
trading-server is a multi-asset, multi-strategy, event-driven trade execution
and backtesting platform (OEMS) for trading common markets.

Copyright (C) 2020  Sam Breznikar <sam@sdbgroup.io>
Copyright (C) 2020  Marc Goulding <gouldingmarc@gmail.com>

Licensed under GNU General Public License 3.0 or later.

Some rights reserved. See LICENSE.md, AUTHORS.md.
"""


class Position:
    """
    Models an active position.
    """

    def __init__(self, logger, model, venue, position_id, symbol, direction,
                 leverage, liquidation, size, value, entry_price, entry_type,
                 targets, t_ids, stop_price, stop_trail, s_id, r_pnl, u_pnl,
                 fees):
        self.logger = logger
        self.model = model              # Name of parent model.
        self.venue = venue              # Exchange or broker traded with.
        self.position_id = position_id  # Position id used by trading venue.
        self.symbol = symbol            # Instrument ticker code.
        self.direction = direction      # Long or short.
        self.leverage = leverage        # Leverage in use.
        self.liquidation = liquidation  # Liquidation price.
        self.size = size                # Asset/contract demonination.
        self.value = value              # USD value (size * USD xchange rate).
        self.entry_price = entry_price  # Entry price. Laddered entry if tuple.
        self.entry_type = entry_type    # Order type for entry.
        self.targets = targets          # List of tuples [(price, % to close)]
        self.target_order_ids = t_ids   # Order ID's for take profit orders.
        self.stop_price = stop_price    # Stop loss price.
        self.stop_trail = stop_trail    # True or False.
        self.stop_order_id = o_id       # Order ID for stop order.
        self.r_pnl = r_pnl              # Realised pnl.
        self.u_pnl = u_pnl              # Unrealised pnl.
        self.fees = fees                # Total fees/commisions paid.
        self.exposure = None            # Percentage of capital at risk.

    def calculate_exposure(self):
        pass


class Order:
    """
    Models an active, untriggered order.
    """

    def __init__(self, logger, model, venue, order_id, p_id, direction, size,
                 value, price, order_type, void_price, trail):
        self.logger = logger
        self.model = model              # Name of parent model.
        self.venue = venue              # Exchange or broker traded with.
        self.order_id = order_id        # Order id used by trading venue.
        self.position_id = p_id         # Related position ID.
        self.symbol = symbol            # Instrument ticker code.
        self.direction = direction      # Long or short.
        self.size = size                # Asset/contract denomination.
        self.value = value              # USD value (size * USD xchange rate).
        self.price = price              # Order price
        self.order_type = order_type    # Limit, market, stop-limit/market, etc
        self.void_price = void_price    # Order invalidation price.
        self.trail = trail              # True or False, only for stops.
