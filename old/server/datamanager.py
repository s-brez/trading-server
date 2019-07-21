import datetime
import os
import csv
import pandas as pd
import numpy
from bitfinex import Bitfinex


class Datamanager:
    """ Provides interpolation, storage, retrieval
        and transfomation for asset data. Slices tick data from exchanges into
        m1 resolution bars, then drip feeds bars to event queue
    """

    # 1 in ms
    step = 60000

    required_timeframes = []
    exchanges = []

    # resampling dict for resample()
    ohlcv_dict = {
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Vol': 'sum'}

    def __init__(self):
        self.exchanges = self.load_exchanges()
        self.required_timeframes = self.load_required_timeframes()

    def get_last_timestamp(self, symbol: str, source):
        """ Return last stored m1 candle timestamp from local datastore.
            Note: source parameter needs to be a reference
            to the exchange object, not a string
        """

        # if a datastore exists, get the last stored timestamp
        if self.check_datastore_exists(symbol, source.get_name()):
            with open(
                './data/' + source.get_name() + '/' + symbol +
                    '_' + source.get_name() + '.csv') as f:
                        try:

                            # parse csv as a list of lists
                            datastore = csv.reader(f)
                            datastore = list(datastore)

                            # get first element of last element
                            text = datastore[-1][0]

                            # format date to UTC human readable
                            date = datetime.datetime.utcfromtimestamp(
                                int(text) / 1000.0).strftime(
                                    '%H:%M:%S %d-%m-%Y')

                            print(
                                source.get_name() + "_" + symbol + "_" +
                                " last update: UTC " + str(date))

                            return text

                        except Exception as e:
                            print(e)
        else:
            print(
                "No datastore exists for " + symbol + '_' +
                source.get_name() + ".")

    def update_existing_datastore(self, symbol, source, timeframe, df):
        """ Append new dataframe to existing CSV.
            Param 'df': dataframe of new candles from last stored timestamp
        """

        # drop any duplicate timestamps
        df.drop_duplicates()

        # if the datastore exists, open it in append mode
        if self.check_datastore_exists(symbol, source, timeframe):
            if isinstance(df, pd.DataFrame):
                with open(
                    './data/' + source + '/' + symbol +
                    '_' + source + '_' + timeframe +
                        '.csv', 'a', newline='') as f:

                            # append the data to the existing CSV
                            df.to_csv(f, header=False)

                            print(
                                symbol + "_" + source + "_" +
                                timeframe + " update complete.")
        else:
            print(
                "Update failed for " + symbol + '_' +
                source + ".")

    def standardise(self):
        """ Reformat all existing datastores for consistent
            index typing and remove any duplicate entries.
            this works when executed one level up from "data" directory
        """

        # get list of subdirectories within "data" subdirectory
        subdirectories = [f.path for f in os.scandir("data") if f.is_dir()]
        for directory in subdirectories:

            # get list of files within each subdirectory of "data"
            files = os.listdir(directory)
            for file in files:

                try:
                    # open .csv files only, case-agnostic
                    if file.lower().endswith('.csv'):
                        print(directory + "\\" + file)
                        with open(directory + "\\" + file) as f:

                            # print file name
                            print(file)

                            # load csv into dataframe
                            df = pd.read_csv(f)
                            df.set_index("Time", inplace=True)

                            # unix ms timestamps    = float or int
                            # datetime timestamp    = string
                            # if unix timestamp, convert ms to datetime
                            if (
                                type(df.index[0]) is numpy.float64 or
                                    numpy.int64):
                                df.index = pd.to_datetime(df.index, unit='ms')

                            # remove duplicates
                            df.drop_duplicates(keep='first', inplace=True)

                            # overwrite existing files
                            df.to_csv(directory + "\\" + file)

                except Exception as e:
                    print(e)
                    return False
        return True

    def check_datastore_exists(self, symbol, source, timeframe):
        """ Checks if local datastore exists for given symbol
        """

        if os.path.isfile(
            './data/' + source.get_name() + '/' + symbol + '_' +
                source + '.csv'):
            return True
        else:
            return False

    def load_exchanges(self):
        """ Returns a list of all exchange objects
            TODO read from file
        """

        exchanges = list()
        exchanges.append(Bitfinex())

        return exchanges

    def load_required_timeframes(self):
        """ Return list of timeframes required for analysis
            Includes native and non-native timeframes
        """

        timeframes = []
        with open("required_timeframes.txt", "r") as f:
            for line in f:
                # list of strings by line
                timeframes.append(line.strip())

        return timeframes

    def resample(self, symbol, source, target_tf):
        """ Return dataframe of resampled candles.
        """

        origin_data = self.transform_dict.get(target_tf)

        df = pd.read_csv(
            './data/' + source.get_name() + '/' + symbol +
            '_' + source.get_name() + '_' + origin_data + '.csv')

        # reformat time column, it gets read as a string otherwise
        df["Time"] = pd.to_datetime(df["Time"], unit='ms')

        # adjust for irregular OCHLV format if required
        if source.get_name() == "Bitfinex":
            df.columns = ["Time", "Open", "Close", "High", "Low", "Vol"]
        # otherwise use standard OHLCV format
        else:
            df.columns = ["Time", "Open", "High", "Low", "Close", "Vol"]

        # set the index to timestamp column``````````````````````
        df.set_index("Time", inplace=True)

        # round all values to 2 decimal places
        df = df.round(2)

        # upsample origin data to target timeframe
        try:
            df = df.resample(target_tf).agg(self.ohlcv_dict).dropna(how='any')
        except Exception as e:
            print(e)

        return df

    def print_all_datastores(self):
        """ print list of all local datastores.
        """
        pass
