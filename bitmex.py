from exchange import Exchange


class Bitmex(Exchange):
    """
    BitMEX exchange model
    """

    def __init__(self, logger):
        super()
        self.logger = logger

    logger = object

