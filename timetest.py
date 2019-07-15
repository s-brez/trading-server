from bitmex import Bitmex
from bitmex_websocket import BitMEXWebsocket
import datetime
import logging
import requests
import pandas as pd
import numpy as np

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


"""
Grabbing bar buckets via REST polling then parsing to dataframe
"""

MAX_BARS = 750

timeframe = "1h"
symbol = "XBT"
bucket_size = 10
base_url = "https://www.bitmex.com/api/v1"
bars_url = "/trade/bucketed?binSize="
payload = "{}{}{}&symbol={}&filter=&count={}&start=&reverse=true".format(
    base_url, bars_url, timeframe, symbol, bucket_size)

print(payload)
response = requests.get(payload).json()

df = pd.DataFrame(response)
df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

modified_dates = []
for i in df['timestamp']:
    new_datestring = ""
    for char in i:
        if not(char.isalpha()):
            new_datestring += char
    modified_dates.append(new_datestring)

df.timestamp = modified_dates
print(df)


