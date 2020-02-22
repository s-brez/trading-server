import threading
from cmd import Cmd
# multiprocessing.set_start_method('spawn')


class Shell(Cmd):

    def __init__(self, version, logger, data, exc, strat, port, broker):
        super(Shell, self).__init__()
        self.prompt = '$_ '
        self.intro = 'trading-server v.' + version + '.'
        self.logger = logger
        self.data = data
        self.exchanges = exc
        self.strategy = strat
        self.portfolio = port
        self.broker = broker
        thread = threading.Thread(
            target=lambda: self.start(), daemon=True)
        thread.start()
        self.logger.debug("Started shell daemon.")

    def do_exit(self, inp):
        return True

    def do_show(self, inp):

        params = inp.split()

        try:
            # Single parameter cases
            if len(params) == 1:

                # Instrument summary
                if params[0] == 'instruments' or params[0] == 'inst':
                    print(
                        self.data.get_total_instruments(),
                        "monitored instruments.")
                    for i in self.data.get_instrument_symbols():
                        print(i)

                # Data summary
                if params[0] == 'data':
                    for e in self.exchanges:
                        for s in e.get_symbols():
                            for t in self.strategy.PREVIEW_TIMEFRAMES:
                                print(e.get_name(), s, t + ":")
                                print(self.strategy.data[e.get_name()][s][t].head(5), "\n")
        except Exception:
            print("Invalid entry.")
            self.do_show(inp)

    def start(self):
        self.cmdloop()
