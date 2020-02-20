from datetime import timezone, datetime, timedelta
from bitmex_ws import Bitmex_WS
from dateutil.tz import gettz
from dateutil import parser
from time import sleep
import traceback
import requests
import logging
import sys


# For debugging/testimg ing parse_ticks() using bitmex_WS.

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s:%(levelname)s:%(module)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)
logging.getLogger("urllib3").propagate = False
requests_log = logging.getLogger("requests")
requests_log.addHandler(logging.NullHandler())
requests_log.propagate = False

BASE_URL = "https://www.bitmex.com/api/v1"
BARS_URL = "/trade/bucketed?binSize="
TICKS_URL = "/trade?symbol="

WS_URL = "wss://www.bitmex.com/realtime"
symbols = ["XBTUSD", "ETHUSD"]
channels = ["trade"]
api_key = None
api_secret = None

ws = Bitmex_WS(
            logger, symbols, channels, WS_URL,
            api_key, api_secret)

if not ws.ws.sock.connected:
    logger.debug("Failed to to connect to BitMEX websocket.")


def get_recent_bars(timeframe, symbol, n):
    """ Return n recent 1-min bars of desired timeframe and symbol. """

    sleep(0.5)
    payload = str(
        BASE_URL + BARS_URL + timeframe + "&partial=false&symbol=" +
        symbol + "&count=" + str(n) + "&reverse=true")

    return requests.get(payload).json()


def seconds_til_next_minute():
    """ Return number of seconds to next minute."""

    now = datetime.utcnow().second
    delay = 60 - now
    return delay


def previous_minute():
    """ Return the previous minute UTC ms epoch timestamp."""

    d1 = datetime.now().second
    d2 = datetime.now().microsecond
    timestamp = datetime.now() - timedelta(
        minutes=1, seconds=d1, microseconds=d2)

    # convert to epoch
    timestamp = int(timestamp.timestamp())

    # Replace final digit with zero, can be 1 or more during a slow cycle.
    timestamp_str = list(str(timestamp))
    timestamp_str[len(timestamp_str) - 1] = "0"
    timestamp = int(''.join(timestamp_str))

    return timestamp


def build_OHLCV(ticks: list, symbol: str, close_as_open=True):
    """
    Args:
        ticks: List of ticks to be converted to 1-min bar.
        symbol: Ticker code.
        close_as_open: If true, the first tick in arg "ticks" must be the final
            tick from the previous minute, to be used for bar open price,
            resulting in no gaps between bars (some exchanges follow this
            practice as standard, some dont). If false, use arg "ticks" first
            tick as the open price.

    Returns:
        1-minute OHLCV bar (dict).

    Raises:
        Tick data timestamp mismatch error.
    """

    if ticks:

        if close_as_open:

            # Convert incoming timestamp format if required.
            if type(ticks[0]['timestamp']) is not datetime:
                median = parser.parse(
                    ticks[int((len(ticks) / 2))]['timestamp'])
                first = parser.parse(ticks[0]['timestamp'])
            else:
                median = ticks[int((len(ticks) / 2))]['timestamp']
                first = ticks[0]['timestamp']

            # This should be the most common case if close_as_open=True.
            # Dont include the first tick for volume and price calc.
            if first.minute == median.minute - 1:
                volume = sum(i['size'] for i in ticks) - ticks[0]['size']
                prices = [i['price'] for i in ticks]
                prices.pop(0)

            # If the timestamps are same, may mean there were no early
            # trades, proceed as though close_as_open=False
            elif first.minute == median.minute:
                volume = sum(i['size'] for i in ticks)
                prices = [i['price'] for i in ticks]

            # There's a timing/data problem is neither case above is true.
            else:
                raise Exception(
                    "Tick data timestamp error: timestamp mismatch." +
                    "\nFirst tick minute: " + str(first) +
                    "\nMedian tick minute: " + str(median))

        elif not close_as_open or close_as_open is False:
            volume = sum(i['size'] for i in ticks)
            prices = [i['price'] for i in ticks]

        high_price = max(prices) if len(prices) >= 1 else None
        low_price = min(prices) if len(prices) >= 1 else None
        open_price = ticks[0]['price'] if len(prices) >= 1 else None
        close_price = ticks[-1]['price'] if len(prices) >= 1 else None

        bar = {'symbol': symbol,
               'timestamp': previous_minute(),
               'open': open_price,
               'high': high_price,
               'low': low_price,
               'close': close_price,
               'volume': volume}
        return bar

    elif ticks is None or not ticks:
        bar = {'symbol': symbol,
               'timestamp': previous_minute(),
               'open': None,
               'high': None,
               'low': None,
               'close': None,
               'volume': 0}
        return bar


def parse_ticks():
    if not ws.ws:
        logger.debug("BitMEX websocket disconnected.")
    else:
        all_ticks = ws.get_ticks()
        target_minute = datetime.now().minute - 1
        ticks_target_minute = []
        tcount = 0

        # search from end of tick list to grab newest ticks first
        for i in reversed(all_ticks):
            try:
                ts = i['timestamp']
                if type(ts) is not datetime:
                    ts = parser.parse(ts)
            except Exception:
                logger.debug(traceback.format_exc())
            # scrape prev minutes ticks
            if ts.minute == target_minute:
                ticks_target_minute.append(i)
                ticks_target_minute[tcount]['timestamp'] = ts
                tcount += 1
            # store the previous-to-target bar's last
            # traded price to use as the open price for target bar
            if ts.minute == target_minute - 1:
                ticks_target_minute.append(i)
                ticks_target_minute[tcount]['timestamp'] = ts
                break

        ticks_target_minute.reverse()

        # debug only
        print("Ticks to parse:")
        for tick in ticks_target_minute:
            if tick['symbol'] == "ETHUSD":
                print(
                    tick['timestamp'], tick['side'],
                    tick['size'], tick['price'])

        # group ticks by symbol
        ticks = {i: [] for i in symbols}
        for tick in ticks_target_minute:
            ticks[tick['symbol']].append(tick)

        # build bars from ticks
        bars = {i: [] for i in symbols}
        for symbol in symbols:
            bar = build_OHLCV(ticks[symbol], symbol)
            bars[symbol].append(bar)
            print(bar)

            # debug only
            # if symbol == "XBTUSD":
            #     print("Final ticks before build_OHLCV() called:")
            #     for tick in ticks[symbol]:
            #         print(
            #             tick['timestamp'], tick['side'],
            #             tick['size'], tick['price'])

        return bars


def get_recent_ticks(symbol, n=1):
    """
    Args:
        symbol:
        n:

    Returns:
        List containing n minutes of recent ticks for the desired symbol.

    Raises:
        Tick data timestamp mismatch error.
    """

    # find difference between start and end of period
    delta = n * 60

    # find start timestamp and convert to ISO1806
    start_epoch = previous_minute() + 60 - delta
    start_iso = datetime.utcfromtimestamp(start_epoch).isoformat()

    # find end timestamp and convert to ISO1806
    end_epoch = previous_minute() + 60
    end_iso = datetime.utcfromtimestamp(end_epoch).isoformat()

    # initial poll
    sleep(1)
    payload = str(
        BASE_URL + TICKS_URL + symbol + "&count=" +
        "1000&reverse=false&startTime=" + start_iso + "&endTime" + end_iso)
    print(payload)

    # print("Starting timestamp", start_iso)
    # print("End timestamp     ", end_iso)
    ticks = []
    initial_result = requests.get(payload).json()
    for tick in initial_result:
        ticks.append(tick)

    # if 1000 ticks in result (max size), keep polling until
    # we get a response with length <1000
    if len(initial_result) == 1000:
        print("Over 1000 ticks exist in the previous minute.")

        maxed_out = True
        while maxed_out:

            # Dont use endTime as it seems to cut off the final few ticks.
            payload = str(
                BASE_URL + TICKS_URL + symbol + "&count=" +
                "1000&reverse=false&startTime=" + ticks[-1]['timestamp'])

            interim_result = requests.get(payload).json()
            for tick in interim_result:
                ticks.append(tick)

            if len(interim_result) != 1000:
                maxed_out = False

    # check median tick timestamp matches start_iso
    median_dt = parser.parse(ticks[int((len(ticks) / 2))]['timestamp'])
    match_dt = parser.parse(start_iso)
    if median_dt.minute != match_dt.minute:
        raise Exception("Tick data timestamp error: timestamp mismatch.")

    # populate list with matching-timestamped ticks only
    final_ticks = [
        i for i in ticks if parser.parse(
            i['timestamp']).minute == match_dt.minute]

    return final_ticks

# print("Number of ticks in n minutes:", len(ticks))


# Store parsed tick-derived bars and reference bars. Once 3 mins complete,
# compare both side by side.

# count = 0
# parsed = []
# fetched = []
# sleep(seconds_til_next_minute())
# while True:
#     print("Waiting for full minute to elapse..")
#     sleep(seconds_til_next_minute())

#     logger.debug("Parsed bars: (should match reference bars):")
#     bars = parse_ticks()
#     for symbol in symbols:
#         print(
#             bars[symbol][0]['timestamp'],
#             datetime.utcfromtimestamp(bars[symbol][0]['timestamp']),
#             "O:", bars[symbol][0]['open'], "H:", bars[symbol][0]['high'],
#             "L:", bars[symbol][0]['low'], "C:", bars[symbol][0]['close'],
#             "V:", bars[symbol][0]['volume'])

#         parsed.append(str(
#                 str(bars[symbol][0]['timestamp']) + "," +
#                 str(datetime.utcfromtimestamp(
#                     bars[symbol][0]['timestamp'])) + "," +
#                 "O:" + str(bars[symbol][0]['open']) + "," +
#                 "H:" + str(bars[symbol][0]['high']) + "," +
#                 "L:" + str(bars[symbol][0]['low']) + "," +
#                 "C:" + str(bars[symbol][0]['close']) + "," +
#                 "V:" + str(bars[symbol][0]['volume'])))

#     logger.debug("Reference bars (correct values):")
#     ref_bars = []
#     for symbol in symbols:
#         ref_bars.append(get_recent_bars("1m", symbol, 1))
#     for bar in ref_bars:
#         isodt = parser.parse(bar[0]['timestamp'])
#         epoch = int(isodt.replace(tzinfo=timezone.utc).timestamp())
#         print(
#             epoch, bar[0]['timestamp'],
#             "O:", bar[0]['open'], "H:", bar[0]['high'], "L:", bar[0]['low'],
#             "C:", bar[0]['close'], "V:", bar[0]['volume'])

#         fetched.append(str(
#             str(epoch) + "," +
#             str(bar[0]['timestamp']) + "," +
#             "O:" + str(bar[0]['open']) + "," +
#             "H:" + str(bar[0]['high']) + "," +
#             "L:" + str(bar[0]['low']) + "," +
#             "C:" + str(bar[0]['close']) + "," +
#             "V:" + str(bar[0]['volume'])))

#     count += 1
#     if count == 3:

#         print("Parsed bars:")
#         for i in parsed:
#             print(i)

#         print("Fetched bars:")
#         for i in fetched:
#             print(i)

#         sys.exit(0)

count = 0
sleep(seconds_til_next_minute())
while True:
    if count == 0 or count % 3:
        print("Waiting for full minute to elapse..")
        sleep(seconds_til_next_minute())

        bars = parse_ticks()

        ticks = get_recent_ticks("ETHUSD", 1)

        print("\nReference ticks:")
        for tick in ticks:
            print(tick['timestamp'], tick['side'], tick['size'], tick['price'])

    count += 1
    if count == 1:
        sys.exit(0)
