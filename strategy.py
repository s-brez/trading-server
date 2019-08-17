
from datetime import date, datetime, timedelta
from model import TrendFollowing
import pandas as pd
import calendar


class Strategy:
    """ """

    MINUTE_TIMEFRAMES = [3, 5, 15, 30]
    HOUR_TIMEFRAMES = [1, 2, 3, 4, 6, 8]
    DAY_TIMEFRAMES = [1, 2, 3]

    def __init__(self, events, logger):
        self.events = events
        self.logger = logger
        self.models = self.load_models(self.logger)

    def parse_data(self, event):
        """Process incoming market data, re-run all models with new data."""
        self.logger.debug(event.get_bar())

    def load_models(self, logger):
        """Create and return a list of all model objects"""

        models = []
        models.append(TrendFollowing())
        self.logger.debug("Initialised models.")
        return models

    def load_dataframes(self):
        """Unpickle saved dataframes if they exist, create new if not.
        Each symbol and timeframe will have its own dataframe"""
        pass

    def get_timeframes(self, time):
        """Return a list of timeframes relevant to the just-elapsed time period.
        E.g if time has just struck UTC 10:30am the list will contain "1m",
        "3m", "5m", "m15" and "30m" strings. The first minute of a new day or
        week will add daily/weekly/monthly timeframe strings. Timeframes in
        use are 1, 3, 5, 15 and 30 mins, 1, 2, 3, 4, 6, 8 and 12 hours, 1, 2
        and 3 days, weekly and monthly."""

        # check agains the previous minute, as that is the just-elapsed period.
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
