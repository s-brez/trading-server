"""
trading-server is a multi-asset, multi-strategy, event-driven trade execution
and backtesting platform (OEMS) for trading common markets.

Copyright (C) 2020  Sam Breznikar <sam@sdbgroup.io>

Licensed under GNU General Public License 3.0 or later.

Some rights reserved. See LICENSE.md, AUTHORS.md.
"""

from abc import ABC
import json
import os
import requests


class MessagingClient(ABC):
    """
    """

    def __init__(self):
        pass


class Telegram(MessagingClient):

    URL = "https://api.telegram.org/bot"

    def __init__(self, logger):
        super().__init__()
        self.logger = logger
        self.token = self.get_token()
        self.whitelist = self.get_whitelist()

    def send_image(self, image_path, text):

        url = self.URL + self.token + "/sendPhoto"
        files = {'photo': open(image_path, 'rb')}

        # Send image only to whitelisted users
        for user_id in json.loads(self.whitelist):

            data = {'chat_id': user_id, 'caption': text}
            r = requests.post(url, files=files, data=data)

            if int(r.status_code) == 200:
                self.logger.info("Setup snapshot sent to " + str(user_id) + ".")
            else:
                self.logger.info("Sending snapshot to " + str(user_id) + " failed.")
                print(r.status_code)

    def send_option_keyboard(self, keyboard):

        url = self.URL + self.token + "/sendMessage"
        reply_markup = {"keyboard": keyboard, "one_time_keyboard": True}

        # Send only to whitelisted users
        for user_id in json.loads(self.whitelist):
            text = {'text': "Accept or veto trade:", 'chat_id': user_id, 'reply_markup': reply_markup}

            r = requests.post(url, json=text)

            if int(r.status_code) == 200:
                self.logger.info("Consent query sent to " + str(user_id) + ".")
            else:
                self.logger.info("Sending consent query to " + str(user_id) + " failed.")
                print(r.status_code)

    def get_updates(self):
        url = self.URL + self.token + "/getUpdates"
        r = requests.get(url).json()
        return r['result']

    def get_token(self):
        """
        Load bot token from environment variable.
        """

        if os.environ['TELEGRAM_BOT_TOKEN'] is not None:
            return os.environ['TELEGRAM_BOT_TOKEN']
        else:
            raise Exception("Telegram bot token missing.")

    def get_whitelist(self):
        """
        Load whitelist from environment variable.
        """

        if os.environ['TELEGRAM_BOT_WHITELIST'] is not None:
            return os.environ['TELEGRAM_BOT_WHITELIST']
        else:
            raise Exception("Telegram bot token missing.")
