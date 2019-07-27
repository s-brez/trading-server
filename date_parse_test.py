import websocket
import threading
import json
import traceback


class Threadtest:

    MAX_SIZE = 200

    def __init__(self):
        self.data = {}
        self.keys = {}
        self.symbols = ("XBTUSD", "ETHUSD")
        self.channels = ("trade", "orderBookL2")
        self.URL = 'wss://testnet.bitmex.com/realtime'
        self.ws = websocket.WebSocketApp(
            self.URL,
            on_message=lambda ws, msg: self.on_message(ws, msg),
            on_error=lambda ws, msg: self.on_error(ws, msg),
            on_close=lambda ws: self.on_close(ws),
            on_open=lambda ws: self.on_open(ws))

        # self.ws.on_open = lambda self: self.send(
        #     '{"op": "subscribe", "args": ["trade:XBTUSD", "trade:ETHUSD"]}')

        # websocket.enableTrace(True)
        thread = threading.Thread(target=self.ws.run_forever())
        thread.daemon = True
        thread.start()

    def on_error(self, ws, msg):
        raise websocket.WebSocketException(msg)

    def on_close(self, ws):
        pass

    def on_open(self, ws):
        ws.send(self.get_channel_subscription_string())

    def on_message(self, ws, msg):
        msg = json.loads(msg)

        table = msg['table'] if 'table' in msg else None
        action = msg['action'] if 'action' in msg else None
        try:
            if 'subscribe' in msg:
                print("Subscribed to: " + msg['subscribe'])
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
                    self.data[table] = self.data[table][int(self.MAX_SIZE) / 2:] # noqa
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

        # self.ws.on_open = lambda self: self.send(
        #     '{"op": "subscribe", "args": ["trade:XBTUSD", "trade:ETHUSD"]}')

    def get_channel_subscription_string(self):
        prefix = '{"op": "subscribe", "args": ['
        suffix = ']}'
        string = ""
        count = 0
        for symbol in self.symbols:
            for channel in self.channels:
                string += '"' + channel + ':' + str(symbol) + '"'
                count += 1
                if count < len(self.channels) + len(self.symbols):
                    string += ", "
        return prefix + string + suffix

    def findItemByKeys(self, keys, table, matchData):
        for item in table:
            matched = True
            for key in keys:
                if item[key] != matchData[key]:
                    matched = False
            if matched:
                return item

    def order_leaves_quantity(self, o):
        if o['leavesQty'] is None:
            return True
        return o['leavesQty'] > 0


tt = Threadtest()
