from abc import ABC, abstractmethod
from datetime import datetime, timedelta


class Exchange(ABC):
    """Exchange abstract class for modelling individual brokers/exchanges."""

    def __init__(self):
        super.__init__()

    def get_new_bars(self):
        """
        Args:

        Returns:
            Exchange objects self.bars[symbol] tree (dict).

        Raises:
        """
        return self.bars

    def get_max_bin_size(self):
        """
        Args:

        Returns:
            Max amount of items returned per REST poll for http api (int).

        Raises:
        """
        return self.MAX_BARS_PER_REQUEST

    def get_symbols(self):
        """
        Args:

        Returns:
            List of all symbols ticker code strings.

        Raises:
        """
        return self.symbols

    def get_name(self):
        """
        Args:

        Returns:
            Venue name string.

        Raises:
        """
        return self.name

    def previous_minute(self):
        """
        Args:

        Returns:
            The previous minute epoch timestamp (int).

        Raises:
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

    def seconds_til_next_minute(self: int):
        """
        Args:

        Returns:
            Number of second to next minute (int).

        Raises:
        """

        now = datetime.datetime.utcnow().second
        delay = 60 - now - 1
        return delay

    def build_OHLCV(self, ticks: list, symbol):
        """
        Args:
            ticks: A list of ticks to aggregate. Assumes the list's first tick
                is from the previous minute, this tick is used for open price.
            symbol: instrument ticker code (string)

        Returns:
            A 1 min OHLCV bar (dict).

        Raises:

        """

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
                   'timestamp': self.previous_minute(),
                   'open': open_price,
                   'high': high_price,
                   'low': low_price,
                   'close': close_price,
                   'volume': volume}
            return bar
        elif ticks is None or not ticks:
            bar = {'symbol': symbol,
                   'timestamp': self.previous_minute(),
                   'open': None,
                   'high': None,
                   'low': None,
                   'close': None,
                   'volume': 0}
            return bar

    def finished_parsing_ticks(self):
        return self.finished_parsing_ticks

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
    def get_recent_ticks(symbol, n):
        """
        Args:
            symbol: instrument ticker code (string)
            n: amount of bars

        Returns:
            List containing n minutes of recent ticks for the specified symbol.

        Raises:

        """

    @abstractmethod
    def parse_ticks(self):
        """
        Args:

        Returns:
            Converts streamed websocket tick data into a 1-min OHLCV bars, then
            appends new bars to the exchange object self.bars[symbol] tree.

        Raises:

        """
