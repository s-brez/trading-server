from event import MarketEvent
from datetime import date
from datetime import timedelta
import datetime
import calendar
from time import sleep


class Datahandler:
    """Datahandler wraps exchange data and locally stored data with Market
    events and adds it to the event queue as each timeframe period elapses.
    Market events are created from either live or stored data (depending on
    if backtesting or live trading) and pushed to the event queue for the
    Strategy object to consume."""

    MINUTE_TIMEFRAMES = [3, 5, 15, 30]
    HOUR_TIMEFRAMES = [1, 2, 3, 4, 6, 8]
    DAY_TIMEFRAMES = [1, 2, 3]

    def __init__(self, exchanges, events, logger):
        self.exchanges = exchanges
        self.events = events
        self.logger = logger
        self.exchanges = []
        self.events = object
        self.logger = object
        self.live_trading = False

    def update_market_data(self):
        """Pushes new market events to the event queue"""

        bars = []
        if self.live_trading:
            bars = self.get_new_data()
        else:
            bars = self.get_historic_data()
        for bar in bars:
            self.events.put(bar)

    def get_new_data(self):
        """Return a list of market events (new bars) for all watched
        symbols from all exchanges for the just-elapsed time period."""
        # new_market_events = []
        # for exchange in self.exchanges:
        #     for symbol in exchange.get_symbols:
        #         data = {}
        #         # wait for exchange classes to finish parsing ticks
        #         while not exchange.finished_parsing_ticks():
        #             sleep(0.005)
        #             if exchange.finished_parsing_ticks():
        #                 data = exchange.get_new_bars()
        #                 break
        return

    def get_historic_data(self):
        """Return a list of market events (historic bars) from
        locally stored data."""
        historic_market_events = []

        return historic_market_events

    def store_new_bars(self, bars: list):
        """Save incoming data to local database."""

    def backfill_missing_data(self):
        """Check for missing data between the last locally-stored timestamp
        and initial timestamp time of currently streaming live data. If
        discrepencies exist, get and store the missing data."""

    def set_live_trading(self, live_trading):
        """Set true or false live execution flag"""
        self.set_live_trading = live_trading

    def get_timeframes(self):
        """Return a list of timeframes relevant to the just-elapsed time period.
        E.g if time has just struck UTC 10:30am the list will contain "1m",
        "3m", "5m", "m15" and "30m" strings. The first minute of a new day or
        week will add daily/weekly/monthly timeframe strings. Timeframes in
        use are 1, 3, 5, 15 and 30 mins, 1, 2, 3, 4, 6, 8 and 12 hours, 1, 2
        and 3 days, weekly and monthly."""

        # check agains the previous minute, as that is the just-elapsed period.
        timestamp = datetime.datetime.utcnow() - timedelta(hours=0, minutes=1)
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
