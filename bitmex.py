from bitmex_websocket import BitMEXWebsocket
from exchange import Exchange
import datetime
from dateutil import parser
from time import sleep


class Bitmex(Exchange):
    """BitMEX exchange model"""

    MAX_BARS_PER_REQUEST = 750
    BASE_URL = "https://www.bitmex.com/api/v1"
    BARS_URL = "/trade/bucketed?binSize="
    TIMESTAMP_FORMAT = '%Y-%m-%d%H:%M:%S.%f'

    def __init__(self, logger):
        super()
        self.logger = logger
        self.name = "BitMEX"
        self.ws = BitMEXWebsocket(
            endpoint="https://testnet.bitmex.com/api/v1",
            symbol="XBTUSD", api_key=None, api_secret=None)

        self.one_minute_bars = []
        self.ticks_minute_elapsed = []
        self.count = 0

        while self.ws.ws.sock.connected:
            # get tick data at first second of every minute
            if datetime.datetime.utcnow().second <= 1:
                # only get ticks after one minute passed
                if self.count >= 1:
                    ticks = self.ws.recent_trades()
                    # grab only the just-elapsed minute's ticks
                    # TODO start iteration from end of list
                    for tick in ticks:
                        ts = parser.parse(tick['timestamp'])
                        if ts.minute == datetime.datetime.utcnow().minute - 1:
                            self.ticks_minute_elapsed.append(tick)
                    # get open, high, low and close prices
                    prices = [i['price'] for i in self.ticks_minute_elapsed]
                    open_price = self.ticks_minute_elapsed[0]['price']
                    high_price = max(prices)
                    low_price = min(prices)
                    close_price = self.ticks_minute_elapsed[-1]['price']
                    bar = {'symbol': 'XBTUSD',
                           'timestamp': self.previous_minute(),
                           'open': open_price,
                           'high': high_price,
                           'low': low_price,
                           'close': close_price}
                    self.one_minute_bars.append(bar)

                self.count += 1

                # sleep until 1 second before the next minute starts
                now = datetime.datetime.utcnow().second
                delay = 60 - now - 1
                sleep(delay)
            sleep(0.05)

    def get_bars(self, instrument: str, start: int, finish: int):
        """ Returns list of all bars, containing all symbols
        """
        return self.one_minute_bars

    def get_first_timestamp(self, instrument: str):
        """
        """
        pass

    def get_instruments(self):
        """
        """
        pass

    def listen_ws(self, instruments: list):
        """
        """

    def get_name(self):
        """
        """
        pass

