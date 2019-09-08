from datetime import date, datetime, timedelta
from model import TrendFollowing
from itertools import groupby, count
from pymongo import MongoClient, errors
import pandas as pd
import pymongo
import pandas as pd
import calendar
from broker import Broker
from time import sleep
import time
import logging
import queue
import datetime


class Exchange:

    def get_name(self):
        return "BitMEX"

    def get_symbols(self):
        return ["XBTUSD", "ETHUSD"]


class strategy_test:

    db_client = MongoClient('mongodb://127.0.0.1:27017/')
    db = db_client['asset_price_master']
    coll = db['BitMEX']

    # All timeframes string values.
    ALL_TIMEFRAMES = [
        "1Min", "3Min", "5Min", "15Min", "30Min", "1H", "2H", "3H", "4H",
        "6H", "8H", "12H", "1D", "2D", "3D", "7D", "14D", "28D"]

    # Timeframe strings: minute int values.
    TF_MINS = {
        "1Min": 1, "3Min": 3, "5Min": 5, "15Min": 15, "30Min": 30, "1H": 60,
        "2H": 120,
        "3H": 180, "4H": 240, "6H": 360, "8H": 480, "12H": 720, "1D": 1440,
        "2D": 2880, "3D": 4320, "7D": 10080, "14D": 20160, "28D": 40320}

    # Pandas resampling instructions.
    RESAMPLE_KEY = {
        'open': 'first', 'high': 'max', 'low': 'min',
        'close': 'last', 'volume': 'sum'}

    MINUTE_TIMEFRAMES = [1, 3, 5, 15, 30]
    HOUR_TIMEFRAMES = [1, 2, 3, 4, 6, 8, 12]
    DAY_TIMEFRAMES = [1, 2, 3, 7, 14, 28]

    def __init__(self):
        self.logger = self.setup_logger()
        self.exchanges = [Exchange()]
        self.data = {
            i.get_name(): self.load_data(i) for i in self.exchanges}

    def setup_logger(self):
        """Create and configure logger"""

        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s:%(levelname)s:%(module)s - %(message)s")
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        # supress requests/urlib3/connectionpool messages
        # logging.DEBUG produces messages with each https request...
        logging.getLogger("urllib3").propagate = False
        requests_log = logging.getLogger("requests")
        requests_log.addHandler(logging.NullHandler())
        requests_log.propagate = False

        return logger

    def get_relevant_timeframes(self, time):
        """Return a list of timeframes relevant to the just-elapsed period.
        E.g if time has just struck UTC 10:30am the list will contain "1Min",
        "3Min", "5Min", "m15" and "30Min" strings. The first minute of a new
        day or week will add daily/weekly/monthly timeframe strings. Timeframes
        in use are 1, 3, 5, 15 and 30 mins, 1, 2, 3, 4, 6, 8 and 12 hours, 1, 2
        and 3 days, weekly and monthly."""

        # check against the previous minute - the just-elapsed period.
        ts = time
        if type(ts) is not datetime.datetime:
            ts = datetime.datetime.utcfromtimestamp(time)
        timestamp = ts - timedelta(hours=0, minutes=1)
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
                print("minute tf added:", f"{minutes}Min")

    def hour_timeframe(self, hours, timestamp, timeframes):
        if timestamp.minute == 0 and timestamp.hour % hours == 0:
            timeframes.append(f"{hours}h")
            print("hour tf added:", f"{hours}Min")

    def day_timeframe(self, days, timestamp, timeframes):
        if (timestamp.minute == 0 and timestamp.hour == 0 and
                timestamp.day % days == 0):
            timeframes.append(f"{days}d")
            print("day tf added:", f"{days}Min")

    def load_data(self, exchange):
        """Create and return a dictionary of dataframes for all symbols and
        timeframes for the given exchange."""

        dicts = {}
        for symbol in exchange.get_symbols():
            dicts[symbol] = {
                tf: self.build_dataframe(
                    exchange, symbol, tf) for tf in self.ALL_TIMEFRAMES}
        return dicts

    def build_dataframe(self, exc, sym, tf, lookback=5):
        """Return a dataframe of size lookback for the given symbol (sym),
        exchange (exc) and timeframe (tf).

        Lookback is the number of previous bars required by a model to perform
        to perform its analysis. E.g for a dataframe with tf = 4h, lookback =
        50, we will need to fetch and resample 4*60*50 1 min bars (12000 bars)
        into 50 4h bars."""

        # Find the total number of 1min bars needed using TFM dict.
        size = self.TF_MINS[tf] * lookback

        # Use a projection to remove mongo "_id" field and symbol.
        result = self.coll.find(
            {"symbol": sym}, {
                "_id": 0, "symbol": 0}).limit(
                    size).sort([("timestamp", -1)])

        # Pass cursor to DataFrame, format time, set index.
        df = pd.DataFrame(result)
        if tf == "1Min":
            print(df.iloc[1])
        df['timestamp'] = pd.to_datetime(
            df['timestamp'], utc=True, unit='s')
        df.set_index("timestamp", inplace=True)


        # Downsample 1 min data to target timeframe
        resampled_df = pd.DataFrame()
        try:
            if tf != "1Min":
                resampled_df = (df.resample(tf).agg(self.RESAMPLE_KEY))
            else:
                resampled_df = df
        except Exception as e:
            print(e)
        if tf == "1Min":
            print(resampled_df.head(3))
        return resampled_df


strategy = strategy_test()
# print(strategy.data["BitMEX"]['XBTUSD'])
# print(strategy.data["BitMEX"]['ETHUSD'])


# print(strategy.get_relevant_timeframes(1567871460))
