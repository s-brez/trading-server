from time import sleep
from threading import Thread
import websocket
import json
import traceback


class Bitmex_WS:

    def __init__(self, logger, symbols, channels, URL, api_key, api_secret):
        self.logger = logger
        self.symbols = symbols
        self.channels = channels
        self.URL = URL
        if api_key is not None and api_secret is None:
            raise ValueError('Enter both public and secret keys')
        if api_key is None and api_secret is not None:
            raise ValueError('Enter both public and secret API keys')
        self.api_key = api_key
        self.api_secret = api_secret
        self.data = {}
        self.keys = {}
        # websocket.enableTrace(True)

        # data table size - increase if ticks get cut off during high vol.
        self.MAX_SIZE = 1000 * len(symbols)
        self.RECONNECT_TIMEOUT = 10

        self.connect()

    def connect(self):
        """
        Args:

        Returns:
            Starts the websocket in a thread and connects to subscription
            channels.

        Raises:
        """

        self.ws = websocket.WebSocketApp(
            self.URL,
            on_message=lambda ws, msg: self.on_message(ws, msg),
            on_error=lambda ws, msg: self.on_error(ws, msg),
            on_close=lambda ws: self.on_close(ws),
            on_open=lambda ws: self.on_open(ws))

        thread = Thread(
            target=lambda: self.ws.run_forever(),
            daemon=True)
        thread.start()
        self.logger.debug("Started websocket daemon.")

        timeout = self.RECONNECT_TIMEOUT
        while not self.ws.sock or not self.ws.sock.connected and timeout:
            sleep(1)
            timeout -= 1
        if not timeout:
            self.logger.debug("Websocket connection timed out.")
            # attempt to reconnect
            if not self.ws.sock.connected:
                sleep(5)
                self.connect()

    def on_message(self, ws, msg):
        """
        Args:
            ws: WebSocketApp object
            msg: message object

        Returns:
            Handles incoming websocket messages.

        Raises:
            Exception("Unknown")
        """

        msg = json.loads(msg)
        # self.logger.debug(json.dumps(msg))
        table = msg['table'] if 'table' in msg else None
        action = msg['action'] if 'action' in msg else None
        try:
            if 'subscribe' in msg:
                self.logger.debug(
                    "Subscribed to " + msg['subscribe'] + ".")
            elif action:
                if table not in self.data:
                    self.data[table] = []

            if action == 'partial':
                self.data[table] = msg['data']
                self.keys[table] = msg['keys']
            elif action == 'insert':
                self.data[table] += msg['data']
                # trim data table size when it exceeds MAX_SIZE
                if(table not in ['order', 'orderBookL2'] and
                        len(self.data[table]) > self.MAX_SIZE):
                    self.data[table] = self.data[table][self.MAX_SIZE // 2:]
            elif action == 'update':
                # Locate the item in the collection and update it.
                for updateData in msg['data']:
                    item = self.find_item_by_keys(
                        self.keys[table],
                        self.data[table],
                        updateData)
                    if not item:
                        return  # No item found to update.
                    item.update(updateData)
                    # Remove cancelled / filled orders
                    if table == 'order' and not self.order_leaves_quantity(item):  # noqa
                        self.data[table].remove(item)
            elif action == 'delete':
                # Locate the item in the collection and remove it.
                for deleteData in msg['data']:
                    item = self.find_item_by_keys(
                        self.keys[table],
                        self.data[table],
                        deleteData)
                    self.data[table].remove(item)
            else:
                if action is not None:
                    raise Exception("Unknown action: %s" % action)
        except Exception:
            self.logger.debug(traceback.format_exc())

    def on_open(self, ws):
        """
        Args:
            ws: WebSocketApp object

        Returns:
            Invoked when websocket starts. Used to subscribe to channels.

        Raises:
        """

        ws.send(self.get_channel_subscription_string())

    def on_error(self, ws, msg):
        """
        Args:
            ws: WebSocketApp object
            msg: message object

        Returns:
            Invoked when websocket encounters an error. Will attempt to
            reconnect websocket after an error.

        Raises:
        """

        self.logger.debug("BitMEX websocket error: " + str(msg))

        # attempt to reconnect if  ws is not connected
        self.ws = None
        self.logger.debug("Attempting to reconnect.")
        sleep(self.RECONNECT_TIMEOUT)
        self.connect()

    def on_close(self, ws):
        """
        Args:
            ws: WebSocketApp object

        Returns:
            Invoked when websocket closes.

        Raises:
        """

        ws.close()

    def get_orderbook(self):
        """
        Args:

        Returns:
            L2 Orderbook (list).

        Raises:
        """

        return self.data['orderBookL2']

    def get_ticks(self):
        """
        Args:

        Returns:
            Ticks (list)

        Raises:
        """

        return self.data['trade']

    def find_item_by_keys(self, keys, table, match_data):
        """
        Args:
            keys: key array object
            table: data table object
            match_data: key to match

        Returns:
            Finds an item in the data table by the provided key.

        Raises:
        """
        for item in table:
            matched = True
            for key in keys:
                if item[key] != match_data[key]:
                    matched = False
            if matched:
                return item

    def get_channel_subscription_string(self):
        """
        Args:

        Returns:
            Subscription payload (string) for all symbols and channels.

        Raises:
        """

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
        """
        Args:
            o: item to match

        Returns:
            True if o['leavesQty'] is zero, False if > 0

        Raises:
        """
        if o['leavesQty'] is None:
            return True
        return o['leavesQty'] > 0
