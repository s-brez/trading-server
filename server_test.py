from urllib3.exceptions import NewConnectionError, MaxRetryError, TimeoutError
from requests.exceptions import ConnectionError
from server import Server
from time import sleep
from os import kill, getpid
import platform
import logging
import signal
import psutil


TIMEOUT_DURATION = 60

logger = logging.getLogger()
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s:%(levelname)s:%(module)s - %(message)s",
    datefmt="%d-%m-%Y %H:%M:%S")
ch.setFormatter(formatter)
logger.addHandler(ch)


host_os = platform.system()
server = Server(logger)

error_count = 0

while True:

    try:
        logger.info("Starting server.")
        server.run()

    # Stop server, kill all python proccesses except this one, restart server.
    except (ConnectionError, NewConnectionError, MaxRetryError, TimeoutError):

        logger.info("Connection error. Terminating")
        error_count += 1
        server = None

        current_pid = getpid()
        py_pids = [p.pid for p in psutil.process_iter() if "python" in str(p.name)]
        to_kill = [x for x in py_pids if x != current_pid]

        for pid in to_kill:
            kill(pid, signal.SIGTERM)

        sleep(TIMEOUT_DURATION * error_count)
