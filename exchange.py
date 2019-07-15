from abc import ABC, abstractmethod


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
    def get_last_bar(self, instrument: str, timeframe: str):
        """
        Return OHLCV bar for specified symbol and timeframe for the
        just-elapsed period.
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
    def subscribe_ws(self, instruments: list):
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
