from dateutil import parser
from dateutil.tz import gettz
from datetime import datetime, timezone


bar = {"timestamp":"2020-02-07T12:42:00.000Z","symbol":"XBTUSD","open":9754.5,"high":9754.5,"low":9748,"close":9748,"trades":944,"volume":5269528,"vwap":9749.4394,"lastSize":17287,"turnover":54049961870,"homeNotional":540.4996187,"foreignNotional":5269528}

final_datetime = parser.parse(bar['timestamp'])
final_timestamp = final_datetime.replace(tzinfo=timezone.utc).timestamp()

print(final_timestamp)

print((final_datetime - datetime(1970, 1, 1, tzinfo=timezone.utc)).total_seconds())