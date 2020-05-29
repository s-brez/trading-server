from datetime import timezone, datetime, timedelta
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
symbol_min_increment = {
    'XBTUSD': 0.5,
    'ETHUSD': 0.05,
    'XRPUSD': 0.0001}


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


orders = [{'trade_id': 47, 'position_id': None, 'order_id': 119131,
           'venue': 'BitMEX', 'symbol': 'XBTUSD', 'direction': 'LONG',
           'size': 334.0, 'price': 9172.5, 'order_type': 'MARKET',
           'metatype': 'ENTRY', 'void_price': 8897.324999999999,
           'trail': False, 'reduce_only': False, 'post_only': False,
           'batch_size': 2, 'status': 'UNFILLED', 'timestamp': None,
           'avg_fill_price': None, 'currency': None, 'venue_id': None},
          {'trade_id': 47, 'position_id': None, 'order_id': 219131,
           'venue': 'BitMEX', 'symbol': 'XBTUSD', 'direction': 'SHORT',
           'size': 334.0, 'price': 9000, 'order_type': 'STOP',
           'metatype': 'STOP', 'void_price': 8897.324999999999,
           'trail': False, 'reduce_only': False, 'post_only': False,
           'batch_size': 2, 'status': 'UNFILLED', 'timestamp': None,
           'avg_fill_price': None, 'currency': None, 'venue_id': None},
          {'trade_id': 47, 'position_id': None, 'order_id': 319131,
           'venue': 'BitMEX', 'symbol': 'XBTUSD', 'direction': 'SHORT',
           'size': 334.0, 'price': 10000.5, 'order_type': 'LIMIT',
           'metatype': 'TAKE_PROFIT', 'void_price': 8897.324999999999,
           'trail': False, 'reduce_only': False, 'post_only': False,
           'batch_size': 2, 'status': 'UNFILLED', 'timestamp': None,
           'avg_fill_price': None, 'currency': None, 'venue_id': None}]


print(place_bulk_orders(orders))
