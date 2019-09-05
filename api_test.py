import requests
from dateutil import parser
import datetime
from pymongo import MongoClient
import pymongo
from itertools import groupby, count
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


def data_status_report(exchange, symbol, MAX_BIN_SIZE_PER_REQUEST, output=False):
    """ Return dict showing state and completeness of given symbols
    stored data. Contains pertinent timestamps, periods of missing bars and
    other relevant info."""

    current_ts = previous_minute()
    max_bin_size = MAX_BIN_SIZE_PER_REQUEST
    result = coll.find(
        {"symbol": symbol}).sort([("timestamp", pymongo.ASCENDING)])
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

    if output:
        print("Origin (on-exchange) timestamp:.", origin_ts)
        print("Oldest locally stored timestamp:", oldest_ts)
        print("Newest locally stored timestamp:", newest_ts)
        print("Current timestamp:..............", current_ts)
        print("Max bin size per REST poll:.....", max_bin_size)
        print("Total required bars:............", len(required))
        print("Total locally stored bars:......", total_stored)
        print("Total missing bars:.............", len(gaps))

    return {
        "exchange:": exchange,
        "symbol": symbol,
        "origin_ts": origin_ts,
        "oldest_ts": oldest_ts,
        "newest_ts": newest_ts,
        "current_ts": current_ts,
        "max_bin_size": max_bin_size
        "total_stored": total_stored,
        "total_needed": len(required),
        "gaps": list(gaps),
    }


def backfill_data_bulk(report):
    """ Get and store missing bars between origin and oldest timestamps.
    Use this only once to get bulk historic data, then fill small gaps with
    backfill_data_gaps() intermittently each day."""

    # backfill origin and oldest timestamp data gap first
    if report['origin_ts'] < report['oldest_ts']:

        # Determine poll sizing and amounts accounting for max_bin_size.
        # Split polling into several large batch polls and a final small poll.
        required = int((report['oldest_ts'] - report['origin_ts']) / 60)
        final_poll_size = required % report['max_bin_size']
        total_polls_batch = int((
            (required - final_poll_size) / report['max_bin_size']))

        # poll exchange REST endpoint for first bulk batch missing bars
        start = report['origin_ts']
        step = report['max_bin_size'] * 60
        bars_to_store = []
        delay = 1  # wait time before attmepting to re-poll after error
        stagger = 2  # error delay co-efficient
        timeout = 10
        for i in range(total_polls_batch):
            try:
                bars = get_bars_in_period(
                    report['symbol'], start, report['max_bin_size'])
                for bar in bars:
                    bars_to_store.append(bar)
                stagger = 2  # reset stagger to base after successful poll
                start += step  # increment the starting poll timestamp
                time.sleep(stagger)
            except Exception as e:
                # retry poll with an exponential delay after each error
                for i in range(timeout):
                    try:
                        time.sleep(delay)
                        bars = get_bars_in_period(
                            report['symbol'], start, report['max_bin_size'])
                        for bar in bars:
                            bars_to_store.append(bar)
                        stagger = 2
                        start += step
                        break
                    except Exception as e:
                        delay *= stagger
                        if i == timeout - 1:
                            raise Exception("Polling timeout.")

        # finish with a single poll for final_poll_size number of bars
        for i in range(timeout):
            try:
                time.sleep(delay)
                final_bars = get_bars_in_period(
                    report['symbol'], start, final_poll_size)
                for bar in final_bars:
                    bars_to_store.append(bar)
                stagger = 2
                break
            except Exception as e:
                # retry poll with an exponential delay after each error
                delay *= stagger
                if i == timeout - 1:
                    raise Exception("Polling timeout.")

        # store bars
        query = {"symbol": report['symbol']}
        print("Stored bars before merge", coll.count_documents(query))
        for bar in bars_to_store:
            try:
                coll.insert_one(bar, upsert=True)
            except pymongo.errors.DuplicateKeyError:
                continue  # skip duplicates if they exist
        print("Stored bars after merge", coll.count_documents(query))
        return True
    return False


def backfill_data_gaps(report):
    """ Get and store small groups of missing bars. Intended to be called
    multiple times daily as a QA measure for patching small amounts of
    bars missing from locally saved data."""

    if len(report['gaps']) != 0:
        # sort timestamps into sequential bins (to reduce polling)
        bins = [
            list(g) for k, g in groupby(
                sorted(report['gaps']), key=lambda n, c=count(0, 60): n - next(c))]

        # poll exchange REST endpoint for missing bars
        bars_to_store = []
        for i in bins:
            try:
                bars = get_bars_in_period(report['symbol'], i[0], len(i))
                for bar in bars:
                    bars_to_store.append(bar)
                stagger = 2  # reset stagger to base after successful poll
                time.sleep(stagger)
            except Exception as e:
                # retry poll with an exponential delay after each error
                for i in range(timeout):
                    try:
                        time.sleep(delay)
                        bars = get_bars_in_period(report['symbol'], i[0], len(i))
                        for bar in bars:
                            bars_to_store.append(bar)
                        stagger = 2
                        break
                    except Exception as e:
                        delay *= stagger
                        if i == timeout - 1:
                            raise Exception("Polling timeout.")

        # sanity check, check that the retreived bars match gaps
        timestamps = [i['timestamp'] for i in bars_to_store]
        timestamps = sorted(timestamps)
        bars = sorted(report['gaps'])
        if timestamps == bars:
            query = {"symbol": report['symbol']}
            print("Stored bars before merge", coll.count_documents(query))
            for bar in bars_to_store:
                try:
                    coll.insert_one(bar)
                except pymongo.errors.DuplicateKeyError:
                    continue  # skip duplicates if they exist
            print("Stored bars after merge", coll.count_documents(query))
            return True
        else:
            raise Exception("Fetched bars do not match missing timestamps.")
    else:
        print("No gaps in data exist.")
        return False


report = data_status_report(
    "BitMEX", "XBTUSD", MAX_BARS_PER_REQUEST, output=True)

backfill_data_gaps(report)


# check for time gaps between last stored bar and current bar
