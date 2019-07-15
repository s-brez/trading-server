
from bitmex import Bitmex
from bitmex_websocket import BitMEXWebsocket
import datetime
import logging
import requests
import pandas as pd
import numpy as np
from dateutil import parser
from time import sleep

"""
For websocket tick data streaming
"""

logger = logging.getLogger()
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)

bitmex = Bitmex(logger)

ws = BitMEXWebsocket(
    endpoint="https://testnet.bitmex.com/api/v1",
    symbol="XBTUSD", api_key=None, api_secret=None)

ticks = []
ticks_minute_elapsed = []
count = 0

while ws.ws.sock.connected:
    # get tick data in the first second of every minute
    if datetime.datetime.utcnow().second <= 1:
        # only update if at least one minute elapsed since ws start
        if count >= 1:
            ticks = ws.recent_trades()
            # isolate the just-elapsed minute's ticks
            for tick in ticks:
                ts = parser.parse(tick['timestamp'])
                if ts.minute == datetime.datetime.utcnow().minute - 1:
                    ticks_minute_elapsed.append(tick)
        count += 1

        for tick in ticks_minute_elapsed:
            print(tick)

        # sleep until just before the next minute ticks over
        now = datetime.datetime.utcnow().second
        delay = 60 - now - 1
        sleep(delay)
    sleep(0.05)

"""
Fetch bar buckets via REST polling, then parse to dataframe
"""

# MAX_BARS_PER_REQUEST = 750
# BASE_URL = "https://www.bitmex.com/api/v1"
# BARS_URL = "/trade/bucketed?binSize="

# timeframe = "1h"
# symbol = "XBT"
# bucket_size = 10

# payload = "{}{}{}&symbol={}&filter=&count={}&start=&reverse=true".format(
#     BASE_URL, BARS_URL, timeframe, symbol, bucket_size)

# response = requests.get(payload).json()

# df = pd.DataFrame(response)
# df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

# modified_dates = []
# for i in df['timestamp']:
#     new_datestring = ""
#     for char in i:
#         if not(char.isalpha()):
#             new_datestring += char
#     modified_dates.append(new_datestring)

# df.timestamp = modified_dates
# print(df)


