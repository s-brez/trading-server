from bitfinex import Bitfinex
from datamanager import Datamanager


class Server:
    """ Server model
        Interacts with all exchange objects and DataHandler to fetch data,
        transform native to non-native trimeframes, andupdate datastores,
        and conduct order management (wip)
    """

    data = Datamanager()

    exchanges = list()
    required_timeframes = list()

    def __init__(self):

        # populate list of all exchange objects
        self.exchanges = self.load_exchanges()

        # load required timeframes from file
        self.required_timeframes = self.load_required_timeframes()

    def build_native_timeframe_datastores(self):
        """ Fetches all historical data for all pairs, all exchanges.
            Required to run only once for initial datastore build.
            Caution - takes many hours.
        """

        timeframes = tuple()

        # iterate through all exchanges, native timeframes and pairs
        for exchange in self.exchanges:
            timeframes = exchange.get_native_timeframes()
            for timeframe in timeframes:
                pairs = exchange.get_all_pairs()
                for pair in pairs:

                    # poll exchange APIs for all historical data
                    # save polled data as CSV
                    self.data.create_new_datastore(
                        pair,
                        exchange.get_name(),
                        timeframe,
                        exchange.get_all_candles(pair, timeframe))

    def build_non_native_timeframe_datastores(self):
        """ Creates missing timeframes from stored data where desired
            timeframes not available natively.
        """

        # iterate through all exchanges, non-native timeframes and pairs
        for exchange in self.exchanges:
            timeframes = exchange.get_non_native_timeframes()
            for target_tf in timeframes:
                pairs = exchange.get_all_pairs()
                for pair in pairs:

                    # resample existing data to target timeframe and
                    # create new datastores from existing saved data
                    self.data.create_new_datastore(
                        pair,
                        exchange.get_name(),
                        target_tf,
                        self.data.resample_data(
                            pair,
                            exchange.get_name(),
                            target_tf))

    def update_datastores(self):
        """ Intended to be run manually intermittently
            during development. To be superceded by smarter
            websocket updating (live tick data stream convert to candles)
        """

        # update native timeframes
        for exchange in self.exchanges:  # iterate through all exchanges
            native_timeframes = exchange.get_native_timeframes()
            for timeframe in native_timeframes:  # & all local timeframes
                pairs = exchange.get_all_pairs()
                for pair in pairs:  # & all pairs
                    self.data.update_existing_datastore(
                        pair,
                        exchange.get_name(),
                        timeframe,
                        exchange.get_new_candles(
                            pair,
                            timeframe,
                            int(
                                self.data.get_last_stored_timestamp(
                                    pair, exchange, timeframe))))
                    self.data.remove_duplicate_entries(
                        pair,
                        exchange.get_name(),
                        timeframe)

        # update non-native timeframes
        for exchange in self.exchanges:
            non_native_timeframes = exchange.get_non_native_timeframes()
            print(non_native_timeframes)
            for timeframe in non_native_timeframes:
                pairs = exchange.get_all_pairs()
                print(pairs)
                for pair in pairs:

                    # resample from native data
                    print("origin data for " + timeframe)
                    df = self.data.resample_data(
                        pair,
                        exchange.get_name(),
                        timeframe)

                    # overwrite existing non_native CSV's
                    df.to_csv(
                        './data/' + exchange.get_name() + '/' + pair +
                        '_' + exchange.get_name() + '_' + timeframe + '.csv')

                    self.data.remove_duplicate_entries(
                        pair,
                        exchange.get_name(),
                        timeframe)

    def load_exchanges(self):
        """ Returns a list of all exchange objects
        """

        # TODO
        # implement a way to dynamically create exchange objects from
        # text file of name strings

        # class_names = []

        # # load data sources (exchanges) from file
        # with open("exchanges.txt", "r") as f:
        #     for line in f:
        #         # list of strings by line
        #         class_names.append(line.strip())

        exchanges = list()

        # NOTE, the below appears to declare the object but not create it

        # # create exchange objects from name list
        # for name in class_names:
        #     exchanges.append(eval(name))

        exchanges.append(Bitfinex())

        return exchanges

    def load_required_timeframes(self):
        """ Returns a list of timeframes required for analysis
            Includes native and non-native timeframes
        """

        timeframes = []

        # load timeframes from file
        with open("required_timeframes.txt", "r") as f:
            for line in f:
                # list of strings by line
                timeframes.append(line.strip())

        return timeframes
