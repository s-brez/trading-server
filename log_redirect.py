import time


filename = 'log.log'
file = open(filename,'r')

while 1:
    where = file.tell()
    line = file.readline()
    if not line:
        time.sleep(1)
        file.seek(where)
    else:
        print(line)
    time.sleep(0.5)