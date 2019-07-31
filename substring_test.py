class substringtest:

    def __init__(self):
        self.symbols = ("XBTUSD", "ETHUSD")
        self.channels = ("trade", "orderBookL2", "order")

    def get_channel_subscription_string(self):
        prefix = '{"op": "subscribe", "args": ['
        suffix = ']}'
        string = ""
        count = 0
        for symbol in self.symbols:
            for channel in self.channels:
                string += '"' + channel + ':' + str(symbol) + '"'
                count += 1
                if count < len(self.channels) + len(self.symbols):
                    string += ", "
        return prefix + string + suffix


s = substringtest()
print(s.get_channel_subscription_string())
print('{"op": "subscribe", "args": ["trade:XBTUSD", "orderBookL2:XBTUSD", "trade:ETHUSD", "orderBookL2:ETHUSD"]}')
