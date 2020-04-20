from datetime import date, datetime, timedelta
from pymongo import MongoClient
from dateutil import parser
import pandas as pd
import calendar
import time


db_client = MongoClient('mongodb://127.0.0.1:27017/')
db = db_client['asset_price_master']
coll = db['BitMEX']

tf = "30Min"
symbol = "XBTUSD"

RESAMPLE_KEY = {
    'open': 'first', 'high': 'max', 'low': 'min',
    'close': 'last', 'volume': 'sum'}

result = coll.find(
    {"symbol": symbol}, {
        "_id": 0, "symbol": 0}).sort([("timestamp", -1)])

# Pass cursor to DataFrame constructor
df = pd.DataFrame(result)

# Format time column
df['timestamp'] = df['timestamp'].apply(
    lambda x: datetime.fromtimestamp(x))

# Set index
df.set_index("timestamp", inplace=True)

# Downsample 1 min data to target timeframe
resampled_df = pd.DataFrame()
try:
    resampled_df = (df.resample(tf).agg(RESAMPLE_KEY))
except Exception as exc:
    print("Resampling error", exc)

resampled_df.to_csv(symbol + tf + ".csv")
