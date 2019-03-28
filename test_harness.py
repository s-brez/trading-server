from server.server import *

server = Server()

server.data.create_new_datastore(
        "ZRXUSD"
        'Bitfinex',
        '1m',
        BFX.get_all_candles("ZRXUSD", '1m'))
