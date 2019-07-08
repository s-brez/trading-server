from exchange import Exchange


class Bitmex(Exchange):
    """
    BitMEX exchange model
    """

    def __init__(self, logger):
        super()
        self.logger = logger

    logger = object

    def get_bars(self, symbol: str, start: int, finish: int):
        """
        """
        pass

    def get_last_bar(self, symbol: str, timeframe: str):
        """
        """
        pass

    def get_first_timestamp(self, symbol: str):
        """
        """
        pass

    def get_instruments(self):
        """
        """
        pass

    def subscribe_ws(self, instruments: list):
        """
        """

    def get_name(self):
        """
        Return name string.
        """
        pass

