from bitmex_ws import Bitmex_WS
import logging
import multiprocessing


logger = logging.getLogger()
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)

symbols = ("XBTUSD", "ETHUSD")
channels = ("trade", "orderBookL2")
URL = 'wss://testnet.bitmex.com/realtime'
api_key = None
api_secret = None


tt = Bitmex_WS(logger, symbols, channels, URL, api_key, api_secret)
