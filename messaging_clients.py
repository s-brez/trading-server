"""
trading-server is a multi-asset, multi-strategy, event-driven trade execution
and backtesting platform (OEMS) for trading common markets.

Copyright (C) 2020  Sam Breznikar <sam@sdbgroup.io>

Licensed under GNU General Public License 3.0 or later.

Some rights reserved. See LICENSE.md, AUTHORS.md.
"""

from abc import ABC, abstractmethod
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
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
        self.main(self.get_token())

        self.PIN = "1234"

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
        Send a message when the command /start is issued.
        """

        update.message.reply_text('Hi!')

    def help_command(self, update, context):
        """
        Send a message when the command /help is issued.
        """
        update.message.reply_text('Help!')

    def echo(self, update, context):
        """
        Echo the user message.
        """
        update.message.reply_text(update.message.text)

    def main(self, token):
        """Start the bot."""

        updater = Updater(token=token, use_context=True)

        # Get the dispatcher to register handlers
        dp = updater.dispatcher

        # on different commands - answer in Telegram
        dp.add_handler(CommandHandler("start", self.start))
        dp.add_handler(CommandHandler("help", self.help_command))

        # on noncommand i.e message - echo the message on Telegram
        dp.add_handler(MessageHandler(Filters.text, self.echo))

        # Start the Bot
        updater.start_polling()

        # Run the bot until you press Ctrl-C or the process receives SIGINT,
        # SIGTERM or SIGABRT. This should be used most of the time, since
        # start_polling() is non-blocking and will stop the bot gracefully.
        updater.idle()
