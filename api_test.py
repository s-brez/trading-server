import requests
from dateutil import parser
import datetime
from pymongo import MongoClient
import pymongo
import datetime
import time


db_client = MongoClient('mongodb://127.0.0.1:27017/')
db = db_client['asset_price_master']
coll = db['BitMEX']
MAX_BARS_PER_REQUEST = 750
BASE_URL = "https://www.bitmex.com/api/v1"
BARS_URL = "/trade/bucketed?binSize="


def previous_minute():
    """ Return the previous minutes UTC ms epoch timestamp."""

    delta = datetime.datetime.utcnow().second
    timestamp = datetime.datetime.utcnow() - datetime.timedelta(seconds=delta)
    timestamp.replace(second=0, microsecond=0)
    # convert to epoch
    timestamp = int(timestamp.timestamp())
    # replace final digit with zero, can be 1 or more during a slow cycle
    timestamp_str = list(str(timestamp))
    timestamp_str[len(timestamp_str) - 1] = "0"
    timestamp = int(''.join(timestamp_str))
    return timestamp


def get_bars_in_period(symbol, start_ts, total):
    """Returns specified amount of 1 min bars starting from start_time.
    E.g      get_bars_in_period("XBTUSD", 1562971900, 100)"""

    if total >= MAX_BARS_PER_REQUEST:
        total = MAX_BARS_PER_REQUEST

    # convert epoch timestamp to ISO 8601
    start = datetime.datetime.utcfromtimestamp(start_ts).isoformat()
    timeframe = "1m"

    # request url string
    payload = (
        f"{BASE_URL}{BARS_URL}{timeframe}&"
        f"symbol={symbol}&filter=&count={total}&"
        f"startTime={start}&reverse=false")
    bars_to_parse = requests.get(payload).json()

    # store only required values (OHLCV) and convert timestamp to epoch
    new_bars = []
    for bar in bars_to_parse:
        new_bars.append({
            'symbol': symbol,
            'timestamp': int(parser.parse(bar['timestamp']).timestamp()),
            'open': bar['open'],
            'high': bar['high'],
            'low': bar['low'],
            'close': bar['close'],
            'volume': bar['volume']})

    return new_bars


def get_origin_timestamp(symbol):
    """Return millisecond timestamp of first available 1 min bar."""

    BASE_URL = "https://www.bitmex.com/api/v1"
    BARS_URL = "/trade/bucketed?binSize="

    # request string
    payload = (
        f"{BASE_URL}{BARS_URL}1m&symbol={symbol}&filter=&"
        f"count=1&startTime=&reverse=false")
    response = requests.get(payload)
    # print(requests.get(payload).headers)
    response = response.json()[0]['timestamp']
    return int(parser.parse(response).timestamp())


def data_status(exchange, symbol, MAX_BIN_SIZE_PER_REQUEST):
    """ Return a dict showing state and completeness of given symbols
    stored data. Contains pertinent timestamps, periods of missing bars and
    other info."""

    current_ts = previous_minute()
    max_bin_size = MAX_BIN_SIZE_PER_REQUEST
    result = coll.find({"symbol": symbol}).sort([("timestamp", pymongo.ASCENDING)])
    total_stored = coll.count_documents({"symbol": symbol})
    origin_ts = get_origin_timestamp(symbol)
    oldest_ts = result[total_stored - 1]['timestamp']
    newest_ts = result[0]['timestamp']
    # make timestamps sort-agnostic, in case of sorting mixups
    if oldest_ts > newest_ts:
        oldest_ts, newest_ts = newest_ts, oldest_ts

    # find gaps in stored data
    actual = {doc['timestamp'] for doc in result}  # stored ts's
    required = {i for i in range(origin_ts, newest_ts + 60, 60)}  # needed ts's
    gaps = required.difference(actual)  # find the difference

    print("Origin timestamp:  ", origin_ts)
    print("Oldest timestamp:  ", oldest_ts)
    print("Newest timestamp:  ", newest_ts)
    print("Current timestamp: ", current_ts)
    print("Total needed bars: ", len(required))
    print("Total stored bars: ", total_stored)
    print("Total missing bars:", len(gaps))
    print("Max bin size p/req:", max_bin_size)
    
    return {
        "exchange:": exchange,
        "symbol:": symbol,
        "origin_ts": origin_ts,
        "oldest_ts": oldest_ts,
        "newest_ts": newest_ts,
        "current_ts": current_ts,
        "total_stored": total_stored,
        "total_needed": len(required),
        "gaps": list(gaps),
        "max_bin_size": max_bin_size
    }


def backfill_data(report):
    """ Get and store missing bars as described in data_status() report."""

    # backfill gaps in data between origin and oldest first
    if report['origin_ts'] < report['oldest_ts']:

        # determine poll sizing and amounts accounting for max bin size
        required = int((report['oldest_ts'] - report['origin_ts']) / 60)
        final_poll_size = required % report['max_bin_size']
        total_polls_reqd = int((
            (required - final_poll_size) / report['max_bin_size']))

        bars_to_store = []
        start = report['origin_ts']
        step = report['max_bin_size'] * 60
        print(
            "Bars to fill between origin and oldest timestamps:",
            required)
        print("Start polling from:", start)
        print("Total polls to backfill origin-old:", total_polls_reqd + 1)
        
        # for i in range(total_polls_needed):
        #     bars = get_bars_in_period(symbol, start, MAX_BARS_PER_REQUEST)
        #     for bar in bars:
        #         bars_to_store.append(bar)
        #     start += step
        #     time.sleep(2)

        # # Finish with a single poll for bars_last_poll number of bars
        # final_bars = get_bars_in_period(symbol, start, bars_last_poll)
        # for bar in final_bars:
        #     bars_to_store.append(bar)

        # query = {"symbol": symbol}
        # print("number of stored bars before merge", coll.count_documents(query))
        # for bar in bars_to_store:
        #     coll.insert_one(bar)
        # print("number of stored bars after merge", coll.count_documents(query))

    # now backfill the smaller gaps between oldest and newest


report = data_status("BitMEX", "ETHUSD", MAX_BARS_PER_REQUEST)
backfill_data(report)


# check for time gaps between last stored bar and current bar
