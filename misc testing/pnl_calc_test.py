from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from requests import Request, Session
from requests.auth import AuthBase
from urllib.parse import urlparse
from datetime import datetime
from dateutil import parser

import json
import hmac
import hashlib
import time
 

REQUEST_TIMEOUT = 10

api_key = ""
api_secret = ""

BASE_URL = "https://www.bitmex.com/api/v1"
BASE_URL_TESTNET = "https://testnet.bitmex.com/api/v1"
ORDERS_URL = "/order"
TRADE_HIST_URL = "/execution/tradeHistory"

retries = Retry(
    total=5,
    backoff_factor=0.25,
    status_forcelist=[502, 503, 504],
    method_whitelist=False)
session = Session()
session.mount('https://', HTTPAdapter(max_retries=retries))

demo_trade = {
    "trade_id": 1,
    "signal_timestamp": 1613627160,
    "type": "SINGLE_INSTRUMENT",
    "active": False,
    "venue_count": 1,
    "instrument_count": 1,
    "model": "EMA Cross - Testing only",
    "direction": "SHORT",
    "timeframe": "1Min",
    "entry_price": 52288.0,
    "u_pnl": 0,
    "r_pnl": 0,
    "fees": 0,
    "exposure": None,
    "venue": "BitMEX",
    "symbol": "XBTUSD",
    "position": None,
    "order_count": 2,
    "orders": {
        "1-1": {
            "trade_id": 1,
            "order_id": "1-1",
            "timestamp": None,
            "avg_fill_price": None,
            "currency": None,
            "venue_id": None,
            "venue": "BitMEX",
            "symbol": "XBTUSD",
            "direction": "SHORT",
            "size": 49.0,
            "price": 52288.0,
            "order_type": "MARKET",
            "metatype": "ENTRY",
            "void_price": 53333.76,
            "trail": False,
            "reduce_only": False,
            "post_only": False,
            "batch_size": 0,
            "status": "UNFILLED"
        },
        "1-2": {
            "trade_id": 1,
            "order_id": "1-2",
            "timestamp": None,
            "avg_fill_price": None,
            "currency": None,
            "venue_id": None,
            "venue": "BitMEX",
            "symbol": "XBTUSD",
            "direction": "LONG",
            "size": 49.0,
            "price": 53333.76,
            "order_type": "STOP",
            "metatype": "STOP",
            "void_price": None,
            "trail": False,
            "reduce_only": True,
            "post_only": False,
            "batch_size": 0,
            "status": "UNFILLED"
        }
    },
    "consent": True
}


def generate_request_signature(secret, request_type, url, nonce,
                               data):
    """
    Generate BitMEX-compatible authenticated request signature header.

    Args:
        secret: API secret key.
        request_type: Request type (GET, POST, etc).
        url: full request url.
        validity: seconds request will be valid for after creation.
    Returns:
        signature: hex(HMAC_SHA256(apiSecret, verb + path + expires + data)
    Raises:
        None.
    """

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
    """
    Add BitMEX-compatible authentication headers to a request object.

    Args:
        api_key: API key.
        api_secret: API secret key.
        request: Request object to be amended.
    Returns:
        request: Modified request object.
    Raises:
        None.
    """

    nonce = str(int(round(time.time()) + REQUEST_TIMEOUT))
    request.headers['api-expires'] = nonce
    request.headers['api-key'] = api_key
    request.headers['api-signature'] = generate_request_signature(
        api_secret, request.method, request.url, nonce, request.body or '')  # noqa
    request.headers['Content-Type'] = 'application/json'
    request.headers['Accept'] = 'application/json'
    request.headers['X-Requested-With'] = 'XMLHttpRequest'

    return request


def get_executions(symbol, start_timestamp=None, end_timestamp=None, count=500):

    # Convert epoch ts's to utc human-readable
    start = str(datetime.utcfromtimestamp(start_timestamp)) if start_timestamp else None
    end = str(datetime.utcfromtimestamp(end_timestamp)) if end_timestamp else None

    payload = {
        'symbol': symbol,
        'count': count,
        'startTime': start,
        'endTime': end,
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

    response = session.send(request).json()

    executions = []

    for res in response:

        fee_type = "TAKER" if res['lastLiquidityInd'] == "RemovedLiquidity" else "MAKER"
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

        executions.append({
                'order_id': res['clOrdID'],
                'venue_id': res['orderID'],
                'timestamp': int(parser.parse(res['timestamp']).timestamp()),
                'avg_exc_price': res['avgPx'],
                'currency': res['currency'],
                'symbol': res['symbol'],
                'direction': direction,
                'size': res['lastQty'],
                'order_type': order_type,
                'fee_type': fee_type,
                'fee_amt': res['commission'],
                'total_fee': res['lastQty'] * res['commission'],
                'status': fill})

    return executions


def calculate_pnl_by_trade(trade_id):

    trade = demo_trade
    t_id = str(trade_id)

    # Get order executions for trade in period from trade signal to now.
    execs = get_executions(trade['symbol'], trade['signal_timestamp'], int(datetime.now().timestamp()))

    # Handle two-order trades. Single exit, single entry.
    if len(trade['orders']) == 2:
        entry_oid = trade['orders'][t_id + "-1"]['order_id']
        exit_oid = trade['orders'][t_id + "-2"]['order_id']

    # TODO: Handle trade types with more than 2 orders
    elif len(trade['orders']) >= 3:
        entry_oid = None
        exit_oid = None
        # tp_oids = []

    # Entry executions will match direction of trade and bear the entry order id.
    entries = [i for i in execs if i['direction'] == trade['direction'] and i['order_id'] == entry_oid]

    # API-submitted exit executions should be the reverse
    exits = [i for i in execs if i['direction'] != trade['direction'] and i['order_id'] == exit_oid]
    manual_exit = False

    # Exit orders placed manually wont bear the order id and cant be evaluated with certainty
    # if there were multiple trades with executions in the same period as the current trade.
    # If manual exit, notify user if the exit total is differnt to entry total.
    if not exits:
        exits = [i for i in execs if i['direction'] != trade['direction']]
        manual_exit = True

    if entries and exits:
        avg_entry = sum(i['avg_exc_price'] for i in entries) / len(entries)
        avg_exit = (sum(i['avg_exc_price'] for i in exits) / len(exits)) + 5000
        fees = sum(i['total_fee'] for i in (entries + exits))
        percent_change = abs((avg_entry - avg_exit) / avg_entry) * 100
        abs_pnl = abs((trade['orders'][t_id + "-1"]['size'] / 100) * percent_change) - fees
        if trade['direction'] == "LONG":
            final_pnl = abs_pnl if avg_exit > avg_entry + fees else -abs_pnl

        elif trade['direction'] == "SHORT":
            final_pnl = abs_pnl if avg_exit < avg_entry - fees else -abs_pnl

        print(avg_entry, avg_exit)
        print(percent_change)
        print(final_pnl)

    # No matching entry or exit executions exist
    else:
        pass


calculate_pnl_by_trade(1)
