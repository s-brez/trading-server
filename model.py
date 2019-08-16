from abc import ABC, abstractmethod


class Model(ABC):
    """Abstract base class for trade strategy models."""

    def __init__(self):
        super.__init__()

    def timeframes(self):
        """Return list of operating timeframes."""

        return self.timeframes

    def lookback(self, timeframe: str):
        """Return model's required lookback (number of
        previous bars to analyse)for a given timeframe string."""

        return self.lookback[timeframe]


class TrendFollowing(Model):
    """Core trend-following model."""

    timeframes = [
        "5m", "15m", "30m", "1h", "2h", "3h", "4h",
        "6h", "8h", "12", "1d", "2d", "3d", "7d"]

    # will need to tune each timeframes ideal look back, 20 is placeholder
    lookback = {
        "5m": 20, "15m": 20, "30m": 20,
        "1h": 20, "2h": 20, "3h": 20,
        "4h": 20, "6h": 20, "8h": 20,
        "12": 20, "1d": 20, "2d": 20,
        "3d": 20, "7d": 20, "14d": 20}

    def __init__(self):
        super()
