"""
trading-server is a multi-asset, multi-strategy, event-driven execution
and backtesting platform (OEMS) for trading common markets.

Copyright (C) 2020  Sam Breznikar <sam@sdbgroup.io>

Licensed under GNU General Public License 3.0 or later.

Some rights reserved. See LICENSE.md, AUTHORS.md.
"""

from pymongo import MongoClient, errors
from threading import Thread
from flask import Flask, Response, request
from time import sleep
import logging
import sys
import json


DB_URL = 'mongodb://127.0.0.1:27017/'
DB_PRICES = 'asset_price_master'
DB_OTHER = 'holdings_trades_signals_master'
DB_TIMEOUT_MS = 30

db_client = MongoClient(DB_URL, serverSelectionTimeoutMS=DB_TIMEOUT_MS)
db_prices = db_client[DB_PRICES]
db_other = db_client[DB_OTHER]

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s:%(levelname)s:%(module)s - %(message)s",
    datefmt="%d-%m-%Y %H:%M:%S")
ch.setFormatter(formatter)
logger.addHandler(ch)

app = Flask(__name__)


# Portfolio data route
@app.route("/portfolio", methods=['GET'])
def return_portfolio():
    if request.method == 'GET':

        portfolio = db_other['portfolio'].find_one({"id": 1}, {"_id": 0})
        if portfolio:
            return json.dumps(portfolio), 200, {'ContentType':'application/json'}
        else:
            return json.dumps({'success': False, 'message': 'Not found'}),
            404, {'ContentType':'application/json'}

    else:
        return json.dumps({'success': False, 'message': 'Invalid method'}),
        403, {'ContentType':'application/json'}


# Portfolio settings route
@app.route("/portfolio/settings/<new_state>", methods=['POST'])
def change_portfolio_settings():
    if request.method == 'POST':
        return " Posted to /portfolio/settings/ successfully"

        # TODO: set new portfolio settings

    else:
        return json.dumps({'success': False, 'message': 'Invalid method'}),
        403, {'ContentType':'application/json'}


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80, debug=False)
