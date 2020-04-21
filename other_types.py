"""
trading-server is a multi-asset, multi-strategy, event-driven trade execution
and backtesting platform (OEMS) for trading common markets.

Copyright (C) 2020  Sam Breznikar <sam@sdbgroup.io>
Copyright (C) 2020  Marc Goulding <gouldingmarc@gmail.com>

Licensed under GNU General Public License 3.0 or later.

Some rights reserved. See LICENSE.md, AUTHORS.md.
"""


class Position:

    def __init__(self, logger, venue, position_id, direction, leverage,
                 liquidation, size, value, entry_price, entry_type, targets,
                 stop_price, stop_trail, void_price, r_pnl, u_pnl, fees):
        self.logger = logger
        self.venue = venue              # Exchange or broker traded with.
        self.position_id = position_id  # Id used by trading venue.
        self.symbol = symbol            # Instrument ticker code.
        self.direction = direction      # Long or short.
        self.leverage = leverage        # Leverage in use.
        self.liquidation = liquidation  # Liquidation price.
        self.size = size                # Asset/contract demonination.
        self.value = value              # USD value (size * USD xchange rate).
        self.entry_price = entry_price  # Entry price.
        self.entry_type = entry_type    # Order type for entry
        self.targets = targets          # List of tuples [(price, % to close)]
        self.stop_price = stop_price    # Stop loss price.
        self.stop_trail = stop_trail    # True or False.
        self.void_price = void_price    # Invalidation price, if not entered.
        self.r_pnl = r_pnl              # Realised pnl.
        self.u_pnl = u_pnl              # Unrealised pnl.
        self.fees = fees                # Total fees/commisions paid.
