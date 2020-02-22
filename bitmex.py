"""
trading-server is a multi-asset, multi-strategy, event-driven execution
and backtesting platform (OEMS) for trading common markets.

Copyright (C) 2020  Sam Breznikar <sam@sdbgroup.io>

Licensed under GNU General Public License 3.0 or later.

Some rights reserved. See LICENSE.md, AUTHORS.md.
"""

from datetime import timezone, datetime, timedelta
from bitmex_ws import Bitmex_WS
from exchange import Exchange
from dateutil import parser
import traceback
import requests


class Bitmex(Exchange):
    """
    BitMEX exchange model.
    """

    MAX_BARS_PER_REQUEST = 750
    BASE_URL = "https://www.bitmex.com/api/v1"
    BARS_URL = "/trade/bucketed?binSize="
    TICKS_URL = "/trade?symbol="
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

        # Non persistent datastores.
        self.bars = {}
        self.ticks = {}

        # Connect to trade websocket
        self.ws = Bitmex_WS(
            self.logger, self.symbols, self.channels, self.WS_URL,
            self.api_key, self.api_secret)
        if not self.ws.ws.sock.connected:
            self.logger.debug("Failed to to connect to BitMEX websocket.")

        # Note, for future channel subs, create assitional Bitmex_WS.

    def parse_ticks(self):

        if not self.ws.ws:
            self.logger.debug("BitMEX websocket disconnected.")
        else:
            all_ticks = self.ws.get_ticks()
            target_minute = datetime.now().minute - 1
            ticks_target_minute = []
            tcount = 0

            # Search from end of tick list to grab newest ticks first.
            for i in reversed(all_ticks):
                try:
                    ts = i['timestamp']
                    if type(ts) is not datetime:
                        ts = parser.parse(ts)
                except Exception:
                    self.logger.debug(traceback.format_exc())

                # Scrape prev minutes ticks.
                if ts.minute == target_minute:
                    ticks_target_minute.append(i)
                    ticks_target_minute[tcount]['timestamp'] = ts
                    tcount += 1

                # Store the previous-to-target bar's last
                # traded price to use as the open price for target bar.
                if ts.minute == target_minute - 1:
                    ticks_target_minute.append(i)
                    ticks_target_minute[tcount]['timestamp'] = ts
                    break

            ticks_target_minute.reverse()

            # Group ticks by symbol.
            self.ticks = {i: [] for i in self.symbols}
            for tick in ticks_target_minute:
                self.ticks[tick['symbol']].append(tick)

            #  Build bars from ticks.
            self.bars = {i: [] for i in self.symbols}
            for symbol in self.symbols:
                bar = self.build_OHLCV(self.ticks[symbol], symbol)
                self.bars[symbol].append(bar)

    def get_bars_in_period(self, symbol, start_time, total):

        if total >= self.MAX_BARS_PER_REQUEST:
            total = self.MAX_BARS_PER_REQUEST

        # Convert epoch timestamp to ISO 8601.
        start = datetime.utcfromtimestamp(start_time).isoformat()
        timeframe = "1m"

        payload = (
            f"{self.BASE_URL}{self.BARS_URL}{timeframe}&"
            f"symbol={symbol}&filter=&count={total}&"
            f"startTime={start}&reverse=false")

        # Uncomment below line to manually verify results.
        # self.logger.debug("API request string: " + payload)

        bars_to_parse = requests.get(payload).json()

        # Store only required values (OHLCV) and convert timestamp to epoch.
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

        if self.origin_tss[symbol] is not None:
            return self.origin_tss[symbol]
        else:
            payload = (
                f"{self.BASE_URL}{self.BARS_URL}1m&symbol={symbol}&filter=&"
                f"count=1&startTime=&reverse=false")

            response = requests.get(payload).json()[0]['timestamp']
            timestamp = int(parser.parse(response).timestamp())

            self.logger.debug(
                "BitMEX" + symbol + " origin timestamp: " + str(timestamp))

            return timestamp

    def get_recent_bars(timeframe, symbol, n=1):

        payload = str(
            self.BASE_URL + self.BARS_URL + timeframe +
            "&partial=false&symbol=" + symbol + "&count=" +
            str(n) + "&reverse=true")

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

    def get_recent_ticks(symbol, n=1):

        # Find difference between start and end of period.
        delta = n * 60

        # Find start timestamp and convert to ISO1806.
        start_epoch = self.previous_minute() + 60 - delta
        start_iso = datetime.utcfromtimestamp(start_epoch).isoformat()

        # find end timestamp and convert to ISO1806
        end_epoch = previous_minute() + 60
        end_iso = datetime.utcfromtimestamp(end_epoch).isoformat()

        # Initial poll.
        sleep(1)
        payload = str(
            self.BASE_URL + self.TICKS_URL + symbol + "&count=" +
            "1000&reverse=false&startTime=" + start_iso + "&endTime" + end_iso)

        ticks = []
        initial_result = requests.get(payload).json()
        for tick in initial_result:
            ticks.append(tick)

        # If 1000 ticks in result (max size), keep polling until
        # we get a response with length <1000.
        if len(initial_result) == 1000:

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

        # Check median tick timestamp matches start_iso.
        median_dt = parser.parse(ticks[int((len(ticks) / 2))]['timestamp'])
        match_dt = parser.parse(start_iso)
        if median_dt.minute != match_dt.minute:
            raise Exception("Tick data timestamp error: timestamp mismatch.")

        # Populate list with matching-timestamped ticks only.
        final_ticks = [
            i for i in ticks if parser.parse(
                i['timestamp']).minute == match_dt.minute]

        return final_ticks
