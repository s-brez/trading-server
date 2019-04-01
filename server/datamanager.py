import datetime
import os
import csv
import pandas as pd
import numpy


class Datamanager:
    """ Provides update, interpolation, storage, retrieval
        and transformation capability for locally stored asset data.
    """

    # dictionary for resampling
    ohlcv_dict = {
        'Open': 'first',
        'Close': 'last',
        'High': 'max',
        'Low': 'min',
        'Vol': 'sum'}

    # dictionary for timeframe transforms. 'target': 'source.get_name()'
    transform_dict = {
        '2h': '1h',
        '4h': '1h',
        '8h': '1h',
        '2D': '1D',
        '3D': '1D'
    }

    def __init__(self):
        pass

    def get_last_stored_timestamp(self, symbol, source, timeframe):
        """ Return last stored 1m candle timestamp from local datastore.
        """

        # if a datastore exists, get the last stored timestamp
        if self.check_datastore_exists(symbol, source.get_name(), timeframe):
            with open(
                './data/' + source.get_name() + '/' + symbol +
                    '_' + source.get_name() + '_' + timeframe + '.csv') as f:

                        try:
                            # parse CSV datastore as list
                            datastore = csv.reader(f)
                            datastore = list(datastore)

                            # get the first element of last entry
                            text = datastore[-1][0]

                            # TODO: add error handling here for
                            # if the source datastore is empty/corrupted
                            # (ie text returns None)

                            # format date to UTC human readable
                            date = datetime.datetime.utcfromtimestamp(
                                int(text) / 1000.0).strftime(
                                    '%H:%M:%S %d-%m-%Y')

                            print(
                                source.get_name() + "_" + symbol + "_" +
                                timeframe + " last update: UTC " + str(date))

                            return text

                        except Exception as e:
                            print(e)
                            print(text)
                            print(datastore)
        else:
            print(
                "No datastore exists for " + symbol + '_' +
                source.get_name() + ".")

    def create_new_datastore(self, symbol, source, timeframe, df):
        """ Save given dataframe to new CSV.
            Param 'df': dataframe of all x timeframe candles of an asset.
        """

        if self.check_datastore_exists(symbol, source, timeframe):
            print(
                "Datastore already exists for " + symbol +
                "_" + source + ". Overwriting old data.")

        # drop any duplicate timestamps
        df.drop_duplicates()

        # save to CSV
        df.to_csv(
            './data/' + source + '/' + symbol +
            '_' + source +
            '_' + timeframe + '.csv')

        print(
            "Created new datastore for " + symbol + "_" +
            source +
            '_' + timeframe + ".")

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

        print("Data standardisation complete.")
        return True

    def check_datastore_exists(self, symbol, source, timeframe):
        """ Checks if local datastore exists for given market.
            Return true if exists, false if not.
        """

        if os.path.isfile(
            './data/' + source + '/' + symbol + '_' +
                source + '_' + timeframe + '.csv'):
            return True
        else:
            return False

    def print_current_time(self):
        """ Print detailed time
        """

        time = datetime.datetime.now().strftime('%H:%M:%S %d-%m-%Y')
        timezone = datetime.datetime.now(
            datetime.timezone.utc).astimezone().tzinfo

        print('Local system time: ' + time + ' ' + str(timezone))

        return time

    def resample_data(self, symbol, source, target_tf):
        """ Resample existing candles to target timeframe candles.
            Return dataframe of resampled candles.
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

        # set the index to timestamp column
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
        """ Show list of all local datastores.
        """
        pass
