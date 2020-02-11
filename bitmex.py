from bitmex_ws import Bitmex_WS
from exchange import Exchange
from dateutil import parser
import traceback
import datetime
import requests


class Bitmex(Exchange):
    """BitMEX exchange model"""

    MAX_BARS_PER_REQUEST = 750
    BASE_URL = "https://www.bitmex.com/api/v1"
    BARS_URL = "/trade/bucketed?binSize="
    # WS_URL = "wss://testnet.bitmex.com/realtime"
    WS_URL = "wss://www.bitmex.com/realtime"
    TIMESTAMP_FORMAT = '%Y-%m-%d%H:%M:%S.%f'

    def __init__(self, logger):
        super()
        self.logger = logger
        self.name = "BitMEX"
        self.symbols = ["XBTUSD", "ETHUSD"]
        self.channels = ["trade"]  # , "orderBookL2"
        self.origin_tss = {"XBTUSD": 1483228800, "ETHUSD": 1533200520}
        self.api_key = None
        self.api_secret = None

        # only ever stores the most recent minutes bars, not persistent
        self.bars = {}

        # connect to websocket
        self.ws = Bitmex_WS(
            self.logger, self.symbols, self.channels, self.WS_URL,
            self.api_key, self.api_secret)
        if not self.ws.ws.sock.connected:
            self.logger.debug("Failed to to connect to BitMEX websocket.")

    def parse_ticks(self):
        if not self.ws.ws:
            self.logger.debug("BitMEX websocket disconnected.")
        else:
            all_ticks = self.ws.get_ticks()
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
                    self.logger.debug(traceback.format_exc())
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
            self.bars = {i: [] for i in self.symbols}

            # build 1 min bars for each symbol
            for symbol in self.symbols:
                ticks = [
                    i for i in ticks_target_minute if i['symbol'] == symbol]
                bar = self.build_OHLCV(ticks, symbol)
                self.bars[symbol].append(bar)
                # self.logger.debug(bar)

    def get_bars_in_period(self, symbol, start_time, total):
        """Returns specified amount of 1 min bars starting from start_time.
        E.g      get_bars_in_period("XBTUSD", 1562971900, 100)"""

        if total >= self.MAX_BARS_PER_REQUEST:
            total = self.MAX_BARS_PER_REQUEST

        # convert epoch timestamp to ISO 8601
        start = datetime.datetime.utcfromtimestamp(start_time).isoformat()
        timeframe = "1m"

        # request url string
        payload = (
            f"{self.BASE_URL}{self.BARS_URL}{timeframe}&"
            f"symbol={symbol}&filter=&count={total}&"
            f"startTime={start}&reverse=false")
        self.logger.debug("API request string: " + payload)
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

    def get_origin_timestamp(self, symbol: str):
        """Return millisecond timestamp of first available 1 min bar. If the
        timestamp is stored, return that, otherwise poll the exchange."""

        if self.origin_tss[symbol] is not None:
            return self.origin_tss[symbol]
        else:
            payload = (
                f"{self.BASE_URL}{self.BARS_URL}1m&symbol={symbol}&filter=&"
                f"count=1&startTime=&reverse=false")

            response = requests.get(payload).json()[0]['timestamp']

            return int(parser.parse(response).timestamp())
