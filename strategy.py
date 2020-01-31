from datetime import date, datetime, timedelta
from model import TrendFollowing
from dateutil import parser
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

        # DataFrame container: data[exchange][symbol][timeframe]
        self.data = {}

    def parse_new_data(self, event):
        """Process incoming market data, update all models with new data."""

        timeframes = self.get_relevant_timeframes(event.get_bar()['timestamp'])

        # update relevant dataframes
        self.update_dataframes(event, timeframes)

        # run models with new data
        self.run_models(event, timeframes)

    def update_dataframes(self, event, timeframes):
        """Update dataframes for the given asset and list of timeframes."""

        sym = event.get_bar()['symbol']
        bar = self.remove_element(event.get_bar(), "symbol")
        exc = event.get_exchange()

        # 1. If df empty, create a new one from stored data + the new bar
        # 2. If df not empty, check the second row timestamp. if it matches
        #    the previous minute, simply insert the new bar in row one
        # 3. If second row timestamp doesnt match, go to step 1.

        for tf in timeframes:
            # update each dataframe
            self.data[exc][sym][tf] = self.build_dataframe(
                exc, sym, tf, bar)
            # print for sanity check
            self.logger.debug(tf)
            self.logger.debug(self.data[exc][sym][tf].head(5))
            self.logger.debug(bar)

            self.logger.debug("should be the first index timestamp value:")
            index_2 = pd.Timestamp(self.data[exc][sym][tf].index.values[0])

            self.logger.debug(index_2)
            self.logger.debug(type(index_2))

            # TODO log the timestamp as human-readable datetime
            self.logger.debug(event)

    def run_models(self, event, timeframes):
        pass

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
                timeframes.append(f"{minutes}Min")

    def hour_timeframe(self, hours, timestamp, timeframes):
        if timestamp.minute == 0 and timestamp.hour % hours == 0:
            timeframes.append(f"{hours}H")

    def day_timeframe(self, days, timestamp, timeframes):
        if (timestamp.minute == 0 and timestamp.hour == 0 and
                timestamp.day % days == 0):
            timeframes.append(f"{days}D")

    def load_models(self, logger):
        """Create and return a list of trade strategy models."""

        models = []
        models.append(TrendFollowing())
        self.logger.debug("Initialised models.")
        return models

    def init_dataframes(self):
        """Create working datasets (self.data dict)"""

        self.logger.debug("Started building DataFrames.")

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

    def build_dataframe(self, exc, sym, tf, current_bar=None, lookback=150):
        """Return a dataframe of size lookback for the given symbol (sym),
        exchange (exc) and timeframe (tf). If "curent_bar" param is passed in,
        construct the dataframe using current_bar as first row of dataframe.

        E.g 1 (no current_bar) for a dataframe with tf = 4h, lookback = 50, we
        need to fetch and resample 4*60*50 1 min bars (12000 bars) into 50 4h
        bars.

        E.g 2 (with current_bar) for dataframe with tf = 4h, lookback = 50, we
        need to fetch and resample 4*60*50 - 1 1 min bars (11999 bars) into 50
        4h bars, using current_bar as the first bar (total 12000 bars)."""

        # Find the total number of 1min bars needed using TFM dict.
        size = self.TF_MINS[tf] * lookback

        # Create Dataframe using only stored bars
        if current_bar is None:

            # Use a projection to remove mongo "_id" field and symbol.
            result = self.db_collections[exc].find(
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

        # Create Dataframe using current_bar and stored bars
        if current_bar:

            # reduce size to account for current_bar
            size = size - 1

            # Use a projection to remove mongo "_id" field and symbol.
            result = self.db_collections[exc].find(
                {"symbol": sym}, {
                    "_id": 0, "symbol": 0}).limit(
                        size).sort([("timestamp", -1)])

            # add current_bar and DB results to a list
            rows = [current_bar]
            for doc in result:
                rows.append(doc)

            # pass list to dataframe constructor
            df = pd.DataFrame(rows)

            # Format time column
            df['timestamp'] = df['timestamp'].apply(
                lambda x: datetime.fromtimestamp(x))

            # Set index
            df.set_index("timestamp", inplace=True)

            # append stored bars to dataframe

            # format dataframe

        # Downsample 1 min data to target timeframe
        resampled_df = pd.DataFrame()
        try:
            resampled_df = (df.resample(tf).agg(self.RESAMPLE_KEY))
        except Exception as exc:
            print("Resampling error", exc)

        return resampled_df.sort_values(by="timestamp", ascending=False)

    def load_local_data(self, exchange):
        """Create and return a dictionary of dataframes for all symbols and
        timeframes for the given exchange."""

        # return dataframes with data
        # dicts = {}
        # for symbol in exchange.get_symbols():
        #     dicts[symbol] = {
        #         tf: self.build_dataframe(
        #             exchange, symbol, tf) for tf in self.ALL_TIMEFRAMES}
        # return dicts

        # return empty dataframes
        dicts = {}
        for symbol in exchange.get_symbols():
            dicts[symbol] = {
                tf: pd.DataFrame() for tf in self.ALL_TIMEFRAMES}
        return dicts

    def remove_element(self, dictionary, element):
        """Return a new dict minuis the given element."""

        new_dict = dict(dictionary)
        del new_dict[element]
        return new_dict
