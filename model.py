"""
trading-server is a multi-asset, multi-strategy, event-driven execution
and backtesting platform (OEMS) for trading common markets.

Copyright (C) 2020  Sam Breznikar <sam@sdbgroup.io>

Licensed under GNU General Public License 3.0 or later.

Some rights reserved. See LICENSE.md, AUTHORS.md.
"""

from abc import ABC, abstractmethod


class Model(ABC):
    """
    Base class for strategy models.
    """

    def __init__(self):
        super.__init__()

    def timeframes(self):
        """
        Return list of operating timeframes.
        """

        return self.timeframes

    def lookback(self, timeframe: str):
        """
        Return model's required lookback (number of
        previous bars to analyse)for a given timeframe string.
        """

        return self.lookback[timeframe]


class TrendFollowing(Model):
    """
    Core trend-following model.
    """

    timeframes = [
        "5m", "15m", "30m", "1h", "2h", "3h", "4h",
        "6h", "8h", "12", "1d", "2d", "3d", "7d"]

    # Will need to tune each timeframes ideal look back, 100 is placeholder.
    lookback = {
        "5m": 100, "15m": 100, "30m": 100,
        "1h": 100, "2h": 100, "3h": 100,
        "4h": 100, "6h": 100, "8h": 100,
        "12": 100, "1d": 100, "2d": 100,
        "3d": 100, "7d": 100, "14d": 100}


    def __init__(self):
        super()
