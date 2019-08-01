
from bitmex import Bitmex
import logging
from data import Datahandler
import queue
from time import sleep


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s:%(levelname)s:%(module)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)

# bitmex = Bitmex(logger)

events = queue.Queue(0)
exchanges = [Bitmex(logger)]
data = Datahandler(exchanges, events, logger)
print(data.get_timeframes())
while True:
    sleep(100)

# MAX_BARS_PER_REQUEST = 750
# BASE_URL = "https://www.bitmex.com/api/v1"
# BARS_URL = "/trade/bucketed?binSize="
# TIMESTAMP_FORMAT = '%Y-%m-%d%H:%M:%S.%f'


# def previous_minute():
#     timestamp = datetime.datetime.utcnow() - datetime.timedelta(minutes=1)
#     timestamp.replace(second=0, microsecond=0)
#     return timestamp


"""
Fetch bar buckets via REST polling, then parse to dataframe
"""

# timeframe = "1h"
# symbol = "XBT"
# bucket_size = 10

# payload = "{}{}{}&symbol={}&filter=&count={}&start=&reverse=true".format(
#     BASE_URL, BARS_URL, timeframe, symbol, bucket_size)

# response = requests.get(payload).json()

# df = pd.DataFrame(response)
# df = df[['timestamp', 'open', 'high', 'low', 'close']]

# modified_dates = []
# for i in df['timestamp']:
#     new_datestring = ""
#     for char in i:
#         if not(char.isalpha()):
#             new_datestring += char
#     modified_dates.append(new_datestring)

# df.timestamp = modified_dates
# print(df)
