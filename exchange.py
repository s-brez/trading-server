from abc import ABC, abstractmethod
import datetime


class Exchange(ABC):
    """
    Broker/Exchange abstract class for modelling individual brokers/exchanges.
    """

    def __init__(self):
        super.__init__()

    @abstractmethod
    def get_bars(self, instrument: str, start: int, finish: int):
        """
        Return list of 1min OHLCV bars for specified period.
        Millisecond timestamp used for start and finish.
        """
        pass

    @abstractmethod
    def get_first_timestamp(self, instrument: str):
        """
        Return millisecond timestamp of first available
        1 min bar.
        """
        pass

    @abstractmethod
    def get_instruments(self):
        """
        Return list of all instrument symbols as strings.
        """
        pass

    @abstractmethod
    def listen_ws(self, instruments: list):
        """
        Subscribes to websocket tick data streams for specified list of
        instruments
        """

    @abstractmethod
    def get_name(self):
        """
        Return name string.
        """
        pass

    def previous_minute():
        timestamp = datetime.datetime.utcnow() - datetime.timedelta(minutes=1)
        timestamp.replace(second=0, microsecond=0)
        return timestamp
