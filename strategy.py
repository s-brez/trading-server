
from datetime import date, datetime, timedelta
from model import TrendFollowing
import pandas as pd
import calendar
import time


class Strategy:
    """Master control layer for all individual strategy models. Consumes market
    events from the event queue, updates strategy models with new data and
    generating Signal events. Stores working data as dataframes in data{}."""

    ALL_TIMEFRAMES = [
        "1Min", "3Min", "5Min", "15Min", "30Min", "1H", "2H", "3H", "4H",
        "6H", "8H", "12H", "1D", "2D", "3D", "7D", "14D", "28D"]

    PREVIEW_TIMEFRAMES = ["1H", "1D"]

    RESAMPLE_KEY = {
        'open': 'first', 'high': 'max', 'low': 'min',
        'close': 'last', 'volume': 'sum'}

    MINUTE_TIMEFRAMES = [1, 3, 5, 15, 30]
    HOUR_TIMEFRAMES = [1, 2, 3, 4, 6, 8, 12]
    DAY_TIMEFRAMES = [1, 2, 3, 7, 14, 28]

    TF_MINS = {
        "1Min": 1, "3Min": 3, "5Min": 5, "15Min": 15, "30Min": 30, "1H": 60,
        "2H": 120,
        "3H": 180, "4H": 240, "6H": 360, "8H": 480, "12H": 720, "1D": 1440,
        "2D": 2880, "3D": 4320, "7D": 10080, "14D": 20160, "28D": 40320}

    def __init__(self, exchanges, logger, db, db_client):
        self.exchanges = exchanges
        self.logger = logger
        self.db = db
        self.db_client = db_client
        self.db_collections = {
            i.get_name(): db[i.get_name()] for i in self.exchanges}
        self.models = self.load_models(self.logger)
        self.logger.debug("Initialised working data.")

        # DataFrame container: data[exchange][symbol][timeframe]
        self.data = {}

    def parse_new_data(self, event):
        """Process incoming market data, update all models with new data."""

        # update relevant datasets
        self.update_datasets(
            event,
            self.get_relevant_timeframes(event.get_bar()['timestamp']))

    def update_datasets(self, bar, timeframes):
        """Update datasets for the given asset and list of of timeframes."""

        self.logger.debug(event)
        self.logger.debug(timeframes)

    def get_relevant_timeframes(self, time):
        """Return a list of timeframes relevant to the just-elapsed period.
        E.g if time has just struck UTC 10:30am the list will contain "1m",
        "3m", "5m", "m15" and "30m" strings. The first minute of a new day or
        week will add daily/weekly/monthly timeframe strings. Timeframes in
        use are 1, 3, 5, 15 and 30 mins, 1, 2, 3, 4, 6, 8 and 12 hours, 1, 2
        and 3 days, weekly and monthly."""

        # check against the previous minute - the just-elapsed period.
        if type(time) is not datetime:
            time = datetime.utcfromtimestamp(time)

        timestamp = time - timedelta(hours=0, minutes=1)
        timeframes = []

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

    def load_models(self, logger):
        """Create and return a list of trade strategy models."""

        models = []
        models.append(TrendFollowing())
        self.logger.debug("Initialised models.")
        return models

    def init_dataframes(self):
        """Create working datasets and log dataframe init time.
         Should only be called after local data has been updated."""

        self.logger.debug("Started building timeframes datasets.")

        start = time.time()
        self.data = {
            i.get_name(): self.load_local_data(i) for i in self.exchanges}
        end = time.time()
        duration = round(end - start, 5)

        symbolcount = 0
        for i in self.exchanges:
            symbolcount += len(i.get_symbols())

        self.logger.debug(
            "Initialised " + str(symbolcount * len(self.ALL_TIMEFRAMES)) +
            " timeframe datasets in " + str(duration) + " seconds.")

    def build_dataframe(self, exc, sym, tf, lookback=150):
        """Return a dataframe of size lookback for the given symbol (sym),
        exchange (exc) and timeframe (tf).

        Lookback is the number of previous bars required by a model to perform
        to perform its analysis. E.g for a dataframe with tf = 4h, lookback =
        50, we will need to fetch and resample 4*60*50 1 min bars (12000 bars)
        into 50 4h bars."""

        # Find the total number of 1min bars needed using TFM dict.
        size = self.TF_MINS[tf] * lookback

        # Use a projection to remove mongo "_id" field and symbol.
        result = self.db_collections[exc.get_name()].find(
            {"symbol": sym}, {
                "_id": 0, "symbol": 0}).limit(
                    size).sort([("timestamp", -1)])

        # Pass cursor to DataFrame constructor
        df = pd.DataFrame(result)

        # Format time column
        df['timestamp'] = df['timestamp'].apply(
            lambda x: datetime.fromtimestamp(x))

        # Set index
        df.set_index("timestamp", inplace=True)

        # Downsample 1 min data to target timeframe
        resampled_df = pd.DataFrame()
        try:
            resampled_df = (df.resample(tf).agg(self.RESAMPLE_KEY))
        except Exception as e:
            print(e)

        return resampled_df.sort_values(by="timestamp", ascending=False)

    def load_local_data(self, exchange):
        """Create and return a dictionary of dataframes for all symbols and
        timeframes for the given exchange."""

        dicts = {}
        for symbol in exchange.get_symbols():
            dicts[symbol] = {
                tf: self.build_dataframe(
                    exchange, symbol, tf) for tf in self.ALL_TIMEFRAMES}
        return dicts
