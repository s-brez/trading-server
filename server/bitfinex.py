import time
import sys
import requests
import traceback
import logging
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

    log = None
    url = ""
    name = ""
    native_timeframes = ()
    non_native_timeframes = ()
    ohlcv_dict = {}
    timeframe_targettime = {}
    usd_pairs = []
    btc_pairs = []
    eth_pairs = []

    def __init__(self):

        self.log = logging.getLogger("server.exchange.Bitfinex")

        logging.info("Instantiate Bitfinex class")

        self.url = 'https://api-pub.bitfinex.com/v2/'

        self.name = "Bitfinex"

        # Bitfinex native OHLCV timeframes
        self.native_timeframes = (
            "1m", "5m", "15m", "30m", "1h", "3h",
            "6h", "12h", "1D", "7D", "1M")

        # timeframes to be transformed from source data
        self.non_native_timeframes = (
            "2h", "4h", "8h", "2D", "3D")

        # resampling dict
        self.ohlcv_dict = {
            'Open': 'first',
            'Close': 'last',
            'High': 'max',
            'Low': 'min',
            'Vol': 'sum'}

        # timeframe : seconds per timeframe unit
        self.timeframe_targettime = {
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

        self.usd_pairs = [
            "BTCUSD", "ETHUSD", "LTCUSD", "EOSUSD", "XRPUSD", "NEOUSD",
            "USTUSD", "BABUSD", "IOTUSD", "ETCUSD", "DSHUSD", "OMGUSD",
            "XMRUSD", "ZECUSD", "BABUSD", "BSVUSD", "BTGUSD", "ZRXUSD"]

        self.btc_pairs = [
            "ETHBTC", "EOSBTC", "XRPBTC", "LTCBTC", "BABBTC", "NEOBTC",
            "ETCBTC", "OMGBTC", "XMRBTC", "IOTBTC", "DSHBTC", "ZECUSD",
            "BSVBTC"]

        self.eth_pairs = [
            "EOSETH"]

    def get_all_candles(self, symbol, timeframe):
        """ Returns dataframe of all candle data of a given asset.
            Use this when creating new datastore.
        """

        logging.info("Call get_all_candles()")

        # first candle timestamp of given asset
        start = self.get_genesis_timestamp(symbol, timeframe)

        # one timeframe unit prior to current time.
        targettime = self.timeframe_to_targettime(timeframe)

        #  set requested candle block size according to timeframe
        limit = self.calculate_block_limit(timeframe)

        # temporary storage to aggregate API responses
        frames = []

        time.sleep(7)
        count = 1

        print(
            "Fetching historical " + timeframe +
            " data for " + symbol + "_Bitfinex.")

        while start < targettime:
            try:
                # poll API
                logging.info("Poll API")
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
                logging.info("Append new data to temp storage")
                frames.extend(response)

                # get the last stored timestamp, the
                # first item of last list in frames[]
                start = frames[-1][0]
                check = frames[-2][0]

                print(
                    "Fetching block " + str(count) + " starting: " +
                    (str(start)) + " (" + str(limit) + " candles per block)")

                count += 1

                # error handling if the new start timestamp is the
                # same as the last stored timestamp
                if start == check:
                    logging.info("Duplicate response received")

                # wait between blocks to avoid API rate limit
                time.sleep(7)

            # debugging stuff
            except Exception as e:
                logging.exception(e)
                logging.debug(
                    traceback.print_exc(
                        limit=None, file=None, chain=True))
                logging.debug("Last timestamp requested: " + start)
                print("Failed to fetch data.")
                sys.exit()

        # finished fetching all candles, now return a formatted dataframe
        logging.info("Format dataframe from temp data storage.")
        df = pd.DataFrame(frames)
        df.columns = ["Time", "Open", "Close", "High", "Low", "Volume"]
        df.set_index(['Time'], inplace=True)
        logging.info(df.head(2))
        logging.info(df.tail(2))
        return df

    def get_new_candles(self, symbol, timeframe, start):
        """ Returns dataframe of candle data from start timestamp to
            current time. Use to update existing datastore.
        """

        logging.info("Call get_new_candles()")

        # one timeframe unit prior to current time.
        targettime = self.timeframe_to_targettime(timeframe)

        # set requested candle block size according to timeframe
        limit = 0

        #  set requested candle block size according to timeframe
        limit = self.calculate_block_limit(timeframe)

        # temporary storage to aggregate API responses
        frames = []

        count = 0
        check = 0

        time.sleep(5)

        print('Start update ' + symbol + '_' + timeframe + ".")

        while start < targettime:
            try:
                print(
                    "Update " + str((count)) + " starting: " +
                    (str(start)))

                # poll API
                logging.info("Poll API")
                response = requests.get(
                    self.url + "candles/trade:" + timeframe +
                    ':t' + symbol + '/hist?limit=' + str(limit) + '&start=' +
                    str(start) + '&sort=1').json()

                # store API url string for debug
                API_url = (
                    self.url + "candles/trade:" + timeframe +
                    ':t' + symbol + '/hist?limit=' + str(limit) + '&start=' +
                    str(start) + '&sort=1')

                # only append candle blocks to frames if a new
                # block has been fetched, dont append duplicates
                if start != check:
                    logging.info("Append new data to temp storage")
                    frames.extend(response)

                # reset start timestamp to the first element of
                # the last stored list in frames[]
                start = frames[-1][0]
                check = frames[-2][0]

                # error loggin if the new start timestamp is the
                # same as the second last stored timestamp
                if start == check:
                    logging.info("Duplicate response received")
                    logging.info(
                        "start: " + str(start) + " check: " + str(check))
                    logging.debug(response)
                    logging.debug(API_url)
                    logging.debug(
                        "Update failure during " + self.name + " " + symbol +
                        " " + timeframe)
                    sys.exit()

                # wait between blocks to avoid API rate limit
                time.sleep(10)

                count += 1

            except Exception as e:
                logging.exception(e)
                sys.exit()

        try:
            df = pd.DataFrame(frames)
            df.columns = ["Time", "Open", "Close", "High", "Low", "Volume"]
            df.set_index(['Time'], inplace=True)
            logging.info("Format dataframe from temp data storage.")
            logging.info(df.head(2))
            logging.info(df.tail(2))
            return df

        except ValueError as e:
            logging.info(e)

    def get_ticker_values(self, symbol):
        """ Returns dataframe of ticker values of given asset.
            TODO: create variant that takes a list of all ticker codes.
        """

        logging.info("Call get_ticker_values()")

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

        logging.info("Call get_genesis_candle()")

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

        logging.info("Call get_genesis_timestamp()")
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
            if(response != ""):
                logging.info("API response: " + response)
                logging.info("Timestamp: " + timestamp)
                logging.info(API_url)
                logging.info(e)

    def timeframe_to_targettime(self, timeframe):
        """ Returns unix timestamp one unit before current
            time based on given timeframe
        """
        logging.info("Call timeframe_to_targettime()")
        targettime = int()

        try:
            targettime = (
                time.time() - int(
                    self.timeframe_targettime.get(timeframe))) * 1000

            return targettime

        except Exception as e:
            logging.info(e)
            sys.exit()

    def calculate_block_limit(self, timeframe):

        logging.info("Call calculate_block_limit()")
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
