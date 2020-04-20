from pymongo import MongoClient
import pandas as pd
from datetime import datetime


db_client = MongoClient('mongodb://127.0.0.1:27017/')
db = db_client['asset_price_master']
coll = db['BitMEX']


def remove_element(dictionary, element):
    new_dict = dict(dictionary)
    del new_dict[element]
    return new_dict

# insert a document
# bar = {
#     'symbol': 'XBTUSD', 'timestamp': 1565540761, 'open': 11466,
#     'high': 11466.5, 'low': 1141, 'close': 11461, 'volume': 1146476}
# x = coll.insert_one(bar)
# print(x)

# match multiple conditions
# query = {"$and": [
#     {"symbol": "XBTUSD"},
#     {"high": None},
#     {"low": None},
#     {"open": None},
#     {"close": None},
#     {"volume": 0}]}
# result = coll.find(query)
# count = coll.count_documents(query)
# # print(coll.count_documents({}))
# # timestamps = [doc['timestamp'] for doc in result]
# for doc in result:
#     print(doc)

# return duplicates
# cursor = coll.aggregate([
#     {"$match": {"timestmp": {"$ne": "null"}}},
#     {"$match": {"symbol": "XBTUSD"}},
#     {"$group": {"_id": "$timestamp", "count": {"$sum": 1},}},
#     {"$match": {"count": {"$gt": 1}}},
#     {"$sort": {"timestamp": -1}},
#     {"$project": {"timestamp": "$_id", "_id": 0}}], allowDiskUse=True)

# cursor = list(cursor)

# for doc in cursor:
#     print(doc)

# print("Duplicates:", len(cursor))

# sort and limit results with projection


size = 15

result = coll.find(
    {"symbol": "XBTUSD"}, {
        "_id": 0, "symbol": 0}).limit(
            size).sort([("timestamp", -1)])

new_bar = {
    'symbol': "XBTUSD", 'timestamp': 1579897620, 'open': 8468, 'high': 8468,
    'low': 8464.5, 'close': 8465, 'volume': 1583863
    }

rows = [remove_element(new_bar, "symbol")]

for doc in result:
    print(datetime.fromtimestamp(doc['timestamp']))
    print(doc)
    # rows.append(doc)

# df = pd.DataFrame(rows)

# df['timestamp'] = df['timestamp'].apply(
#     lambda x: datetime.fromtimestamp(x))

# df.set_index("timestamp", inplace=True)

# print(df)
