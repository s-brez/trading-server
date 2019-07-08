from server import Server
import datetime

server = Server()

print(server.data.exchanges[0].get_candles("BTCUSD"))
