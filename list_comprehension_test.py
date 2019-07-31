symbols = ["XBTUSD", "ETHUSD"]
bars = {i: [] for i in symbols}
print(bars)

ticks = [{'price': 10, 'size': 2}, {'price': 15, 'size': 3}]
prices = [i['price'] for i in ticks]
volume = sum(i['size'] for i in ticks)
print(prices)
print(volume)

symbols = ["XBTUSD", "ETHUSD"]
channels = ["trade", "orderBookL2"]


def get_channel_subscription_string():
    prefix = '{"op": "subscribe", "args": ['
    suffix = ']}'
    string = ""
    count = 0
    for symbol in symbols:
        for channel in channels:
            string += '"' + channel + ':' + str(symbol) + '"'
            count += 1
            if count < len(channels) * len(symbols):
                string += ", "
    return prefix + string + suffix


