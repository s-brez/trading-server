import requests

headers = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'Accept': 'application/json',
    'X-Requested-With': 'XMLHttpRequest',
}

data = {
  'symbol': 'XBTUSD',
  'side': 'Buy',
  'orderQty': '1000',
  'price': '8850',
  'stopPx': 'null',
  'clOrdID': 'null',
  'ordType': 'Limit',
  'timeInForce': 'null',
  'execInst': 'null',
  'text': 'null'
}

response = requests.post('https://testnet.bitmex.com/api/v1/order', headers=headers, data=data)
print(response.content)