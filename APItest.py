
from bitmex import Bitmex
from bitmex_websocket import BitMEXWebsocket
import datetime
import logging
import requests
import pandas as pd
from dateutil import parser
from time import sleep


MAX_BARS_PER_REQUEST = 750
BASE_URL = "https://www.bitmex.com/api/v1"
BARS_URL = "/trade/bucketed?binSize="
TIMESTAMP_FORMAT = '%Y-%m-%d%H:%M:%S.%f'


# def previous_minute():
#     timestamp = datetime.datetime.utcnow() - datetime.timedelta(minutes=1)
#     timestamp.replace(second=0, microsecond=0)
#     return timestamp

"""
For websocket tick data streaming
"""

# logger = logging.getLogger()
# l ogger.setLevel(logging.INFO)
# ch = logging.StreamHandler()
# formatter = logging.Formatter(
#     "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
# ch.setFormatter(formatter)
# logger.addHandler(ch)

# bitmex = Bitmex(logger)

# ws = BitMEXWebsocket(
#     endpoint="https://testnet.bitmex.com/api/v1",
#     symbol="XBTUSD", api_key=None, api_secret=None)

# timestamp_format = '%Y-%m-%d%H:%M:%S.%f'
# ticks = []
# ticks_minute_elapsed = []
# count = 0
# bar = {}

# while ws.ws.sock.connected:
#     # get tick data at first second of every minute
#     if datetime.datetime.utcnow().second <= 1:
#         # only get ticks after one minute passed
#         if count >= 1:
#             ticks = ws.recent_trades()
#             # grab only the just-elapsed minute's ticks
#             # TODO start from end of list
#             for tick in ticks:
#                 ts = parser.parse(tick['timestamp'])
#                 if ts.minute == datetime.datetime.utcnow().minute - 1:
#                     ticks_minute_elapsed.append(tick)
#             # get open, high, low and close prices
#             prices = [i['price'] for i in ticks_minute_elapsed]
#             open_price = ticks_minute_elapsed[0]['price']
#             high_price = max(prices)
#             low_price = min(prices)
#             close_price = ticks_minute_elapsed[-1]['price']
#             bar = {'symbol': 'XBTUSD',
#                    'timestamp': previous_minute(),
#                    'open': open_price,
#                    'high': close_price,
#                    'low': low_price,
#                    'close': close_price}
#             print(bar)

#         count += 1

#         # sleep until 1 second before the next minute starts
#         now = datetime.datetime.utcnow().second
#         delay = 60 - now - 1
#         sleep(delay)
#     sleep(0.05)

"""
Fetch bar buckets via REST polling, then parse to dataframe
"""

timeframe = "1h"
symbol = "XBT"
bucket_size = 10

payload = "{}{}{}&symbol={}&filter=&count={}&start=&reverse=true".format(
    BASE_URL, BARS_URL, timeframe, symbol, bucket_size)

response = requests.get(payload).json()

df = pd.DataFrame(response)
df = df[['timestamp', 'open', 'high', 'low', 'close']]

modified_dates = []
for i in df['timestamp']:
    new_datestring = ""
    for char in i:
        if not(char.isalpha()):
            new_datestring += char
    modified_dates.append(new_datestring)

df.timestamp = modified_dates
print(df)
