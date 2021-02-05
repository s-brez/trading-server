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
        print(image_path)
        print(text)

        print(self.whitelist)

        # Send image only to whitelisted users with active status
        for user_id in json.loads(self.whitelist):
            url = self.URL + self.token + "/sendPhoto"
            print(url)
            print(user_id)
            files = {'photo': open(image_path, 'rb')}
            data = {'chat_id': user_id}
            r = requests.post(url, files=files, data=data)
            print(r.status_code, r.reason, r.content)

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
