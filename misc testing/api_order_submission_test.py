from datetime import timezone, datetime, timedelta
from pymongo import MongoClient, errors
from requests import Request, Session
from requests.auth import AuthBase
from urllib.parse import urlparse
from dateutil import parser
import traceback
import requests
import hashlib
import os
import json
import hmac
import time


MAX_BARS_PER_REQUEST = 750
TIMESTAMP_FORMAT = '%Y-%m-%d%H:%M:%S.%f'

BASE_URL = "https://www.bitmex.com/api/v1"
BASE_URL_TESTNET = "https://testnet.bitmex.com/api/v1"
WS_URL = "wss://www.bitmex.com/realtime"
BARS_URL = "/trade/bucketed?binSize="
TICKS_URL = "/trade?symbol="
POSITIONS_URL = "/position"
ORDERS_URL = "/order"
BULK_ORDERS_URL = "/order/bulk"
TRADE_HIST_URL = "/execution/tradeHistory"

DB_URL = 'mongodb://127.0.0.1:27017/'
DB_PRICES = 'asset_price_master'
DB_OTHER = 'holdings_trades_signals_master'
DB_TIMEOUT_MS = 10

symbol_min_increment = {
    'XBTUSD': 0.5,
    'ETHUSD': 0.05,
    'XRPUSD': 0.0001}

db_client = MongoClient(
    DB_URL,
    serverSelectionTimeoutMS=DB_TIMEOUT_MS)
db_prices = db_client[DB_PRICES]
db_other = db_client[DB_OTHER]


def load_api_keys():
    venue_name = "BITMEX"
    key = os.environ[venue_name + '_API_KEY']
    secret = os.environ[venue_name + '_API_SECRET']
    return key, secret


api_key, api_secret = load_api_keys()


def generate_request_signature(secret, request_type, url, nonce,
                               data):

    parsed_url = urlparse(url)
    path = parsed_url.path

    if parsed_url.query:
        path = path + '?' + parsed_url.query

    if isinstance(data, (bytes, bytearray)):
        data = data.decode('utf8')

    message = str(request_type).upper() + path + str(nonce) + data
    signature = hmac.new(bytes(secret, 'utf8'), bytes(message, 'utf8'),
                         digestmod=hashlib.sha256).hexdigest()

    return signature


def generate_request_headers(request, api_key, api_secret):

    nonce = str(int(round(time.time()) + 20))
    request.headers['api-expires'] = nonce
    request.headers['api-key'] = api_key
    request.headers['api-signature'] = generate_request_signature(
        api_secret, request.method, request.url, nonce, request.body or '')
    request.headers['Content-Type'] = 'application/json'
    request.headers['Accept'] = 'application/json'
    request.headers['X-Requested-With'] = 'XMLHttpRequest'

    return request


def get_positions():
    s = Session()
    prepared_request = Request(
        'GET',
        BASE_URL_TESTNET + POSITIONS_URL,
        params='').prepare()
    request = generate_request_headers(prepared_request, api_key,
                                       api_secret)
    response = s.send(request).json()

    return response


def round_increment(number, symbol):
    inc = symbol_min_increment[symbol]
    if number < 1:
        quote = number
    else:
        quote = (number // inc) * inc
    return quote


def format_orders(orders):
    formatted = []
    for order in orders:
        price = round_increment(order['price'], order['symbol'])

        # TODO: add logic for below three fields.
        execInst = None
        stopPx = None
        timeInForce = None

        symbol = order['symbol']
        side = "Buy" if order['direction'] == "LONG" else "Sell"
        orderQty = round_increment(order['size'], order['symbol'])
        clOrdID = order['order_id']
        text = order['metatype']

        if order['order_type'] == "LIMIT":
            ordType = "Limit"
        elif order['order_type'] == "MARKET":
            ordType = "Market"
            price = None
        elif order['order_type'] == "STOP_LIMIT":
            ordType = "StopLimit"
        elif order['order_type'] == "STOP":
            ordType = "Stop"
            stopPx = price
            price = None
        else:
            ordType = None

        formatted.append({
                'symbol': symbol,
                'side': side,
                'orderQty': orderQty,
                'price': price,
                'stopPx': stopPx,
                'clOrdID': int(order['order_id']),
                'ordType': ordType,
                'timeInForce': timeInForce,
                'execInst': execInst,
                'text': text})

    return formatted


def place_single_order(order):
    payload = format_orders([order])[0]

    s = Session()

    prepared_request = Request(
        'POST',
        BASE_URL_TESTNET + ORDERS_URL,
        json=payload,
        params='').prepare()

    request = generate_request_headers(
        prepared_request,
        api_key,
        api_secret)

    response = s.send(request)

    return response


def place_bulk_orders(orders):

    # Separate market orders as BitMEX doesnt allow bulk market orders.
    m_o = [o for o in orders if o['order_type'] == "MARKET"]
    nm_o = [o for o in orders if o not in m_o]

    # Send market orders individually amd store responses.
    responses = [place_single_order(o) for o in m_o if m_o]

    # Submit non-market orders in a single batch.
    response = None
    if nm_o:
        payload = {'orders': format_orders(nm_o)}

        s = Session()

        prepared_request = Request(
            'POST',
            BASE_URL_TESTNET + BULK_ORDERS_URL,
            json=payload,
            params='').prepare()

        request = generate_request_headers(
            prepared_request,
            api_key,
            api_secret)

        response = s.send(request)

    # Unpack successful order confirmations and handle errors.
    order_confirmations = []
    for r in responses + [response]:
        if r.status_code == 200:

            res = r.json()

            if isinstance(res, list):
                for item in res:
                    order_confirmations.append(item)

            elif isinstance(res, dict):
                order_confirmations.append(res)

        elif 400 <= r.status_code <= 404:
            # Syntax, auth or system limit error messages, raise exception.
            raise Exception(r.status_code, r.json()['error']['message'])

        elif r.status_code == 503:
            # Server overloaded, retry after 500ms, dont raise exception.
            print(r.status_code, r.json()['error']['message'])

            # TODO: Check what orders were placed (if any) and re-submit.

        else:
            print(r.status_code, r.json())

    updated_orders = []
    if order_confirmations:
        for res in order_confirmations:
            for order in orders:
                if int(order['order_id']) == int(res['clOrdID']):

                    if res['ordStatus'] == 'Filled':
                        fill = "FILLED"
                    elif res['ordStatus'] == 'New':
                        fill = "NEW"

                    updated_orders.append({
                        'trade_id': order['trade_id'],
                        'position_id': order['position_id'],
                        'order_id': order['order_id'],
                        'timestamp': res['timestamp'],
                        'avg_fill_price': res['avgPx'],
                        'currency': res['currency'],
                        'venue_id': res['orderID'],
                        'venue': order['venue'],
                        'symbol': order['symbol'],
                        'direction': order['direction'],
                        'size': res['orderQty'],
                        'price': res['price'],
                        'order_type': order['order_type'],
                        'metatype': order['metatype'],
                        'void_price': order['void_price'],
                        'trail': order['trail'],
                        'reduce_only': order['reduce_only'],
                        'post_only': order['post_only'],
                        'batch_size': order['batch_size'],
                        'status': fill})

    return updated_orders


def cancel_orders(order_ids: list):
    payload = {"orderID": order_ids}
    print(payload)
    s = Session()
    prepared_request = Request(
        "DELETE",
        BASE_URL_TESTNET + ORDERS_URL,
        json=payload,
        params='').prepare()

    request = generate_request_headers(
        prepared_request,
        api_key,
        api_secret)

    response = s.send(request).json()

    return response


def close_position(symbol: str):
    positions = get_positions()
    for pos in positions:
        if pos['symbol'] == symbol:
            position = pos
            break

    if position:
        payload = {
            'symbol': symbol,
            'orderQty': -pos['currentQty'],
            'ordType': "Market"}

        s = Session()

        prepared_request = Request(
            'POST',
            BASE_URL_TESTNET + ORDERS_URL,
            json=payload,
            params='').prepare()

        request = generate_request_headers(
            prepared_request,
            api_key,
            api_secret)

        response = s.send(request).json()
        if response['ordStatus'] == "Filled":
            return True
        else:
            return False


def get_executions(symbol, start_timestamp=None, count=500):
    payload = {
        'symbol': symbol,
        'count': count,
        'start': start_timestamp,
        'reverse': True}

    prepared_request = Request(
        'GET',
        BASE_URL_TESTNET + TRADE_HIST_URL,
        json=payload,
        params='').prepare()

    request = generate_request_headers(
        prepared_request,
        api_key,
        api_secret)

    response = Session().send(request).json()

    executions = []
    for res in response:

        fee_type = "TAKER" if res['lastLiquidityInd'] == "RemovedLiquidity" else "MAKER"
        direction = "LONG" if res['side'] == "Buy" else "SHORT"

        if res['ordStatus'] == "Filled":
            fill = "FILLED"
        elif res['ordStatus'] == "Cancelled":
            fill = "CANCELLED"
        elif res['ordStatus'] == "New":
            fill = "NEW"
        elif res['ordStatus'] == "PartiallyFilled":
            fill = "PARTIAL"
        else:
            raise Exception(res['ordStatus'])

        if res['ordType'] == "Limit":
            order_type = "LIMIT"
        elif res['ordType'] == "Market":
            order_type = "MARKET"
        elif res['ordType'] == "StopLimit":
            order_type = "STOP_LIMIT"
        elif res['ordType'] == "Stop":
            order_type = "STOP"
        else:
            raise Exception(res['ordType'])

        executions.append({
                'order_id': res['clOrdID'],
                'venue_id': res['orderID'],
                'timestamp': int(parser.parse(res['timestamp']).timestamp()),
                'avg_exc_price': res['avgPx'],
                'currency': res['currency'],
                'symbol': res['symbol'],
                'direction': direction,
                'size': res['lastQty'],
                'order_type': res['ordType'],
                'fee_type': fee_type,
                'fee_amt': res['commission'],
                'total_fee': res['execComm'] / res['avgPx'],
                'status': fill})

    return executions


def get_orders(symbol, start_timestamp=None, count=500):
    payload = {
        'symbol': symbol,
        'count': count,
        'start': start_timestamp,
        'reverse': True}

    prepared_request = Request(
        'GET',
        BASE_URL_TESTNET + ORDERS_URL,
        params='', json=payload).prepare()

    request = generate_request_headers(
        prepared_request,
        api_key,
        api_secret)

    response = Session().send(request).json()

    # return response

    orders = []
    for res in response:
        # if res['clOrdID']:

        direction = "LONG" if res['side'] == "Buy" else "SHORT"

        if res['ordStatus'] == "Filled":
            fill = "FILLED"
        elif res['ordStatus'] == "Canceled":
            fill = "CANCELLED"
        elif res['ordStatus'] == "New":
            fill = "NEW"
        elif res['ordStatus'] == "PartiallyFilled":
            fill = "PARTIAL"
        else:
            raise Exception(res['ordStatus'])

        if res['ordType'] == "Limit":
            order_type = "LIMIT"
        elif res['ordType'] == "Market":
            order_type = "MARKET"
        elif res['ordType'] == "StopLimit":
            order_type = "STOP_LIMIT"
        elif res['ordType'] == "Stop":
            order_type = "STOP"
        else:
            raise Exception(res['ordType'])

        # If "\n" in response text field, use substring after "\n".
        if "\n" in res['text']:
            text = res['text'].split("\n")
            metatype = text[1]
        elif (
            res['text'] == "ENTRY" or res['text'] == "STOP" or res['text'] ==
                "TAKE_PROFIT" or res['text'] == "FINAL_TAKE_PROFIT"):
            metatype = res['text']
        else:
            # raise Exception("Order metatype error:", res['text'])
            print("Order metatype error:", res['text'])
            metatype = res['text']

        orders.append({
            'order_id': res['clOrdID'],
            'venue_id': res['orderID'],
            'timestamp': int(parser.parse(res['timestamp']).timestamp()),
            'price': res['price'],
            'avg_fill_price': res['avgPx'],
            'currency': res['currency'],
            'venue': "BitMEX",
            'symbol': res['symbol'],
            'direction': direction,
            'size': res['orderQty'],
            'order_type': order_type,
            'metatype': metatype,
            'void_price': res['stopPx'],
            'status': fill})

    return orders

# id_pairs = {
#     'e5f4bbcf-ec61-c2c5-0365-c0b1d57d4e57': '64-1',
#     'd76349e3-4d27-3764-7c71-c58a8b6955f3': '63-1'}

# ids_for_cancellation = [
#     'e5f4bbcf-ec61-c2c5-0365-c0b1d57d4e57',
#     'd76349e3-4d27-3764-7c71-c58a8b6955f3']

# print(cancel_orders(ids_for_cancellation))


portfolio = db_other['portfolio'].find_one({"id": 1}, {"_id": 0})

print(json.dumps(portfolio, indent=2))
