from pymongo import MongoClient
import pandas as pd
from datetime import datetime
import json


db_client = MongoClient('mongodb://127.0.0.1:27017/')
db_other = db_client['holdings_trades_signals_master']
coll = db_other['signals']
# coll = db_other['trades']
# coll = db_other['portfolio']

result = coll.find({}, {"_id": 0}).sort([("entry_timestamp", -1)])  # signals
# result = coll.find({}, {"_id": 0}).sort([("id", -1)])  # portfolio
result = coll.find({}, {"_id": 0}).sort([("trade_id", -1)])  # trades

[print((json.dumps(i, indent=2))) for i in result]
