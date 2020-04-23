from requests.auth import AuthBase
from urllib.parse import urlparse
from pymongo import MongoClient
from datetime import datetime
import pandas as pd
import requests
import hashlib
import hmac
import time
import os


db_client = MongoClient('mongodb://127.0.0.1:27017/')
db_other = db_client['holdings_trades_signals_master']
coll = db_other['signals']
# coll = db_other['trades']
# coll = db_other['portfolio']


def generate_request_signature(secret, request_type, url, nonce, data):
    """
    Generate BitMEX-compatible authenticated request signature header.

    Args:
        secret: API secret key.
        request_type: Request type (GET, POST, etc).
        url: full request url.
        validity: seconds request will be valid for after creation.
    Returns:
        signature: hex(HMAC_SHA256(apiSecret, verb + path + expires + data))
    Raises:
        None.
    """

    parsed_url = urlparse(url)
    path = parsed_url.path

    if parsed_url.query:
        path = path + '?' + parsed_url.query

    if isinstance(data, (bytes, bytearray)):
        data = data.decode('utf8')

    message = request_type.upper() + path + str(nonce) + data
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

    nonce = str(int(round(time.time()) + 5))
    request.headers['api-expires'] = nonce
    request.headers['api-key'] = api_key
    request.headers['api-signature'] = generate_request_signature(
        api_secret, request.method, request.url, nonce, request.body or '')

    return request

