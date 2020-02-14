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
<<<<<<< Updated upstream

=======
BASE_URL = "https://www.bitmex.com/api/v1"
BARS_URL = "/trade/bucketed?binSize="
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
    """ Return n recent bars of desired timeframe and symbol. """

    sleep(1)
    payload = (
        "https://www.bitmex.com/api/v1/trade/bucketed?binSize=" +
        timeframe + "&partial=false&symbol=" + symbol +
        "&count=" + str(n) + "&reverse=true")
=======
    """ Return n recent 1-min bars of desired timeframe and symbol. """

    sleep(0.5)
    payload = str(
        BASE_URL + BARS_URL + timeframe + "&partial=false&symbol=" +
        symbol + "&count=" + str(n) + "&reverse=true")
>>>>>>> Stashed changes

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

    # # replace final digit with zero, can be 1 or more during a slow cycle
    timestamp_str = list(str(timestamp))
    timestamp_str[len(timestamp_str) - 1] = "0"
    timestamp = int(''.join(timestamp_str))

    return timestamp


def build_OHLCV(ticks: list, symbol):
    """Return a 1 min bar as dict from a list of ticks. Assumes the given
    list's first tick is from the previous minute, uses this tick for
    bar open price."""

    if ticks:
        volume = sum(i['size'] for i in ticks) - ticks[0]['size']
        # dont include the first tick for volume calc
        # as first tick comes from the previous minute - used for
        # bar open price only
        prices = [i['price'] for i in ticks]
        high_price = max(prices) if len(prices) >= 1 else None
        low_price = min(prices) if len(prices) >= 1 else None
        open_price = ticks[0]['price'] if len(prices) >= 1 else None
        close_price = ticks[-1]['price'] if len(prices) >= 1 else None
        # format OHLCV as 1 min bar
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

        # reset bar dict ready for new bars
        bars = {i: [] for i in symbols}

        # build 1 min bars for each symbol
        for symbol in symbols:
            ticks = [
                i for i in ticks_target_minute if i['symbol'] == symbol]
            bar = build_OHLCV(ticks, symbol)
            bars[symbol].append(bar)
            # logger.debug(bar)

        return bars


<<<<<<< Updated upstream
=======
def get_recent_ticks(symbol, n):
    """ Return n minutes of recent ticks for the desired symbol. """

    diff = n * 60
    start_time = previous_minute() - diff
    end_time = previous_minute()

    sleep(0.5)
    payload = None


# ticks = get_recent_ticks("XBTUSD", 3)
# for tick in ticks:
#     print(tick)


>>>>>>> Stashed changes
# Store parsed tick-derived bars and reference bars. Once 10 mins complete,
# compare both side by side.

count = 0
parsed = []
fetched = []
sleep(seconds_til_next_minute())
while True:
    print("Waiting for full minute to elapse..")
    sleep(seconds_til_next_minute())

    logger.debug("Parsed bars: (should match reference bars):")
    bars = parse_ticks()
    for symbol in symbols:
        print(
            bars[symbol][0]['timestamp'],
            datetime.utcfromtimestamp(bars[symbol][0]['timestamp']),
            "O:", bars[symbol][0]['open'], "H:", bars[symbol][0]['high'],
            "L:", bars[symbol][0]['low'], "C:", bars[symbol][0]['close'],
            "V:", bars[symbol][0]['volume'])

        parsed.append(str(
                str(bars[symbol][0]['timestamp']) + "," +
                str(datetime.utcfromtimestamp(
                    bars[symbol][0]['timestamp'])) + "," +
                "O:" + str(bars[symbol][0]['open']) + "," +
                "H:" + str(bars[symbol][0]['high']) + "," +
                "L:" + str(bars[symbol][0]['low']) + "," +
                "C:" + str(bars[symbol][0]['close']) + "," +
                "V:" + str(bars[symbol][0]['volume'])))

    logger.debug("Reference bars (correct values):")
    ref_bars = []
    for symbol in symbols:
        ref_bars.append(get_recent_bars("1m", symbol, 1))
    for bar in ref_bars:
        isodt = parser.parse(bar[0]['timestamp'])
        epoch = int(isodt.replace(tzinfo=timezone.utc).timestamp())
        print(
            epoch, bar[0]['timestamp'],
            "O:", bar[0]['open'], "H:", bar[0]['high'], "L:", bar[0]['low'],
            "C:", bar[0]['close'], "V:", bar[0]['volume'])

        fetched.append(str(
            str(epoch) + "," +
            str(bar[0]['timestamp']) + "," +
            "O:" + str(bar[0]['open']) + "," +
            "H:" + str(bar[0]['high']) + "," +
            "L:" + str(bar[0]['low']) + "," +
            "C:" + str(bar[0]['close']) + "," +
            "V:" + str(bar[0]['volume'])))

    count += 1
    if count == 10:

        print("Parsed bars:")
        for i in parsed:
            print(i)

        print("Fetched bars:")
        for i in fetched:
            print(i)

        sys.exit(0)
