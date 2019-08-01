import platform
import subprocess
import logging

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s:%(levelname)s:%(module)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)

BASE_URL = "https://www.bitmex.com/"
WS_URL = "wss://www.bitmex.com/realtime"


def ping(host):
    # Ping parameters as function of OS
    ping_str = "-n 1" if platform.system().lower() == "windows" else "-c 1"
    args = "ping " + " " + ping_str + " " + host
    need_sh = False if platform.system().lower() == "windows" else True
    return subprocess.call(args, shell=need_sh) == 0


print(ping(BASE_URL))
