from abc import ABC, abstractmethod


class Exchange(ABC):
    """ Exchange superclass
    """

    def __init__(self):
        super.__init__()

    @abstractmethod
    def get_candles(self, symbol: str, start: int, finish: int):
        """ Return dataframe of 1min OHLCV candle data for specified period
        """
        pass

    @abstractmethod
    def get_first_timestamp(self, symbol: str):
        """ Return int unix millisecond timestamp of first available
            1 min candle of a given asset
        """
        pass

    @abstractmethod
    def get_pairs(self):
        """ Return (tuple) all pairs.
        """
    pass

    @abstractmethod
    def get_name(self):
        """ Return (String) name
        """
    pass
