"""
trading-server is a multi-asset, multi-strategy, event-driven execution
and backtesting platform (OEMS) for trading common markets.

Copyright (C) 2020  Sam Breznikar <sam@sdbgroup.io>

Licensed under GNU General Public License 3.0 or later.

Some rights reserved. See LICENSE.md, AUTHORS.md.
"""

from event_types import OrderEvent, FillEvent
from other_types import Position
import time


class Portfolio:
    """
    Portfolio manages the net holdings for all models, issuing order events
    and reacting to fill events to open and close positions and strategies
    dictate.

    Capital allocations to strategies and risk parameters are defined here.
    """

    MAX_SIMULTANEOUS_POSITIONS = 20
    MAX_CORRELATED_TRADES = 1
    MAX_ACCEPTED_DRAWDOWN = 15          # Percentage as integer.
    RISK_PER_TRADE = 1                  # Percentage as integer OR 'kelly'
    DEFAULT_STOP = 3                    # % stop distance if none provided.

    def __init__(self, exchanges, logger, db_other, db_client, models):
        self.exchanges = exchanges
        self.logger = logger
        self.db_other = db_other
        self.db_client = db_client
        self.models = models

        self.pf = self.load_portfolio()
        self.verify_positions()

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
        Process incoming signal event and adjust postiions accordingly.

        Args:
            events: event queue object.
            event: new market event.

        Returns:
           None.

        Raises:
            None.
        """

        if self.within_risk_limits(event):
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

    def load_portfolio(self, ID=0):
        """
        Load portfolio matching ID from database.
        """

        portfolio = self.db_other['portfolio'].find_one({"id": ID}, {"_id": 0})

        if portfolio:
            return portfolio
        else:
            # Return a default, empty portfolio if no portfolio exists.
            return {
                'id': ID,
                'start_date': int(time.time()),
                'initial_funds': 0,
                'current_value': 0,
                'positions': [],
                'orders': [],
                'model_allocations': {
                    i: (100 / len(self.models)) for i in self.models},
                'risk_per_trade': self.RISK_PER_TRADE,
                'max_correlated_trades': self.MAX_CORRELATED_TRADES,
                'max_accepted_drawdown': self.MAX_ACCEPTED_DRAWDOWN,
                'max_simultaneous_positions': self.MAX_SIMULTANEOUS_POSITIONS,
                'default_stop': self.DEFAULT_STOP}

    def verify_holdings(self):
        """
        Check stored portfolio data matches actual positions.
        """

        # save portfolio to db here, after positions checked.

    def within_risk_limits(self, signal):
        """
        Return true if current holdings are within permissible risk limits.
        """

        # Check if the new signal would breach any risk limits.
        for position in self.pf['positions']:
            pass
