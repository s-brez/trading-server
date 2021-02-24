from urllib3.exceptions import NewConnectionError, MaxRetryError
from time import sleep
from os import system
import subprocess
import platform

from server import Server

RETRY_TIME = 60

host_os = platform.system()
server = Server()

try:
    server.run()
except (ConnectionError, NewConnectionError, MaxRetryError, TimeoutError):

    # kill all python proccesses, wait and restart
    if host_os == "Windows":
        system('cmd /k "taskkill /IM python.exe /F"')
        print("Server restart in 1 minute.")
        sleep(RETRY_TIME)
        system('cmd /k "python server_test.py"')

    elif host_os == "Linux":
        subprocess.check_output(["pkill" "-9" "python"])
        print("Server restart in 1 minute.")
        sleep(RETRY_TIME)
        subprocess.check_output(["python", "server_test.py"])
