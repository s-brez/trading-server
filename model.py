from abc import ABC, abstractmethod


class Model(ABC):
    """Abstract base class for trade strategy models."""

    def __init__(self):
        super.__init__()

    def get_timeframes(self):
        """Return list of operating timeframes."""

        return self.timeframes

    def get_lookback(self, timeframe: str):
        """Return model's required lookback (number of
        previous bars to analyse) for a given timeframe."""

        return self.lookback[timeframe]


class TrendFollowing(Model):
    """Core trend-following model."""

    timeframes = [
        "5m", "15m", "30m", "1h", "2h", "3h", "4h",
        "6h", "8h", "12", "1d", "2d", "3d", "7d"]

    # need to tune each timeframes ideal look back, 100 is placeholder for now
    lookback = {
        "5m": 100, "15m": 100, "30m": 100, "1h": 100, "2h": 100,
        "3h": 100, "4h": 100, "6h": 100, "8h": 100, "12": 100,
        "1d": 100, "2d": 100, "3d": 100, "7d": 100, "14d": 100, "28d": 100}

    def __init__(self):
        super()
