import threading
from cmd import Cmd
# multiprocessing.set_start_method('spawn')


class Shell(Cmd):

    def __init__(self, logger, data, exchanges, strategy, portfolio, broker):
        super(Shell, self).__init__()
        self.prompt = '>_ '
        self.logger = logger
        self.data = data
        self.exchanges = exchanges
        self.strategy = strategy
        self.portfolio = portfolio
        self.broker = broker
        thread = threading.Thread(
            target=lambda: self.start(), daemon=True)
        thread.start()
        self.logger.debug("Started shell daemon.")

    def do_exit(self, input):
        return True

    def do_show(self, input):
        print("Showing '{}'".format(input))

    def start(self):
        self.cmdloop()
