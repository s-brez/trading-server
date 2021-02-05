"""
trading-server is a multi-asset, multi-strategy, event-driven execution
and backtesting platform (OEMS) for trading common markets.

Copyright (C) 2020  Sam Breznikar <sam@sdbgroup.io>

Licensed under GNU General Public License 3.0 or later.

Some rights reserved. See LICENSE.md, AUTHORS.md.
"""

from datetime import date, datetime, timedelta
from model import EMACrossTestingOnly
from pymongo import MongoClient, errors
from features import Features
from dateutil import parser
import pandas as pd
import calendar
import pymongo
import queue
import time
import copy


class Strategy:
    """
    Ccontrol layer for all individual strategy models. Consumes
    market events from the event queue, updates strategy models with new data
    and generating Signal events.

    Signal events are pushed to the main event-handling queue, and also put
    into a save-later queue for db storage, after time-intensive work is done.
    """

    # For reampling with pandas.
    ALL_TIMEFRAMES = [
        "1Min", "3Min", "5Min", "15Min", "30Min", "1H", "2H", "3H", "4H",
        "6H", "8H", "12H", "16H", "1D", "2D", "3D", "4D", "7D", "14D", "28D"]

    PREVIEW_TIMEFRAMES = ["1H", "1D"]

    RESAMPLE_KEY = {
        'open': 'first', 'high': 'max', 'low': 'min',
        'close': 'last', 'volume': 'sum'}

    MINUTE_TIMEFRAMES = [1, 3, 5, 15, 30]
    HOUR_TIMEFRAMES = [1, 2, 3, 4, 6, 8, 12, 16]
    DAY_TIMEFRAMES = [1, 2, 3, 4, 7, 14, 28]

    TF_MINS = {
        "1Min": 1, "3Min": 3, "5Min": 5, "15Min": 15, "30Min": 30, "1H": 60,
        "2H": 120, "3H": 180, "4H": 240, "6H": 360, "8H": 480, "12H": 720,
        "16H": 960, "1D": 1440, "2D": 2880, "3D": 4320, "4D": 5760,
        "7D": 10080, "14D": 20160, "28D": 40320}

    # Extra bars to include in resample requests to account for indicator lag.
    LOOKBACK_PAD = 50

    # Maximum lookback in use by any strategy.
    MAX_LOOKBACK = 150

    def __init__(self, exchanges, logger, db_prices, db_other, db_client):
        self.exchanges = exchanges
        self.logger = logger
        self.db_prices = db_prices
        self.db_other = db_other
        self.db_client = db_client
        self.db_collections_price = {
            i.get_name(): db_prices[i.get_name()] for i in self.exchanges}

        # Save-later queue.
        self.signals_save_to_db = queue.Queue(0)

        # DataFrame container: data[exchange][symbol][timeframe].
        self.data = {}
        self.init_dataframes(empty=True)

        # Strategy models.
        self.models = self.load_models(self.logger)

        # Signal container: signals[exchange][symbol][timeframe].
        self.signals = {}

        # persistent reference to features library.
        self.feature_ref = Features()

    def new_data(self, events, event, count):
        """
        Process incoming market data and update all models with new data.

        Args:
            events: event queue object.
            event: new market event.

        Returns:
            None.

        Raises:
            None.
        """

        # Wait for 3 mins of operation to clear up any null bars.
        if count >= 3:

            # Get operating timeframes for the current period.

            timestamp = event.get_bar()['timestamp']
            timeframes = self.get_relevant_timeframes(timestamp)

            self.logger.info("Event timestamp just in: " + str(
                datetime.utcfromtimestamp(timestamp)))

            # Store trigger timeframes (operating timeframes).
            op_timeframes = copy.deepcopy(timeframes)

            # Get additional timeframes required by models.
            for model in self.models:
                model.get_required_timeframes(timeframes)

            # Update datasets for all required timeframes.
            self.update_dataframes(event, timeframes, op_timeframes)

            # Calculate new feature values.
            self.calculate_features(event, timeframes)

            # Run models with new data.
            self.run_models(event, op_timeframes, events)

    def update_dataframes(self, event, timeframes, op_timeframes):
        """
        Update dataframes for the given event and list of timeframes.

        Args:
            event: new market event.
            timeframes: list of relevant timeframes to the just-elapsed period.

        Returns:
            None.

        Raises:
            None.
        """

        sym = event.get_bar()['symbol']
        bar = self.remove_element(event.get_bar(), "symbol")
        exc = event.get_exchange()
        venue = exc.get_name()

        timestamp = datetime.utcfromtimestamp(bar['timestamp'])

        # Update each relevant dataframe.
        for tf in timeframes:

            size = len(self.data[venue][sym][tf].index)

            # If dataframe already populated, append the new bar. Only update
            # op_timeframes if appending, as required tf data will be mid-bar.
            if size > 0 and tf in op_timeframes:

                new_row = self.single_bar_resample(
                        venue, sym, tf, bar, timestamp)

                # If timestamps out of order, rebuild the dataset.

                # if existing row timestamp not tf period from current, rebuild

                # Append.
                self.data[venue][sym][tf] = self.data[venue][sym][tf].append(
                    new_row)

                self.logger.info(
                    "Appended new row to " + str(tf) + " dataset.")

            # If dataframe is empty, populate a new one.
            elif size == 0:
                self.data[venue][sym][tf] = self.build_dataframe(
                    venue, sym, tf, bar)
                self.logger.info(
                    "Created new df for " + str(tf) + " dataset.")

            # Final pad in case of null bars.
            self.data[venue][sym][tf].fillna(method="pad", inplace=True)

            # TODO: df.append() is slow and copies the whole dataframe. Later
            # need to swap to a data structure other than a dataframe for live
            # data addition. Like an in-memory csv/DB, or list of dicts, etc.

        # Log model and timeframe details.
        for model in self.models:

            venue = exc.get_name()
            inst = model.get_instruments()[venue][sym]

            if inst == sym:
                self.logger.info(
                    model.get_name() + ": " + venue + ": " + inst)
                self.logger.info(
                    "Operating timeframes: " + str(op_timeframes))
                self.logger.info(
                    "Required timeframes: " + str(timeframes))

    def calculate_features(self, event, timeframes):
        """
        Calculate features required for each model, append the values to each
        timeframe dataset.

        Args:
            None.
        Returns:
            None.
        Raises:
            None.
        """
        sym = event.get_bar()['symbol']
        exc = event.get_exchange()

        # Calculate feature data for each model/feature/timeframe.
        for model in self.models:

            lb = model.get_lookback()
            venue = exc.get_name()
            inst = model.get_instruments()[venue][sym]

            # Check if model is applicable to the event.
            if inst == sym:
                for tf in timeframes:

                    features = model.get_features()
                    data = self.data[venue][sym][tf]

                    # Calculate feature data.
                    for feature in features:

                        # f[0] is feature type
                        # f[1] is feature function
                        # f[2] is feature param
                        f = feature[1](
                                self.feature_ref,
                                feature[2],
                                data)

                        # Handle indicator and time-series feature data.
                        if (f[0] == "indicator" or
                            (type(f) == pd.core.series.Series) or
                                (type(f) == pd.Series)):

                            # Use feature param as dataframe col name.
                            ID = "" if feature[2] is None else str(feature[2])

                            # Round and append to dataframe.
                            self.data[venue][sym][tf][
                                feature[1].__name__ +
                                ID] = f.round(6)

                        # Handle boolean feature data.
                        elif f[0] == "boolean":
                            pass

                        # TODO

    def run_models(self, event, op_timeframes: list, events):
        """
        Run models for the just-elpased period.

        Args:
            event: new market event.
            op_timeframes: relevant timeframes to the just-elapsed period.

        Returns:
            None.

        Raises:
            None.

        """

        self.logger.info("Running models.")

        sym = event.get_bar()['symbol']
        exc = event.get_exchange()

        for model in self.models:

            venue = exc.get_name()
            inst = model.get_instruments()[venue][sym]

            if inst == sym:
                for tf in op_timeframes:
                    if tf in model.get_operating_timeframes():

                        # Get non-op, but still required timeframe codes.
                        req_tf = model.get_required_timeframes(
                            [tf], result=True)

                        # Get non-trigger data as list of {tf : dataframe}.
                        req_data = [
                            {i: self.data[venue][sym][i]} for i in req_tf]

                        # Run model.
                        result = model.run(self.data[venue][sym], req_data, tf,
                                           sym, exc)

                        # Put generated signal in the main event queue.
                        if result:
                            events.put(result)

                            # Put signal in separate save-later queue.
                            self.signals_save_to_db.put(result)

    def build_dataframe(self, exc, sym, tf, current_bar=None, lookback=150):
        """
        Return a dataframe of size lookback for the given symbol,
        exchange and timeframe. If "curent_bar" param is passed in,
        construct the dataframe using current_bar as first row of dataframe.

        E.g 1 (no current_bar) for a dataframe with tf = 4h, lookback = 50, we
        need to fetch and resample 4*60*50 1 min bars (12000 bars) into 50 4h
        bars.

        E.g 2 (with current_bar) for dataframe with tf = 4h, lookback = 50, we
        need to fetch and resample 4*60*50 - 1 1 min bars (11999 bars) into 50
        4h bars, using current_bar as the first bar (total 12000 bars).

        Args:
            exc: exchange name (string).
            symb: instrument ticker code (string)
            tf: timeframe code (string).
            current_bar: bar to insert first, if using
            lookback: number of final bars required for the model to use.

        Returns:
            dataframe: dataframe containing resampled price data.

        Raises:
            Resampling error.
        """

        # Find the total number of 1min bars needed using TFM dict.
        if lookback > 1:
            # Increase the size of lookback by 50 to account for feature lag.
            size = int(self.TF_MINS[tf] * (lookback + self.LOOKBACK_PAD))
        else:
            # Dont adjust lookback for single bar requests.
            size = self.TF_MINS[tf] * (lookback)

        # Create Dataframe using current_bar and stored bars.
        if current_bar:

            # Reduce size to account for current_bar.
            size = size - 1

            # Use a projection to remove mongo "_id" field and symbol.
            result = self.db_collections_price[exc].find(
                {"symbol": sym}, {
                    "_id": 0, "symbol": 0}).limit(
                        size).sort([("timestamp", -1)])

            # Add current_bar and DB results to a list.
            rows = [current_bar]
            for doc in result:
                rows.append(doc)

        # Create Dataframe using only stored bars
        if not current_bar:

            # Use a projection to remove mongo "_id" field and symbol.
            rows = self.db_collections_price[exc].find(
                {"symbol": sym}, {
                    "_id": 0, "symbol": 0}).limit(
                        size).sort([("timestamp", -1)])

        # Pass cursor to DataFrame constructor.
        df = pd.DataFrame(rows)

        # Format time column.
        df['timestamp'] = df['timestamp'].apply(
            lambda x: datetime.utcfromtimestamp(x))

        # Set index.
        df.set_index("timestamp", inplace=True)

        # Pad any null bars forward.
        df.fillna(method="pad", inplace=True)

        # Downsample 1 min data to target timeframe
        resampled_df = pd.DataFrame()
        try:
            resampled_df = (df.resample(tf).agg(self.RESAMPLE_KEY))
        except Exception as exc:
            print("Resampling error", exc)

        return resampled_df.sort_values(by="timestamp", ascending=True)

    def single_bar_resample(self, venue, sym, tf, bar, timestamp):
        """
        Return a pd.Series containing a single bar of timeframe "tf" for
        the given venue and symbol.

        Args:
            venue: exchange name (string).
            sym: instrument ticker code (string)
            tf: timeframe code (string).
            bar: newest 1-min bar.

        Returns: new_row: pd.Series containing a single bar of timeframe "tf"
        for the given venue and symbol.

        Raises:
            Resampling error.
        """

        if tf == "1Min":
            # Don't need to do any resampling for 1 min bars.
            rows = [bar]

        else:
            # Determine how many bars to fetch for resampling.
            size = self.TF_MINS[tf] - 1

            # Use a projection to remove mongo "_id" field and symbol.
            result = self.db_collections_price[venue].find(
                {"symbol": sym}, {
                    "_id": 0, "symbol": 0}).limit(
                        size).sort([("timestamp", -1)])

            # Add current_bar and DB results to a list.
            rows = [bar]
            for doc in result:
                rows.append(doc)

        # Pass cursor to DataFrame constructor.
        df = pd.DataFrame(rows)

        # Format time column.
        df['timestamp'] = df['timestamp'].apply(
            lambda x: datetime.utcfromtimestamp(x))

        # Set index.
        df.set_index("timestamp", inplace=True)

        # Pad any null bars forward.
        df.fillna(method="pad", inplace=True)

        # Downsample 1 min data to target timeframe.
        resampled = pd.DataFrame()
        try:
            resampled = (df.resample(tf).agg(self.RESAMPLE_KEY))
        except Exception as exc:
            print("Resampling error", exc)

        # Must be ascending=True to grab the first value with iloc[].
        resampled.sort_values(by="timestamp", ascending=False, inplace=True)

        new_row = resampled.iloc[0]

        return new_row

    def remove_element(self, dictionary, element):
        """
        Return a shallow copy of dictionary less the given element.

        Args:
            dictionary: dictionary to be copied.
            element: element to be removed.

        Returns:
            new_dict: copy of dictionary less element.

        Raises:

        """

        new_dict = dict(dictionary)
        del new_dict[element]

        return new_dict

    def load_models(self, logger):
        """
        Create and return a list of trade strategy models.

        Args:
            logger: logger object.

        Returns:
            models: list of models.

        Raises:
            None.
        """

        models = []
        models.append(EMACrossTestingOnly(logger))
        self.logger.info("Initialised models.")
        return models

    def init_dataframes(self, empty=False):
        """
        Create working datasets (self.data dict).

        Args:
            None.

        Returns:
            empty: boolean flag. If True, will return empty dataframes.

        Raises:
            None.
        """

        start = time.time()

        self.data = {
            i.get_name(): self.load_local_data(
                i, empty) for i in self.exchanges}

        end = time.time()
        duration = round(end - start, 5)

        symbolcount = 0
        for i in self.exchanges:
            symbolcount += len(i.get_symbols())

        # Only log output if data is loaded.
        if not empty:
            self.logger.info(
                "Initialised " + str(symbolcount * len(self.ALL_TIMEFRAMES)) +
                " timeframe datasets in " + str(duration) + " seconds.")

    def load_local_data(self, exchange, empty=False):

        """
        Create and return a dictionary of dataframes for all symbols and
        timeframes for the given venue.

        Args:
            exchange: exchange object.
            empty: boolean flag. If True, will return empty dataframes.

        Returns:
            dicts: tree containing a dataframe for all symbols and
            timeframes for the given exchange. If "empty" is true,
            dont load any data.

        Raises:
            None.
        """

        dicts = {}
        for symbol in exchange.get_symbols():

            # Return empty dataframes.
            if empty:
                dicts[symbol] = {
                    tf: pd.DataFrame() for tf in self.ALL_TIMEFRAMES}

            # Return dataframes with data.
            elif not empty:
                dicts[symbol] = {
                    tf: self.build_dataframe(
                        exchange, symbol, tf) for tf in self.ALL_TIMEFRAMES}

        return dicts

    def trim_datasets(self):
        """
        Reduce size of datasets if length > MAX_LOOKBACK + LOOKBACK_PAD.
        Args:
           None.

        Returns:
           None.

        Raises:
           None.
        """

        for exc in self.exchanges:

            venue = exc.get_name()

            for sym in exc.get_symbols():
                for tf in self.ALL_TIMEFRAMES:

                    size = len(self.data[venue][sym][tf].index)

                    if size > self.MAX_LOOKBACK + self.LOOKBACK_PAD:
                        diff = size - (self.MAX_LOOKBACK + self.LOOKBACK_PAD)

                        # Get list of indicies to drop.
                        to_drop = [i for i in range(diff)]

                        # Drop rows by index in-place.
                        self.data[venue][sym][tf].drop(
                            self.data[venue][sym][tf].index[to_drop],
                            inplace=True)

                        # print("Timeframe:", tf, " \n", self.data[e][s][tf])

    def get_relevant_timeframes(self, time):
        """
        Return a list of timeframes relevant to the just-elapsed period.
        E.g if time has just struck UTC 10:30am the list will contain "1min",
        "3Min", "5Min", "15Min" and "30Min" strings. The first minute of a new
        day or week will add daily/weekly/monthly timeframe strings.

        Args:
            time: datetime object

        Returns:
            timeframes: list containing relevant timeframe string codes.

        Raises:
            None.

        """

        # Check against the previous minute - the just-elapsed period.
        if type(time) is not datetime:
            time = datetime.utcfromtimestamp(time)

        timestamp = time - timedelta(hours=0, minutes=1)
        timeframes = []

        self.logger.info("Timestamp just elapsed: " + str(timestamp))

        for i in self.MINUTE_TIMEFRAMES:
            self.minute_timeframe(i, timestamp, timeframes)
        for i in self.HOUR_TIMEFRAMES:
            self.hour_timeframe(i, timestamp, timeframes)
        for i in self.DAY_TIMEFRAMES:
            self.day_timeframe(i, timestamp, timeframes)

        # if (timestamp.minute == 0 and timestamp.hour == 0 and
        #         calendar.day_name[date.today().weekday()] == "Monday"):
        #     timeframes.append("7D")

        return timeframes

    def minute_timeframe(self, minutes, timestamp, timeframes):
        """
        Adds minute timeframe codes to timeframes list if the relevant
        period has just elapsed.
        """

        for i in range(0, 60, minutes):
            if timestamp.minute == i:
                timeframes.append(str(minutes) + "Min")

    def hour_timeframe(self, hours, timestamp, timeframes):
        """
        Adds hourly timeframe codes to timeframes list if the relevant
        period has just elapsed.
        """

        if timestamp.minute == 0 and timestamp.hour % hours == 0:
            timeframes.append(str(hours) + "H")

    def day_timeframe(self, days, timestamp, timeframes):
        """
        Adds daily timeframe codes to timeframes list if the relevant
        period has just elapsed.
        """

        if (timestamp.minute == 0 and timestamp.hour == 0 and
                timestamp.day % days == 0):
            timeframes.append(str(days) + "D")

    def save_new_signals_to_db(self):
        """
        Save signals in save-later queue to database.

        Args:
            None.
        Returns:
            None.
        Raises:
            pymongo.errors.DuplicateKeyError.
        """

        count = 0
        while True:

            try:
                signal = self.signals_save_to_db.get(False)

            except queue.Empty:
                if count:
                    self.logger.info(
                        "Wrote " + str(count) + " new signals to database " +
                        str(self.db_other.name) + ".")
                break

            else:
                if signal is not None:
                    count += 1
                    # Store signal in relevant db collection.
                    try:

                        self.db_other['signals'].insert_one(
                            self.remove_element(signal.get_signal_dict(), "op_data"))

                    # Skip duplicates if they exist.
                    except pymongo.errors.DuplicateKeyError:
                        continue

                self.signals_save_to_db.task_done()
