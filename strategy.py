
from datetime import date, datetime, timedelta
from model import TrendFollowing
import pandas as pd
import calendar


class Strategy:
    """Master control layer, or meta-model, of all individual strategy models.
    Responsible for consuming Market events from the event queue, updating
    strategy models with new data, then generating Signal events. Stores
    working data as dataframes."""

    ALL_TIMEFRAMES = [
        "1m", "2m", "3m", "5m", "15m", "30m", "1h", "2h", "3h", "4h",
        "6h", "8h", "12", "1d", "2d", "3d", "7d", "14d", "28d"]

    TIMEFRAMES_AS_MINUTES = {
        "1m": 1, "2": 2, "3m": 3, "5m": 5, "15m": 15, "30m": 30, "1h": 60,
        "2h": 120, "3h": 180, "4h": 240, "6h": 360, "8h": 480, "12": 720,
        "1d": 1440, "2d": 2880, "3d": 4320, "7d": 10080, "14d": 20160,
        "28d": 40320}

    MINUTE_TIMEFRAMES = [1, 2, 3, 5, 15, 30]
    HOUR_TIMEFRAMES = [1, 2, 3, 4, 6, 8, 12]
    DAY_TIMEFRAMES = [1, 2, 3, 7, 14, 28]

    def __init__(self, exchanges, logger, db, db_client):
        self.exchanges = exchanges
        self.logger = logger
        self.db = db
        self.db_client = db_client
        self.db_collections = {
            i.get_name(): db[i.get_name()] for i in self.exchanges}
        self.dataframes = self.load_dataframes()
        self.models = self.load_models(self.logger)

    def get_relevant_timeframes(self, time):
        """Return a list of timeframes relevant to the just-elapsed period.
        E.g if time has just struck UTC 10:30am the list will contain "1m",
        "3m", "5m", "m15" and "30m" strings. The first minute of a new day or
        week will add daily/weekly/monthly timeframe strings. Timeframes in
        use are 1, 3, 5, 15 and 30 mins, 1, 2, 3, 4, 6, 8 and 12 hours, 1, 2
        and 3 days, weekly and monthly."""

        # check against the previous minute - the just-elapsed period.
        timestamp = time - timedelta(hours=0, minutes=1)
        timeframes = ["1m"]

        for i in self.MINUTE_TIMEFRAMES:
            self.minute_timeframe(i, timestamp, timeframes)

        for i in self.HOUR_TIMEFRAMES:
            self.hour_timeframe(i, timestamp, timeframes)

        for i in self.DAY_TIMEFRAMES:
            self.day_timeframe(i, timestamp, timeframes)

        if (timestamp.minute == 0 and timestamp.hour == 0 and
                calendar.day_name[date.today().weekday()] == "Monday"):
            timeframes.append("1w")

        return timeframes

    def minute_timeframe(self, minutes, timestamp, timeframes):
        for i in range(0, 60, minutes):
            if timestamp.minute == i:
                timeframes.append(f"{minutes}m")

    def hour_timeframe(self, hours, timestamp, timeframes):
        if timestamp.minute == 0 and timestamp.hour % hours == 0:
            timeframes.append(f"{hours}h")

    def day_timeframe(self, days, timestamp, timeframes):
        if (timestamp.minute == 0 and timestamp.hour == 0 and
                timestamp.day % days == 0):
            timeframes.append(f"{days}d")

    def parse_data(self, event):
        """Process incoming market data, update all models with new data."""

        self.logger.debug(event.get_bar())

    def load_dataframes(self):
        """Create and return a dictionary of dataframes for all symbols and
        timeframes."""
        pass

    def load_models(self, logger):
        """Create and return a list of all model objects"""

        models = []
        models.append(TrendFollowing())
        self.logger.debug("Initialised models.")
        return models

