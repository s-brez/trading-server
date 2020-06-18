from datetime import timezone, datetime, timedelta
from pymongo import MongoClient, errors
from requests import Request, Session
from requests.auth import AuthBase
from urllib.parse import urlparse
from dateutil import parser
import pandas as pd
import traceback
import requests
import hashlib
import json
import hmac
import time
import os


DB_URL = 'mongodb://127.0.0.1:27017/'
DB_PRICES = 'asset_price_master'
DB_OTHER = 'holdings_trades_signals_master'
DB_TIMEOUT_MS = 10


db_client = MongoClient(
    DB_URL,
    serverSelectionTimeoutMS=DB_TIMEOUT_MS)
db_prices = db_client[DB_PRICES]
db_other = db_client[DB_OTHER]

df = pd.read_csv('op_data.csv')

# Format time column.
df['timestamp'] = df['timestamp'].apply(
    lambda x: parser.parse(x))

# Set index
df.set_index("timestamp", inplace=True)

# Pad any null bars forward.
df.fillna(method="pad", inplace=True)

trade = {
  "trade_id": 91,
  "signal_timestamp": 1592390100,
  "type": "SINGLE_INSTRUMENT",
  "active": False,
  "venue_count": 1,
  "instrument_count": 1,
  "model": "EMA Cross - Testing only",
  "direction": "SHORT",
  "u_pnl": 0,
  "r_pnl": 0,
  "fees": 0,
  "exposure": None,
  "venue": "BitMEX",
  "symbol": "XBTUSD",
  "position": None,
  "order_count": 2,
  "orders": {
    "91-1": {
      "trade_id": 91,
      "order_id": "91-1",
      "timestamp": None,
      "avg_fill_price": None,
      "currency": None,
      "venue_id": None,
      "venue": "BitMEX",
      "symbol": "XBTUSD",
      "direction": "SHORT",
      "size": 100.0,
      "price": 9481.5,
      "order_type": "MARKET",
      "metatype": "ENTRY",
      "void_price": 9671.13,
      "trail": False,
      "reduce_only": False,
      "post_only": False,
      "batch_size": 0,
      "status": "UNFILLED"
    },
    "91-2": {
      "trade_id": 91,
      "order_id": "91-2",
      "timestamp": None,
      "avg_fill_price": None,
      "currency": None,
      "venue_id": None,
      "venue": "BitMEX",
      "symbol": "XBTUSD",
      "direction": "LONG",
      "size": 100.0,
      "price": 9671.13,
      "order_type": "STOP",
      "metatype": "STOP",
      "void_price": None,
      "trail": False,
      "reduce_only": True,
      "post_only": False,
      "batch_size": 0,
      "status": "UNFILLED"
    }
  }
}


