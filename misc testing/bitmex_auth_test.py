from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from requests import Request, Session
from requests.auth import AuthBase
from urllib.parse import urlparse

import hmac
import hashlib
import time


REQUEST_TIMEOUT = 10

api_key = ""
api_secret = ""

BASE_URL = "https://www.bitmex.com/api/v1"
BASE_URL_TESTNET = "https://testnet.bitmex.com/api/v1"
ORDERS_URL = "/order"


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


payload = {
    'symbol': "ETHUSD",
    'side': 'Buy',
    'orderQty': 10,
    'price': None,
    'stopPx': None,
    'clOrdID': None,
    'ordType': 'Market',
    'timeInForce': 'ImmediateOrCancel',
    'execInst': None,
    'text': None}

prepared_request = Request(
    'POST',
    BASE_URL_TESTNET + ORDERS_URL,
    json=payload,
    params='').prepare()

request = generate_request_headers(
    prepared_request,
    api_key,
    api_secret)

retries = Retry(
    total=5,
    backoff_factor=0.25,
    status_forcelist=[502, 503, 504],
    method_whitelist=False)
session = Session()
session.mount('https://', HTTPAdapter(max_retries=retries))

response = session.send(request)

print(response, response.text)
