import logging

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s:%(levelname)s:%(module)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)

BASE_URL = "https://www.bitmex.com/"
WS_URL = "wss://www.bitmex.com/realtime"
