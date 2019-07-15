
from bitmex import Bitmex
from bitmex_websocket import BitMEXWebsocket
import datetime
import logging
import requests
import pandas as pd
import numpy as np
from dateutil import parser
from time import sleep
from exchange import Exchange


class Bitmex(Exchange):
    """BitMEX exchange model"""

    def __init__(self, logger):
        super()
        self.logger = logger

    logger = object
    name = "BitMEX"
    instruments = ["XBTUSD"]

    MAX_BARS_PER_REQUEST = 750
    API_KEY = None
    API_SECRET = None
    BASE_URL = "https://www.bitmex.com/api/v1"
    BARS_URL = "/trade/bucketed?binSize="

    def get_bars(self, instrument: str, start: int, finish: int):
        """
        """
        pass

    def get_last_bar(self, instrument: str, timeframe: str):
        """
        """
        pass

    def get_first_timestamp(self, instrument: str):
        """
        """
        pass

    def get_instruments(self):
        """
        """
        pass

    def subscribe_ws(self, instruments: list):
        """ """
        ws = BitMEXWebsocket(
            endpoint="https://testnet.bitmex.com/api/v1",
            symbol=instruments[0], api_key=API_KEY, api_secret=API_SECRET)

    def get_name(self):
        """
        """
        pass

