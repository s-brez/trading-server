"""
trading-server is a multi-asset, multi-strategy, event-driven execution
and backtesting platform (OEMS) for trading common markets.

Copyright (C) 2020  Sam Breznikar <sam@sdbgroup.io>

Licensed under GNU General Public License 3.0 or later.

Some rights reserved. See LICENSE.md, AUTHORS.md.
"""

from event import OrderEvent, FillEvent


class Portfolio:
    """
    Portfolio manages the net holdings for all models, issuing order events
    and reacting to fill events to open and close positions and strategies
    dictate.
    """

    def __init__(self, exchanges, logger, db_other, db_client):
        self.exchanges = exchanges
        self.logger = logger
        self.db_other = db_other
        self.db_client = db_client

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
        Process incoming signal event and adjust portfolio accordingly.

        Args:
            events: event queue object.
            event: new market event.

        Returns:
           None.

        Raises:
            None.
        """
        pass

    def new_fill(self, events, event):
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
