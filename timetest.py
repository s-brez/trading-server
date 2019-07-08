from bitmex import Bitmex
from datetime import datetime
import logging
import requests
import pandas as pd
import numpy as np

logger = logging.getLogger()
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)

MAX_BARS = 750

url1 = "https://www.bitmex.com/api/v1"
url2 = "/trade/bucketed?binSize=1h&symbol=XBT&filter=&count=10&start=&reverse=true"

bitmex = Bitmex(logger)

response = requests.get(url1 + url2).json()

df = pd.DataFrame(response)
df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

print(df['timestamp'][0])


