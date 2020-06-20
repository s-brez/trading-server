"""
trading-server is a multi-asset, multi-strategy, event-driven trade execution
and backtesting platform (OEMS) for trading common markets.

Copyright (C) 2020  Sam Breznikar <sam@sdbgroup.io>

Licensed under GNU General Public License 3.0 or later.

Some rights reserved. See LICENSE.md, AUTHORS.md.
"""

from abc import ABC, abstractmethod
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                          BasePersistence)
import os


class MessagingClient(ABC):
    """
    """

    def __init__(self):
        pass


class Telegram(MessagingClient):
    """
    """

    def __init__(self, logger, portfolio):
        super().__init__()
        self.logger = logger
        self.token = self.get_token()

        self.whitelist = [410309133]
        self.attempted_access = []

        self.updater = Updater(token=self.token, use_context=True)
        self.dp = self.updater.dispatcher

        # Command message handler.
        self.dp.add_handler(CommandHandler("start", self.start))

        # Non-command message handlers.
        self.dp.add_handler(MessageHandler(Filters.text, self.non_cmd))

        self.updater.start_polling()
        self.updater.idle()

    def get_token(self):
        """
        Load bot token from environment variable.
        """

        if os.environ['TELEGRAM_BOT_TOKEN']:
            return os.environ['TELEGRAM_BOT_TOKEN']
        else:
            raise Exception("Telegram bot token missing.")

    def start(self, update, context):
        """
        Log start attempts.
        """

        self.attempted_access.append(update.message.from_user['id'])
        if update.message.from_user['id'] in self.whitelist:
            update.message.reply_text("User authenticated.")

    def non_cmd(self, update, context):
        """
        """
        pass
