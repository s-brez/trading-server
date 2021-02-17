"""
trading-server is a multi-asset, multi-strategy, event-driven execution
and backtesting platform (OEMS) for trading common markets.

Copyright (C) 2020  Sam Breznikar <sam@sdbgroup.io>

Licensed under GNU General Public License 3.0 or later.

Some rights reserved. See LICENSE.md, AUTHORS.md.
"""

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

        # Data table size - approcimate tick/min capacity per symbol.
        self.MAX_SIZE = 15000 * len(symbols)
        self.RECONNECT_TIMEOUT = 10

        self.connect()

    def connect(self):
        """
        Args:
            None

        Returns:
            Starts the websocket in a thread and connects to subscription
            channels.

        Raises:
            None.
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
        self.logger.info("Started websocket daemon.")

        timeout = self.RECONNECT_TIMEOUT
        while not self.ws.sock or not self.ws.sock.connected and timeout:
            sleep(1)
            timeout -= 1
        if not timeout:
            self.logger.info("Websocket connection timed out.")
            # Attempt to reconnect
            if not self.ws.sock.connected:
                sleep(5)
                self.connect()

    def on_message(self, ws, msg):
        """
        Handles incoming websocket messages.

        Args:
            ws: WebSocketApp object
            msg: message object

        Returns:
            None.

        Raises:
            Exception("Unknown")
        """

        msg = json.loads(msg)
        # self.logger.info(json.dumps(msg))
        table = msg['table'] if 'table' in msg else None
        action = msg['action'] if 'action' in msg else None
        try:

            if 'subscribe' in msg:
                self.logger.info(
                    "Subscribed to " + msg['subscribe'] + ".")

            elif action:
                if table not in self.data:
                    self.data[table] = []

            if action == 'partial':
                self.data[table] = msg['data']
                self.keys[table] = msg['keys']

            elif action == 'insert':
                self.data[table] += msg['data']

                # Trim data table size when it exceeds MAX_SIZE.
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
                    # Remove cancelled / filled orders.
                    if table == 'order' and not self.match_leaves_quantity(item):  # noqa
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
            self.logger.info(traceback.format_exc())

    def on_open(self, ws):
        """
        Invoked when websocket starts. Used to subscribe to channels.

        Args:
            ws: WebSocketApp object

        Returns:
            None.

        Raises:
            None.
        """

        ws.send(self.get_channel_subscription_string())

    def on_error(self, ws, msg):
        """
        Invoked when websocket encounters an error. Will attempt to
        reconnect websocket after an error.

        Args:
            ws: WebSocketApp object
            msg: message object

        Returns:
            None.

        Raises:
            None.
        """

        self.logger.info("BitMEX websocket error: " + str(msg))

        # attempt to reconnect if  ws is not connected
        self.ws = None
        self.logger.info("Attempting to reconnect.")
        sleep(self.RECONNECT_TIMEOUT)
        self.connect()

    def on_close(self, ws):
        """
        Invoked when websocket closes.

        Args:
            ws: WebSocketApp object

        Returns:
            Invoked when websocket closes.

        Raises:
            None.
        """

        ws.close()

    def get_orderbook(self):
        """
        Returns the L2 orderbook.

        Args:
            None.

        Returns:
            L2 Orderbook (list).

        Raises:
            None.
        """

        return self.data['orderBookL2']

    def get_ticks(self):
        """
        Returns ticks for the recent minute.

        Args:
            None.

        Returns:
            Ticks (list)

        Raises:
            None.
        """

        return self.data['trade']

    def find_item_by_keys(self, keys, table, match_data):
        """
        Finds an item in the data table using the provided key.

        Args:
            keys: key array object
            table: data table object
            match_data: key to match

        Returns:
            item: matched item.

        Raises:
            None.
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
        Returns websocket channel subscription string.

        Args:
            None.

        Returns:
            Subscription payload (string) for all symbols and channels.

        Raises:
            None.
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

    def match_leaves_quantity(self, o):
        """
        Args:
            o: item to match
        Returns:
            True if o['leavesQty'] is zero, False if > 0

        Raises:
            None.
        """
        if o['leavesQty'] is None:
            return True
        return o['leavesQty'] > 0
