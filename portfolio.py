"""
trading-server is a multi-asset, multi-strategy, event-driven execution
and backtesting platform (OEMS) for trading common markets.

Copyright (C) 2020  Sam Breznikar <sam@sdbgroup.io>

Licensed under GNU General Public License 3.0 or later.

Some rights reserved. See LICENSE.md, AUTHORS.md.
"""


class Portfolio:
    """

    """

    def __init__(self, logger):
        self.logger = logger

    def update_price(self, events, event):
        """
        Check price and time updates gainst existing positions.

        Args:
            events: event queue object.
            event: new market event.

        Returns:
           None.

        Raises:
            None.
        """
        pass

    def new_signal(self, events, event):
        """
        Process incoming signal event and generate

        Args:
            events: event queue object.
            event: new market event.

        Returns:
           None.

        Raises:
            None.
        """
        pass

    def fill(self, events, event):
        """
        Process incoming fill event and update position records accordingly.

        Args:
            events: event queue object.
            event: new market event.

        Returns:
           None.

        Raises:
            None.
        """
        pass
