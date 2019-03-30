from server import Server

server = Server()

# build all datastores (run once)
# server.build_native_timeframe_datastores()
# server.build_non_native_timeframe_datastores()

# # update all datastores (run intermittently during development)
# # to be superceded with websocket live stream
# server.update_datastores()

server.data.create_new_datastore(
    "ZRXUSD",
    "Bitfinex",
    "1m",
    server.exchanges[0].get_all_candles("ZRXUSD", "1m"))

# print(server.exchanges[0].get_name)
