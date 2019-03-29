from server.server import *

server = Server()

# build all datastores (run once)
server.build_native_timeframe_datastores()
server.build_non_native_timeframe_datastores()

# update all datastores (run intermittently during development)
# to be superceded with websocket live stream
server.update_datastores()
