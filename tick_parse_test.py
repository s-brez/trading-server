from bitmex_ws import Bitmex_WS
from dateutil import parser
from time import sleep
import traceback
import datetime
import requests
import datetime
import logging

# For debugging/testimg ing parse_ticks() using bitmex_WS.


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

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
    """ Return n recent bars of desired timeframe and symbol. """
    payload = (
        "https://www.bitmex.com/api/v1/trade/bucketed?binSize=" +
        timeframe + "&partial=false&symbol=" + symbol +
        "&count=" + n + "&reverse=true")

    return requests.get(payload).json()


def seconds_til_next_minute():
    """ Return number of seconds to next minute."""

    now = datetime.datetime.utcnow().second
    delay = 60 - now
    return delay


def previous_minute():
    """ Return the previous minute UTC ms epoch timestamp."""

    delay = datetime.datetime.utcnow().second
    timestamp = datetime.datetime.utcnow() - datetime.timedelta(
        seconds=delay)
    timestamp.replace(second=0, microsecond=0)
    # convert to epoch
    timestamp = int(timestamp.timestamp())
    # replace final digit with zero, can be 1 or more during a slow cycle
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
        target_minute = datetime.datetime.utcnow().minute - 1
        ticks_target_minute = []
        tcount = 0

        # search from end of tick list to grab newest ticks first
        for i in reversed(all_ticks):
            try:
                ts = i['timestamp']
                if type(ts) is not datetime.datetime:
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


print("Started..")
sleeptime = seconds_til_next_minute()
sleep(sleeptime)

while True:
    print("Waiting for full minute to elapse..")
    sleeptime = seconds_til_next_minute()
    sleep(sleeptime)

    print("Parsing ticks..")
    bars = parse_ticks()

    for bar in bars:
        for symbol in symbols:
            print(bar[symbol])
