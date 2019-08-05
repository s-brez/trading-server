from event import MarketEvent
import time


class Datahandler:
    """Datahandler wraps exchange data and locally stored data with Market
    events and adds it to the event queue as each timeframe period elapses.
    Market events are created from either live or stored data (depending on
    if backtesting or live trading) and pushed to the event queue for the
    Strategy object to consume."""

    def __init__(self, exchanges, logger):
        self.exchanges = exchanges
        self.logger = logger
        self.live_trading = False
        self.total_instruments = self.get_total_instruments()

        # performance stats
        self.parse_count = 0
        self.total_parse_time = 0
        self.mean_parse_time = 0
        self.std_dev_parse_time = 0
        self.var_parse_time = 0

    def update_market_data(self, events):
        """Push new market events to the event queue"""

        if self.live_trading:
            market_data = self.get_new_data()
        else:
            market_data = self.get_historic_data()

        for event in market_data:
            events.put(event)
        self.logger.debug(events)
        return events

    def get_new_data(self):
        """Parse all new tick data, then return a list of market events
        (new bars) for all symbols from all exchanges for the just-elapsed
        time period."""

        # get timestamp to match for new bars
        timestamp = int(self.exchanges[0].previous_minute().timestamp())

        # record parse times
        self.logger.debug("Started parsing ticks.")
        start_parse = time.time()

        # parse new ticks
        for exchange in self.exchanges:
            exchange.parse_ticks()
        end_parse = time.time()
        duration = round(end_parse - start_parse, 5)
        self.logger.debug(
            "Parsed " + str(self.total_instruments) + " instruments in " +
            str(duration) + " seconds.")

        # record & update data parsing stats
        self.track_performance(duration)

        # wrap new data in market events
        new_market_events = []
        for exchange in self.exchanges:
            bars = exchange.get_bars()
            for symbol in exchange.get_symbols():
                for bar in bars[symbol]:
                    if bar['timestamp'] == timestamp:
                        event = MarketEvent(exchange.get_name(), bar)
                        new_market_events.append(event)
                        break
        return new_market_events

    def get_historic_data(self):
        """Return a list of market events (historic bars) from
        locally stored data."""

        historic_market_events = []

        return historic_market_events

    def store_new_bars(self, bars: list):
        """Save incoming data to local database."""

    def backfill_missing_data(self):
        """Check for missing data between the last locally-stored timestamp
        and initial timestamp time of currently streaming live data. If
        discrepencies exist, get and store the missing data."""

    def set_live_trading(self, live_trading):
        """Set true or false live execution flag"""

        self.live_trading = live_trading

    def get_total_instruments(self):
        """Return total number of monitored instruments."""

        total = 0
        for exchange in self.exchanges:
            total += len(exchange.get_symbols())
        return total

    def track_performance(self, duration):
        """Track tick processing times and other performance statistics."""

        self.parse_count += 1
        self.total_parse_time += duration
        self.mean_parse_time = self.total_parse_time / self.parse_count
