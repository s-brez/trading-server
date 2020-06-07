"""
trading-server is a multi-asset, multi-strategy, event-driven execution
and backtesting platform (OEMS) for trading common markets.

Copyright (C) 2020  Sam Breznikar <sam@sdbgroup.io>

Licensed under GNU General Public License 3.0 or later.

Some rights reserved. See LICENSE.md, AUTHORS.md.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import os


class Exchange(ABC):
    """
    Exchange abstract class, concrete brokers/exchange classes to inherit this.
    """

    def __init__(self):
        pass

    def get_new_bars(self):
        """
        Args:
            None.

        Returns:
            self.bars[symbol] tree (dict).

        Raises:
            None.
        """

        return self.bars

    def get_max_bin_size(self):
        """
        Args:
            None.

        Returns:
            Max amount of items returned per REST poll for http api (int).

        Raises:
            None.
        """

        return self.MAX_BARS_PER_REQUEST

    def get_symbols(self):
        """
        Args:
            None.

        Returns:
            List of all symbols ticker code strings.

        Raises:
            None.
        """

        return self.symbols

    def get_name(self):
        """
        Args:
            None.

        Returns:
            Venue name string.

        Raises:
            None.
        """

        return self.name

    def previous_minute(self):
        """
        Args:
            None.

        Returns:
            Previous minute epoch timestamp (int).

        Raises:
            None.
        """

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

    def seconds_til_next_minute(self):
        """
        Args:
            None.

        Returns:
            Number of second to next minute (int).

        Raises:
            None.
        """

        now = datetime.datetime.utcnow().second
        delay = 60 - now - 1
        return delay

    def build_OHLCV(
            self, ticks: list, symbol: str, close_as_open=True, offset=60):

        """
        Args:
            ticks: A list of ticks to aggregate. Assumes the list's first tick
                is from the previous minute, this tick is used for open price.
            symbol: instrument ticker code (string)
            close_as_open: If true, first tick in arg "ticks" must be the final
                tick from the previous minute, to be used for bar open price,
                resulting in no gaps between bars (some exchanges follow this
                practice as standard, some dont). If false, use arg "ticks" 1st
                tick as the open price.
            offset: number of second to advance timestamps by. Some venues
                timestamp their bars differently. Tradingview bars are
                timestamped 1 minute behind bitmex, for example.

        Returns:
            A 1 min OHLCV bar (dict).

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
                   'timestamp': self.previous_minute() + offset,
                   'open': open_price,
                   'high': high_price,
                   'low': low_price,
                   'close': close_price,
                   'volume': volume}
            return bar

        elif ticks is None or not ticks:
            bar = {'symbol': symbol,
                   'timestamp': self.previous_minute() + offset,
                   'open': None,
                   'high': None,
                   'low': None,
                   'close': None,
                   'volume': 0}
            return bar

    def finished_parsing_ticks(self):
        return self.finished_parsing_ticks

    def load_api_keys(self):
        """
        Loads key and secret from environment variables.

        Keys must be stored as follows (all capitalised):
        API key:    VENUE_NAME_API_KEY
        API secret: VENUE_NAME_SECRET_KEY

        Args:
            None.

        Returns:
            key: api key matching exchange name.
            secret: api secret key matching venue name.

        Raises:
            None.
        """

        venue_name = self.get_name().upper()
        key = os.environ[venue_name + '_API_KEY']
        secret = os.environ[venue_name + '_API_SECRET']

        return key, secret

    def round_increment(self, number, symbol):
        """
        Round a given number to its nearest minimum increment
        """

        inc = self.symbol_min_increment[symbol]

        if number < 1:
            quote = number
        else:
            quote = (number // inc) * inc

        # print("Rounded quote:", quote)
        return quote


    @abstractmethod
    def place_bulk_orders(self, orders: list):
        """
        Given a list of order events objects, place corresponding orders with
        the respective trading venue.

        Args:
            orders: list of order objects

        Returns:

        Raises:

        """

    @abstractmethod
    def place_single_order(self, order):
        """
        Place a single order with the respective trading venue.

        Args:
            order: order object

        Returns:

        Raises:

        """

    @abstractmethod
    def cancel_orders(self, order_ids: list):
        """
        Cancel all orders matching list of given order IDs.

        Args:
            orders: list of orders.

        Returns:
            cancel_status: dict, {order_id: cancel succcess/fail message}

        Raises:

        """

    @abstractmethod
    def close_position(self, symbol, qty, direction):
        """
        Close 'qty' units of 'symbol' instrument in 'direction' direction.

        Args:
            symbol: instrument symbol to close.
            qty: number of units of instrument to close.
            direction: LONG or SHORT

        Returns:
            True if successful close, False if not.
        Raises:

        """

    @abstractmethod
    def format_orders(self, orders: list):
        """
        Converts internally formatted orders into relevant venue order format.

        Args:
            orders: list of order objects

        Returns:
            formatted_orders: new list of venue-appropirate formatted orders

        Raises:

        """

    @abstractmethod
    def get_executions(self, symbol, start_timestamp, count):
        """
        Args:
            symbol: instrument ticker code (string)
            start_timestamp: epoch timestamp (int)
            count: amount of results to fetch (int)

        Returns:
            List of balance-affecting executions for the given symbol.
            Each execution should be a dict with the following format:
                {
                    'order_id': ???,
                    'venue_id': ???,
                    'timestamp': ???,       epooch timestamp (int)
                    'avg_exc_price': ???,
                    'currency': ???,
                    'symbol': ???,
                    'direction': ???,       LONG or SHORT
                    'size': ???,
                    'order_type': ???,
                    'fee_type': ???,
                    'fee_amt': ???,         multiplicand to find total fee cost
                    'total_fee': ???,       fees charged for transaction in USD
                    'status' ???:           FILLED, CANCELLED, NEW, PARTIAL
                }

        Raises:
            None.
        """

    @abstractmethod
    def get_bars_in_period(self, symbol: str, start_time: int, total: int):
        """
        Args:
            symbol: instrument ticker code (string)
            start_time: epoch timestamp (int)
            total: amount of bars to fetch (int)

        Returns:
            List of historic 1min OHLCV bars for specified period. Returns
            specified amount of 1 min bars starting from start_time.

        Raises:
            None.
        """

    @abstractmethod
    def get_recent_bars(self, timeframe: str, symbol: str, n: int):
        """
        Args:
            timeframe: timeframe code (string)
            symbol: instrument ticker code (string)
            n: amount of bars

        Returns:
            List of n recent 1-min bars of specified timeframe and symbol.

        Raises:
            None.
        """

    @abstractmethod
    def get_origin_timestamp(self, symbol: str):
        """
        Args:
            symbol: instrument ticker code (string)

        Returns:
            Epoch timestamp (int) of first available (oldest) 1 min bar.

        Raises:
        """

    @abstractmethod
    def get_recent_ticks(symbol: str, n: int):
        """
        Args:
            symbol:
            n: number of minutes worth of ticks (int)

        Returns:
            Instrument ticker code (string).

        Raises:
            Tick data timestamp mismatch error.

        """

    @abstractmethod
    def parse_ticks(self):
        """
        Args:
            None.

        Returns:
            Converts streamed websocket tick data into a 1-min OHLCV bars, then
            appends new bars to the exchange object self.bars[symbol] tree.

        Raises:
            None.
        """

    @abstractmethod
    def get_positions(self):
        """
        Args:
            None.

        Returns:
            List containing open positions.

        Raises:
            None.
        """

    @abstractmethod
    def get_orders(self):
        """
        Args:
            None.

        Returns:
            List containing all orders, both active and inactive.

        Raises:
            None.
        """
