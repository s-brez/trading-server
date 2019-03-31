from server import Server

server = Server()

# build all datastores (run only once)
# server.build_native_timeframe_datastores()
# server.build_non_native_timeframe_datastores()

# # update all datastores (run intermittently during development)
# # to be superceded with websocket live stream
# server.update_datastores()

# Example - fetch and store data for asset, source and timeframe
server.data.create_new_datastore(
    "ZECUSD",
    "Bitfinex",
    "1m",
    server.exchanges[0].get_all_candles("ZECUSD", "1m"))
