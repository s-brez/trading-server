"""
trading-server is a multi-asset, multi-strategy, event-driven trade execution
and backtesting platform (OEMS) for trading common markets.

Copyright (C) 2020  Sam Breznikar <sam@sdbgroup.io>

Licensed under GNU General Public License 3.0 or later.

Some rights reserved. See LICENSE.md, AUTHORS.md.
"""

from abc import ABC, abstractmethod
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                          DictPersistence)
import json
import os


class MessagingClient(ABC):
    """
    """

    def __init__(self):
        pass


class Telegram(MessagingClient):

    def __init__(self, logger, portfolio):
        super().__init__()
        self.logger = logger
        self.token = self.get_token()
        self.whitelist = self.get_whitelist()

    def run(self):
        p_dict_str = str(json.dumps({"whitelist": self.whitelist, "active": None}))
        print(p_dict_str)
        self.p = DictPersistence(bot_data_json=p_dict_str)
        self.updater = Updater(token=self.token, persistence=self.p,
                               use_context=True)
        self.dp = self.updater.dispatcher
        self.dp.add_handler(CommandHandler("start", self.start))
        # self.dp.add_handler(MessageHandler(Filters.text, self.non_cmd))

        self.updater.start_polling()
        # Do not use this if bot is running in another thread.
        # self.updater.idle()

    def start(self, update, context):

        if update.message.from_user['id'] in context.bot_data['whitelist']:
            update.message.reply_text("User authenticated.")
            context.bot_data['active'] = {
                "user_id": update.message.from_user['id'],
                "chat_id": update.message['chat']['id']}

            # print(update.message)
            # print(context.bot_data['active'])

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
