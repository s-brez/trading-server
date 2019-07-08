import time
import datetime
from datetime import timezone


timestamp = datetime.datetime.utcnow()
# timestamp = int(round(time.time() * 1000))
# timestamp = datetime.datetime.fromtimestamp(timestamp // 1000)



print(timestamp)
print(timestamp.hour)
print(timestamp.minute)

