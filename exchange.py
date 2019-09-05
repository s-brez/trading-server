from abc import ABC, abstractmethod
import datetime


class Exchange(ABC):
    """Exchange abstract class for modelling individual brokers/exchanges."""

    def __init__(self):
        super.__init__()

    def get_new_bars(self):
        """Return dict of new 1min OHLCV bars."""
        return self.bars

    def get_max_bin_size(self):
        """"Return max number of bars allowed per REST API request"""
        return self.MAX_BARS_PER_REQUEST

    def get_symbols(self):
        """Return list of all instrument symbols strings."""
        return self.symbols

    def get_name(self):
        """Return name string."""
        return self.name

    def previous_minute(self):
        """ Return the previous minute UTC ms epoch timestamp."""

        delay = datetime.datetime.utcnow().second
        timestamp = datetime.datetime.utcnow() - datetime.timedelta(seconds=delay)
        timestamp.replace(second=0, microsecond=0)
        # convert to epoch
        timestamp = int(timestamp.timestamp())
        # replace final digit with zero, can be 1 or more during a slow cycle
        timestamp_str = list(str(timestamp))
        timestamp_str[len(timestamp_str) - 1] = "0"
        timestamp = int(''.join(timestamp_str))
        return timestamp

    def seconds_til_next_minute(self):
        """ Return number of seconds until T-1 sec to next minute."""

        now = datetime.datetime.utcnow().second
        delay = 60 - now - 1
        return delay

    def build_OHLCV(self, ticks: list, symbol):
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
    def get_bars_in_period(self):
        """Return list of historic 1min OHLCV bars for specified period."""

    @abstractmethod
    def get_origin_timestamp(self, symbol: str):
        """Return millisecond timestamp of first available 1 min bar."""

    @abstractmethod
    def parse_ticks(self):
        """Scrape previous minutes ticks."""
