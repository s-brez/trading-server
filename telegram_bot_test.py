from datetime import timezone, datetime, timedelta
from pymongo import MongoClient, errors
from requests import Request, Session
from requests.auth import AuthBase
from urllib.parse import urlparse


import mplfinance as mpl
from io import BytesIO
from PIL import Image, ImageGrab, ImageDraw
import IPython.display as IPydisplay

from time import sleep
from threading import Thread
from messaging_clients import Telegram
import logging


from dateutil import parser
import pandas as pd
import numpy as np
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

db_client = MongoClient('mongodb://127.0.0.1:27017/')
db_other = db_client['holdings_trades_signals_master']
# coll = db_other['signals']
# coll = db_other['trades']
coll = db_other['portfolio']
# result = coll.find({}, {"_id": 0}).sort([("entry_timestamp", -1)])  # signals
result = list(coll.find({}, {"_id": 0}).sort([("id", -1)]))  # portfolio
# result = coll.find({}, {"_id": 0}).sort([("trade_id", -1)])  # trades


def setup_logger():
    log_level = logging.INFO
    logger = logging.getLogger()
    logger.setLevel(log_level)
    ch = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s:%(levelname)s:%(module)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S")
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # Supress requests/urlib3/connectionpool messages as
    # logging.DEBUG produces messages with each https request.
    logging.getLogger("urllib3").propagate = False
    requests_log = logging.getLogger("requests")
    requests_log.addHandler(logging.NullHandler())
    requests_log.propagate = False

    return logger


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
  "timeframe": "1Min",
  "entry_price": 9481.5,
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

SNAPSHOT_SIZE = 50

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

# Rename columns for mpl.
df.rename({'open': 'Open', 'high': 'High', 'low': 'Low',
           'close': 'Close', 'volume': 'Volume'}, axis=1, inplace=True)

# Use only the last x bars for the image.
df = df.tail(SNAPSHOT_SIZE)

entry = datetime.utcfromtimestamp(trade['signal_timestamp'])

# Add entry marker
entry_marker = [np.nan for i in range(SNAPSHOT_SIZE)]
entry_marker[-1] = trade['entry_price']


def create_addplots(df, mpl):
    """
    """

    adps, hlines = [], {'hlines': [], 'colors': [], 'linestyle': '--',
                        'linewidths': 0.75}

    # Add technical feature data (indicator values, etc).
    for col in list(df):
        if (
            col != "Open" and col != "High" and col != "Low"
                and col != "Close" and col != "Volume"):
            adps.append(mpl.make_addplot(df[col]))

    # Add entry marker
    color = 'limegreen' if trade['direction'] == "LONG" else 'crimson'
    adps.append(mpl.make_addplot(
        entry_marker, type='scatter', markersize=200, marker='.', color=color))

    return adps, hlines


adp, hlines = create_addplots(df, mpl)
style = mpl.make_mpf_style(gridstyle='')

filename = str(trade['trade_id']) + "_" + trade['model'] + "_" + trade['timeframe']
imgbuffer = BytesIO()
imgbuffer.name = filename

plot = mpl.plot(df, type='candle', addplot=adp, style=style, hlines=hlines,
                title="\n" + trade['model'] + ", " + trade['timeframe'],
                datetime_format='%d-%m %H:%M', figscale=1, savefig=imgbuffer,
                tight_layout=False)

portfolio = result

tg_bot = Telegram(setup_logger(), portfolio)
thread = Thread(target=lambda: tg_bot.run(), daemon=True)
thread.start()

print("Tg bot created in new thread")
sleep(4)

# hit /start in this time
# image = Image.open(imgbuffer)
# image.save(imgbuffer, "PNG")
# imgbuffer.seek(0)

bot_data = tg_bot.p.bot_data
print(bot_data)

# tg_bot.send_photo()
