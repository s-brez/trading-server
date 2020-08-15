"""
trading-server is a multi-asset, multi-strategy, event-driven trade execution
and backtesting platform (OEMS) for trading common markets.

Copyright (C) 2020  Sam Breznikar <sam@sdbgroup.io>

Licensed under GNU General Public License 3.0 or later.

Some rights reserved. See LICENSE.md, AUTHORS.md.
"""

from abc import ABC, abstractmethod
from telegram.ext import Updater, MessageHandler, Filters
import os


class MessagingClient(ABC):
    """
    """

    def __init__(self):
        pass


class Telegram(MessagingClient):
    """
    """

    def __init__(self, logger):
        super().__init__()
        self.logger = logger
        self.token = self.get_token()
        self.updater = Updater(token=self.token, use_context=True)

    def get_token(self):
        """
        Load bot token from environment variable.
        """

        if os.environ['TELEGRAM_BOT_TOKEN']:
            return os.environ['TELEGRAM_BOT_TOKEN']
        else:
            raise Exception("Telegram bot token missing.")
