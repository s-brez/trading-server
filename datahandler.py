from event import MarketEvent


class Datahandler:
    """
    Datahandler wraps exchange data and locally stored data with Market
    events and adds it to the event queue as each timeframe period elapses.

    Market events are created from either live or stored data (depending on
    if in backtesting or in live trading modes) and pushed to the event queue
    for the Strategy object to consume.
    """

    def __init__(self, exchanges, events, logger):
        self.exchanges = exchanges
        self.events = events
        self.logger = logger

    exchanges = []
    events = object
    logger = object
    live_trading = False

    def update_bars(self):
        """
        Pushes all new market events into the event queue

        """
        bars = []

        if self.live_trading:
            bars = self.get_new_bars()

        elif not self.live_trading:
            bars = self.get_historic_bars()

        for bar in bars:
            self.events.put(bar)

    def get_new_bars(self):
        """
        Return a list of market events containing new bars for all watched
        symbols from all exchanges for the just-elapsed time period.
        """
        new_bars = []

        for exchange in self.exchanges:
            for instrument in exchange.get_instruments():
                for timeframe in self.get_timeframes():
                    new_bars.append(
                        MarketEvent(
                            instrument.get_symbol(),
                            exchange.get_last_bar(
                                timeframe, instrument.get_symbol()),
                            exchange.get_name()))
        return new_bars

    def get_historic_bars(self):
        """
        Create market events containing "new" historic 1 min bars for all
        watched symbols
        """
        historic_bars = []

        return historic_bars

    def set_live_trading(self, live_trading):
        """
        Set true or false live execution flag
        """
        self.set_live_trading = live_trading

    def get_timeframes(self):
        """
        Return a list of timeframes relevant to the just-elapsed time period.
        E.g if time has just struck UTC 10:30am the list will contain "m1",
        "m5", "m15" and "30m" strings. The first minute of a new day or week 
        or month will return a new daily/weekly/monthly candle. Timeframes in
        use are 1, 3, 5, 15, 30, 60, 120, 180, 240, 360, 480 and 720 mins,
        1, 2 and 3 days, weekly and monthly.
        """
        timeframes = []
        if 
        return timframes
