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


def get_recent_bar(timeframe, symbol, n=1):
    """ Return n recent 1-min bars of desired timeframe and symbol. """

    sleep(0.5)
    payload = str(
        BASE_URL + BARS_URL + timeframe + "&partial=false&symbol=" +
        symbol + "&count=" + str(n) + "&reverse=true")

    # print(payload)nnnnnn

    result = requests.get(payload).json()

    bars = []
    for i in result:
        bars.append({
                'symbol': symbol,
                'timestamp': i['timestamp'],
                'open': i['open'],
                'high': i['high'],
                'low': i['low'],
                'close': i['close'],
                'volume': i['volume']})
    return bars


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
        ticks: A list of ticks to aggregate. Assumes the list's first tick
               is from the previous minute, this tick is used for open price.
        symbol: Ticker code.
        close_as_open: If true, the first tick in arg "ticks" must be the final
            tick from the previous minute, to be used for bar open price,
            resulting in no gaps between bars (some exchanges follow this
            practice as standard, some dont). If false, use arg "ticks" first
            tick as the open price.

        Note: Some venues use a 1 min offset for bar timestamps. Tradingview
        bars are timestamped 1 minute behind bitmex, for example.

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
               'timestamp': previous_minute() + 60,
               'open': open_price,
               'high': high_price,
               'low': low_price,
               'close': close_price,
               'volume': volume}
        return bar

    elif ticks is None or not ticks:
        bar = {'symbol': symbol,
               'timestamp': previous_minute() + 60,
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

            # group ticks by symbol
            ticks = {i: [] for i in symbols}
            for tick in ticks_target_minute:
                ticks[tick['symbol']].append(tick)

            # build bars from ticks
            bars = {i: [] for i in symbols}
            for symbol in symbols:
                bar = build_OHLCV(ticks[symbol], symbol)
                bars[symbol].append(bar)

            return bars, ticks


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
    # print(payload)

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


count = 0
sleep(seconds_til_next_minute())
while True:
    if count == 0 or count % 3:
        print("Waiting for full minute to elapse..")
        sleep(seconds_til_next_minute())

        bars, pticks = parse_ticks()

        # print("Parsed ticks:")
        # for tick in pticks["XBTUSD"]:
        #     print(
        #         tick['timestamp'], tick['side'],
        #         tick['size'], tick['price'])

        print("Parsed bars:")
        print(bars["XBTUSD"])
        # print(bars["ETHUSD"])

        # stats
        # print(
        #     "Open:", pticks["XBTUSD"][0]['price'])
            # "High:",
            # "Low:",
            # "Close:",
            # "Volume:", )

        # print("\nReference ticks:")
        ticks = get_recent_ticks("XBTUSD")
        # for tick in ticks:
        #     print(
        #         tick['timestamp'], tick['side'], tick['size'],
        #         tick['price'])

        print("Reference bars:")
        print(get_recent_bar("1m", "XBTUSD"))
        # print(get_recent_bars("1m", "ETHUSD", 1))

        # stats

    count += 1
    if count == 1:
        sys.exit(0)
