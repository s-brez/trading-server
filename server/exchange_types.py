from abc import ABC, abstractmethod


class CryptoExchange(ABC):
    """ Cryptocurrency exchange superclass
        All cryptocurrency exchange classes to inherit this class
    """

    def __init__(self):
        super.__init__()

    @abstractmethod
    def get_all_candles(self, symbol, timeframe):
        """ Returns dataframe of all candle data of a given asset.
            Use this when creating new datastore.
        """
        pass

    @abstractmethod
    def get_new_candles(self, symbol, timeframe, start):
        """ Returns dataframe of candle data from start timestamp to
            current time. Use to update existing datastore.
        """
        pass

    @abstractmethod
    def get_ticker_values(self, symbol):
        """ Returns dataframe of ticker values of given asset.
            TODO: create variant that takes a list of all ticker codes.
        """
        pass

    @abstractmethod
    def get_genesis_timestamp(self, symbol, timeframe):
        """ Returns string timestamp of first available
            1 min candle of a given asset
        """
        pass

    # **********************************************
    # Use @property tag (getters) in child classes
    # for all methods below this point in this class
    # **********************************************

    @abstractmethod
    def timeframe_to_targettime(self, timeframe):
        """ Returns unix timestamp one unit before current
            time based on given timeframe
        """
        pass

    @abstractmethod
    def calculate_block_limit(self, timeframe):
        """ Return as an int the amount of candles to request per block
            based on the timeframe being requested
        """
        pass

    @abstractmethod
    def native_timeframes(self):
        """ Returns (tuple) native timeframes
        """
        pass

    @abstractmethod
    def non_native_timeframes(self):
        """ Return (tuple) non-native timeframes
        """
        pass

    @abstractmethod
    def get_usd_pairs(self):
        """ Returns tuple of usd pairs
        """
    pass

    @abstractmethod
    def get_btc_pairs(self):
        """ Returns (tuple) btc margin pairs
        """
    pass

    @abstractmethod
    def get_eth_pairs(self):
        """ Return (tuple) eth margin pairs
        """
    pass

    @abstractmethod
    def get_all_pairs(self):
        """ Return (tuple) all pairs.
        """
    pass

    @abstractmethod
    def get_name(self):
        """ Return (String) name
        """
    pass


class FXBroker(ABC):
    """ FX broker superclass
        All FX exchange broker to inherit this class
    """


class EquitiesBroker(ABC):
    """ Equities exchange superclass
        All equities/commodities broker classes to inherit this class
    """
