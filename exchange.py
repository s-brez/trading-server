from abc import ABC, abstractmethod
import datetime
import ping
import socket


class Exchange(ABC):
    """Exchange abstract class for modelling individual brokers/exchanges."""

    def __init__(self):
        super.__init__()

    def get_bars(self):
        """Return dict of new 1min OHLCV bars."""
        return self.bars

    @abstractmethod
    def get_bars_in_period(self, ):
        """Return list of historic 1min OHLCV bars for specified period."""

    @abstractmethod
    def get_first_timestamp(self, instrument: str):
        """Return millisecond timestamp of first available 1 min bar."""

    @abstractmethod
    def parse_ticks(self):
        """Scrape the correct ticks from a given list of all ticks, ready to be
        passed to build_OHLCV"""

    def ping(self):
        """Ping the destination exchange"""
        try:
            ping.verbose_ping(self.BASE_URL, count=3)
            delay = ping.Ping(self.WS_URL, timeout=2000).do()
        except socket.error as e:
            self.logger.debug("Ping error: ", e)


    def get_instruments(self):
        """Return list of all instrument symbols strings."""
        return self.symbols

    def get_name(self):
        """Return name string."""
        return self.name

    def previous_minute(self):
        """ Return the previous minutes UTC timestamp."""
        timestamp = datetime.datetime.utcnow() - datetime.timedelta(minutes=1)
        timestamp.replace(second=0, microsecond=0)
        return timestamp

    def seconds_til_next_minute(self):
        """ Return number of seconds until T-1 sec to next minute."""
        now = datetime.datetime.utcnow().second
        delay = 60 - now - 1
        return delay

    def build_OHLCV(self, ticks: list, symbol):
        """Return a 1 min bar dict from a given list of ticks """
        if ticks is not None:
            prices = [i['price'] for i in ticks]
            volume = sum(i['size'] for i in ticks)
            high_price = max(prices) if len(prices) >= 1 else None
            low_price = min(prices) if len(prices) >= 1 else None
            open_price = ticks[0]['price'] if len(prices) >= 1 else None
            close_price = ticks[-1]['price'] if len(prices) >= 1 else None
            # format OHLCV as 1 min bar
            bar = {'symbol': symbol,
                   'timestamp': int(self.previous_minute().timestamp()), # noqa
                   'open': open_price,
                   'high': high_price,
                   'low': low_price,
                   'close': close_price,
                   'volume': volume}
            return bar
        elif ticks is None:
            bar = {'symbol': symbol,
                   'timestamp': int(self.previous_minute().timestamp()), # noqa
                   'open': None,
                   'high': None,
                   'low': None,
                   'close': None,
                   'volume': 0}
            return bar

