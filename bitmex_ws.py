from time import sleep
import websocket
import threading
import json
import traceback


class Bitmex_WS:

    MAX_SIZE = 1000

    def __init__(self, logger, symbols, channels, URL, api_key, api_secret):
        self.logger = logger
        self.data = {}
        self.keys = {}
        self.symbols = symbols
        self.channels = channels
        self.URL = URL
        if api_key is not None and api_secret is None:
            raise ValueError('Enter both public and secret keys')
        if api_key is None and api_secret is not None:
            raise ValueError('Enter both public and secret API keys')
        self.api_key = api_key
        self.api_secret = api_secret
        # websocket.enableTrace(True)
        self.connect()

    def connect(self):
        self.ws = websocket.WebSocketApp(
            self.URL,
            on_message=lambda ws, msg: self.on_message(ws, msg),
            on_error=lambda ws, msg: self.on_error(ws, msg),
            on_close=lambda ws: self.on_close(ws),
            on_open=lambda ws: self.on_open(ws))
        thread = threading.Thread(target=lambda: self.ws.run_forever())
        thread.daemon = True
        thread.start()
        self.logger.debug("Started BitMEX websocket thread")

        timeout = 5
        while not self.ws.sock or not self.ws.sock.connected and timeout:
            sleep(1)
            timeout -= 1
        if not timeout:
            self.exit()
            raise websocket.WebSocketTimeoutException(
                'WS Connection timed out.')

    def on_open(self, ws):
        ws.send(self.get_channel_subscription_string())

    def on_message(self, ws, msg):
        msg = json.loads(msg)
        # self.logger.debug(json.dumps(msg))
        table = msg['table'] if 'table' in msg else None
        action = msg['action'] if 'action' in msg else None
        try:
            if 'subscribe' in msg:
                self.logger.debug("Subscribed to BitMEX " + msg['subscribe'])
            elif action:
                if table not in self.data:
                    self.data[table] = []

            if action == 'partial':
                self.data[table] += msg['data']
                self.keys[table] = msg['keys']
            elif action == 'insert':
                self.data[table] += msg['data']
                # trim data table size when it exceeds MAX_SIZE
                if(table not in ['order', 'orderBookL2'] and
                        len(self.data[table]) > self.MAX_SIZE):
                    self.data[table] = self.data[table][int(self.MAX_SIZE / 2):] # noqa
            elif action == 'update':
                # Locate the item in the collection and update it.
                for updateData in msg['data']:
                    item = self.findItemByKeys(
                        self.keys[table],
                        self.data[table],
                        updateData)
                    if not item:
                        return  # No item found to update.
                    item.update(updateData)
                    # Remove cancelled / filled orders
                    if table == 'order' and not self.order_leaves_quantity(item): # noqa
                        self.data[table].remove(item)
            elif action == 'delete':
                # Locate the item in the collection and remove it.
                for deleteData in msg['data']:
                    item = self.findItemByKeys(
                        self.keys[table],
                        self.data[table],
                        deleteData)
                    self.data[table].remove(item)
            else:
                if action is not None:
                    raise Exception("Unknown action: %s" % action)
        except Exception:
            print(traceback.format_exc())

    def on_error(self, ws, msg):
        raise websocket.WebSocketException(msg)

    def on_close(self, ws):
        pass

    def get_orderbook(self):
        return self.data['orderBookL2']

    def get_ticks(self):
        return self.data['trade']

    def findItemByKeys(self, keys, table, matchData):
        for item in table:
            matched = True
            for key in keys:
                if item[key] != matchData[key]:
                    matched = False
            if matched:
                return item

    def get_channel_subscription_string(self):
        """Return a s"""
        prefix = '{"op": "subscribe", "args": ['
        suffix = ']}'
        string = ""
        count = 0
        for symbol in self.symbols:
            for channel in self.channels:
                string += '"' + channel + ':' + str(symbol) + '"'
                count += 1
                if count < len(self.channels) * len(self.symbols):
                    string += ", "
        return prefix + string + suffix

    def order_leaves_quantity(self, o):
        if o['leavesQty'] is None:
            return True
        return o['leavesQty'] > 0
