import time
import requests
import traceback
import pandas as pd

from exchange_types import CryptoExchange


class Bitfinex(CryptoExchange):
    """ Bitfinex exchange model
        Poll Bitfinex API to fetch candle, orderbook, wallet and other data.

        Ticker API endpoint:

        Example:
            https://api-pub.bitimeframeinex.com/v2/tickers?symbols=tBTCUSD
        Returns:
            JSON: [[SYMBOL, BID, BID_SIZE, ASK, ASK_SIZE, DAILY_CHANGE,
            DAILY_CHANGE_PERC, LAST_PRICE, VOLUME, HIGH, LOW],]

        Candle API endpoint:

        Example:
            https://api-pub.bitimeframeinex.com/v2/candles/trade:1m:tBTCUSD
            /hist?limit=100&start=1549086300000&end=1549174500000
        Returns:
            JSON: [[MTS, OPEN, CLOSE, HIGH, LOW, VOLUME],]
    """

    url = 'https://api-pub.bitfinex.com/v2/'

    name = "Bitfinex"

    native_timeframes = (  # Bitfinex native OHLCV timeframes.
        "1m", "5m", "15m", "30m", "1h", "3h",
        "6h", "12h", "1D", "7D", "1M")

    non_native_timeframes = (  # timeframes to be transformed from source data
        "2h", "4h", "8h", "2D", "3D")

    ohlcv_dict = {  # for resampling of data, show
        'Open': 'first',
        'Close': 'last',
        'High': 'max',
        'Low': 'min',
        'Vol': 'sum'}

    timeframe_targettime = {  # timeframe : seconds per timeframe unit
        "1m": 60,
        "5m": 300,
        "15m": 900,
        "30m": 1800,
        "1h": 3600,
        "2h": 7200,
        "3h": 10800,
        "4h": 14400,
        "6h": 21600,
        "8h": 28800,
        "12h": 43200,
        "1D": 86400,
        "2D": 172800,
        "3D": 259200,
        "1W": 604800,
        "7D": 604800,
        "1M": 2629746}

    usd_pairs = [
        "BTCUSD", "ETHUSD", "LTCUSD", "EOSUSD", "XRPUSD", "NEOUSD",
        "USTUSD", "BABUSD", "IOTUSD", "ETCUSD", "DSHUSD", "OMGUSD",
        "XMRUSD", "ZECUSD", "BABUSD", "BSVUSD", "BTGUSD", "ZRXUSD"]

    btc_pairs = [
        "ETHBTC", "EOSBTC", "XRPBTC", "LTCBTC", "BABBTC", "NEOBTC",
        "ETCBTC", "OMGBTC", "XMRBTC", "IOTBTC", "DSHBTC", "ZECUSD",
        "BSVBTC"]

    eth_pairs = [
        "EOSETH"]

    def __init__(self):
        pass

    def get_all_candles(self, symbol, timeframe):
        """ Returns dataframe of all candle data of a given asset.
            Use this when creating new datastore.
        """

        # first candle timestamp of given asset
        start = self.get_genesis_timestamp(symbol, timeframe)

        # one timeframe unit prior to current time.
        targettime = self.timeframe_to_targettime(timeframe)

        #  set requested candle block size according to timeframe
        limit = self.calculate_block_limit(timeframe)

        # temporary storage to aggregate API responses
        frames = []

        time.sleep(3)
        count = 1

        print(
            "Fetching historical " + timeframe +
            " data for " + symbol + "_Bitfinex.")

        while start < targettime:
            try:
                # poll API
                response = requests.get(
                    self.url + "candles/trade:" +
                    timeframe + ':t' + symbol + '/hist?limit=' +
                    str(limit) + '&start=' + str(start) + '&sort=1').json()

                # save API url string for debug
                API_url = (
                    self.url + "candles/trade:" + timeframe + ':t' +
                    symbol + '/hist?limit=' + str(limit) + '&start=' +
                    str(start) + '&sort=1')

                # append new batches of candles to frames
                frames.extend(response)

                # get the last stored timestamp, the
                # first item of last list in frames[]
                start = frames[-1][0]
                check = frames[-2][0]
                print(str(count) + ": " + (str(start)))
                count += 1

                # write to file and return if poll fetches same data
                if start == check:
                    df = pd.DataFrame(frames)
                    df.columns = [
                        "Time", "Open", "Close", "High", "Low", "Volume"]
                    df.set_index(['Time'], inplace=True)
                    print(df.tail())
                    print(frames)
                    return df

                # wait between blocks to avoid API rate limit
                time.sleep(4)

            # debugging stuff
            except Exception as e:
                print(e)
                traceback.print_exc(limit=None, file=None, chain=True)
                print(API_url)
                print(response)
                print(start)
                print(frames)
                # exit to prevent rate limit
                exit()

        # finished fetching all candles, now return a formatted dataframe
        df = pd.DataFrame(frames)
        df.columns = ["Time", "Open", "Close", "High", "Low", "Volume"]
        df.set_index(['Time'], inplace=True)
        return df

    def get_new_candles(self, symbol, timeframe, start):
        """ Returns dataframe of candle data from start timestamp to
            current time. Use to update existing datastore.
        """

        # one timeframe unit prior to current time.
        targettime = self.timeframe_to_targettime(timeframe)

        # set requested candle block size according to timeframe
        limit = 0

        #  set requested candle block size according to timeframe
        limit = self.calculate_block_limit(timeframe)

        # temporary storage to aggregate API responses
        frames = []

        error_count = 0
        count = 1

        print('Start update ' + symbol + '_' + timeframe + ".")
        time.sleep(3)
        while start < targettime:
            try:
                # TODO: Add capability to resume from rate limit/error
                time.sleep(3)

                # poll API
                response = requests.get(
                    self.url + "candles/trade:" + timeframe +
                    ':t' + symbol + '/hist?limit=' + str(limit) + '&start=' +
                    str(start) + '&sort=1').json()

                # store API url string for debug
                API_url = (
                    self.url + "candles/trade:" + timeframe +
                    ':t' + symbol + '/hist?limit=' + str(limit) + '&start=' +
                    str(start) + '&sort=1')
                frames.extend(response)

                # first element of last list
                start = frames[-1][0]
                count += 1
            except Exception as e:
                print(e)
                print(API_url)
                print("Last timestamp: " + str(start))
                error_count += 1
                if error_count > 3:
                    break
                # TODO: Add capability to save "start" and e to file
        try:
            df = pd.DataFrame(frames)
            df.columns = ["Time", "Open", "Close", "High", "Low", "Volume"]
            df.set_index(['Time'], inplace=True)
            return df
        except ValueError as e:
            # print(e)
            print(symbol + ' data is up to date')

    def get_ticker_values(self, symbol):
        """ Returns dataframe of ticker values of given asset.
            TODO: create variant that takes a list of all ticker codes.
        """

        response = requests.get(self.url + "tickers?symbols=t" + symbol).json()
        df = pd.DataFrame(response)

        # set columns
        df.columns = [
            "Ticker", "Bid", "Bid_size", "Ask",
            "Ask_size", "Daily_change", "Daily_change_%",
            "Last_price", "Vol", "High", "Low"]

        # reorder columns
        cols = [
            "Ticker", "Last_price", "Daily_change",
            "High", "Low", "Daily_change_%", "Bid",
            "Bid_size", "Ask", "Ask_size", "Vol"]
        df = df[cols]

        # set ticker code manually to avoid "t" prefix
        df.at[0, "Ticker"] = symbol

        # change column data type
        df.Daily_change = df.Daily_change.astype(str)

        # append '%' to Daily change cell value"
        df.at[0, "Daily_change"] = str(df.at[0, "Daily_change"]) + '%'

        # set index and return ticker data as formatted dataframe
        df.set_index("Ticker", inplace=True)
        return df

    def get_genesis_candle(self, symbol, timeframe):
        """ Returns dataframe containing first available
            1 min candle of given asset.
        """

        # poll the API
        response = requests.get(
            self.url + "candles/trade:1m:t" + symbol +
            '/hist?limit=1&sort=1').json()

        # store response in a dataframe
        df = pd.DataFrame(response)

        # format the dataframe
        df.columns = ["Time", "Open", "Close", "High", "Low", "Vol"]
        df.set_index("Time", inplace=True)

        return df

    def get_genesis_timestamp(self, symbol, timeframe):
        """ Returns string timestamp of first available
            1 min candle of a given asset
        """

        timestamp = int()

        try:
            # poll API
            response = requests.get(
                self.url + "candles/trade:1m:t" + symbol +
                '/hist?limit=1&sort=1').json()

            # store API request string for debug
            API_url = (
                self.url + "candles/trade:1m:t" + symbol +
                '/hist?limit=1&sort=1')

            # get timestamp, the first item of first list
            timestamp = response[0][0]

            return timestamp

        except Exception as e:
            print("API response: " + response)
            print("Timestamp: " + timestamp)
            print("API url string: " + API_url)
            print(e)
            traceback.print_exc(limit=None, file=None, chain=True)

    def timeframe_to_targettime(self, timeframe):
        """ Returns unix timestamp one unit before current
            time based on given timeframe
        """

        targettime = int()

        try:
            targettime = (
                time.time() - int(
                    self.timeframe_targettime.get(timeframe))) * 1000

            return targettime

        except Exception as e:
            print(targettime)
            print(e)
            exit()

    def calculate_block_limit(self, timeframe):

        limit = 0

        # intradaily candle block size
        if self.timeframe_targettime.get(timeframe) <= 43200:
            limit = 5000

        # intraweekly candle block size
        if (
            self.timeframe_targettime.get(timeframe) > 43200 and
                self.timeframe_targettime.get(timeframe) <= 60480):
            limit = 500

        # intramonthly candle block size
        if (
            self.timeframe_targettime.get(timeframe) > 60480 and
                self.timeframe_targettime.get(timeframe) <= 262976):
            limit = 24

        return limit

    def get_native_timeframes(self):
        """ Returns list of local-to-exchange timeframes
        """
        return self.native_timeframes

    def get_non_native_timeframes(self):
        """ Returns list of non-native timeframes
        """
        return self.non_native_timeframes

    def get_usd_pairs(self):
        """ Returns list of usd margin pairs
        """
        return self.usd_pairs

    def get_btc_pairs(self):
        """ Returns list of btc margin pairs
        """
        return self.btc_pairs

    def get_eth_pairs(self):
        """ Returns list of eth margin pairs
        """
        return self.eth_pairs

    def get_all_pairs(self):
        """ Returns all pairs as a list.
        """

        return self.usd_pairs + self.btc_pairs + self.eth_pairs

    def get_name(self):
        """ Return name
        """

        return self.name
