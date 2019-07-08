import time
import sys
import requests
import traceback
import pandas as pd

from exchange import Exchange


class Bitfinex(Exchange):
    """ Bitfinex wrapper
        Candle API Example:
            https://api-pub.bitimeframeinex.com/v2/candles/trade:1m:tBTCUSD
            /hist?limit=100&start=1549086300000&end=1549174500000
        Returns:
            JSON: [[MTS, OPEN, CLOSE, HIGH, LOW, VOLUME],]
    """

    url = 'https://api-pub.bitfinex.com/v2/'
    name = "Bitfinex"

    ohlcv_dict = {
        'Open': 'first',
        'Close': 'last',
        'High': 'max',
        'Low': 'min',
        'Vol': 'sum'}

    pairs = [
        "BTCUSD", "ETHUSD", "LTCUSD", "EOSUSD", "XRPUSD", "NEOUSD",
        "USTUSD", "BABUSD", "IOTUSD", "ETCUSD", "DSHUSD", "OMGUSD",
        "XMRUSD", "ZECUSD", "BABUSD", "BSVUSD", "BTGUSD", "ZRXUSD",
        "ETHBTC", "EOSBTC", "XRPBTC", "LTCBTC", "BABBTC", "NEOBTC",
        "ETCBTC", "OMGBTC", "XMRBTC", "IOTBTC", "DSHBTC", "ZECUSD",
        "BSVBTC", "EOSETH"]

    def __init__(self):
        super()

    def get_candles(self, symbol: str, start: int, finish: int):
        """ Return dataframe of 1min OHLCV candle data for specified period
        """

        # logging.info("Call get_candles()")

        # while start < targettime:
        #     try:
        #         # poll API
        #         logging.info("Poll API")
        #         response = requests.get(
        #             self.url + "candles/trade:" +
        #             timeframe + ':t' + symbol + '/hist?limit=' +
        #             str(limit) + '&start=' + str(start) + '&sort=1').json()

        #         # save API url string for debug
        #         API_url = (
        #             self.url + "candles/trade:" + timeframe + ':t' +
        #             symbol + '/hist?limit=' + str(limit) + '&start=' +
        #             str(start) + '&sort=1')

        #         # append new batches of candles to frames
        #         logging.info("Append new data to temp storage")
        #         frames.extend(response)

        #         # get the last stored timestamp, the
        #         # first item of last list in frames[]
        #         start = frames[-1][0]
        #         check = frames[-2][0]

        #         print(
        #             "Fetching block " + str(count) + " starting: " +
        #             (str(start)) + " (" + str(limit) + " candles per block)")

        #         count += 1

        #         # error handling if the new start timestamp is the
        #         # same as the last stored timestamp
        #         if start == check:
        #             logging.info("Duplicate response received")

        #         # wait between blocks to avoid API rate limit
        #         time.sleep(7)

        #     # debugging stuff
        #     except Exception as e:
        #         logging.exception(e)
        #         logging.debug(
        #             traceback.print_exc(
        #                 limit=None, file=None, chain=True))
        #         logging.debug("Last timestamp requested: " + start)
        #         print("Failed to fetch data.")
        #         sys.exit()

        # # finished fetching all candles, now return a formatted dataframe
        # logging.info("Format dataframe from temp data storage.")
        # df = pd.DataFrame(frames)
        # df.columns = ["Time", "Open", "Close", "High", "Low", "Volume"]
        # df.set_index(['Time'], inplace=True)
        # logging.info(df.head(2))
        # logging.info(df.tail(2))
        # return df

    def get_first_timestamp(self, symbol: str):
        """ Returns int timestamp of first available
            1 min candle of a given asset
        """

        timestamp = 0
        try:
            # poll API
            response = requests.get(
                self.url + "candles/trade:1m:t" + symbol +
                '/hist?limit=1&sort=1').json()

            # get timestamp, the first item of first list
            timestamp = response[0][0]

            return timestamp
        except Exception as e:
            pass

    def get_pairs(self):
        """ Returns list of pairs
        """
        return self.pairs

    def get_name(self):
        """ Return name
        """
        return self.name
