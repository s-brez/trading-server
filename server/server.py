from datamanager import Datamanager
from exchanges import *
import traceback


class Server():
    """ Server model
        Interacts with all exchange objects and DataHandler to fetch data,
        update datastores, and conduct order management
        
    """

    data = Datamanager()

    exchanges = list()
    required_timeframes = list()

    def __init__(self):

        # populate list of all exchange objects
        self.exchanges = load_exchanges()

        # load required timeframes from file
        self.required_timeframes = load_required_timeframes()

    def build_native_timeframe_datastores():
        """ Fetches all historical data for all pairs, all exchanges.
            Required to run only once for initial datastore build.
            Caution - takes many hours.
        """

        # iterate through all exchanges, native timeframes and pairs
        for exchange in exchanges:
            timeframes = exchange.get_native_timeframes()
            for timeframe in timeframes:
                pairs = exchange.get_all_pairs()
                for pair in pairs:

                    # poll exchange REST APIs for all historical data
                    # save polled data as CSVs
                    data.create_new_datastore(
                        pair,
                        exchange.get_name(),
                        timeframe,
                        exchange.get_all_candles(pair, timeframe))

    def build_non_native_timeframe_datastores():
        """ Creates missing timeframes from stored data where desired
            timeframes not available natively.
        """

        # iterate through all exchanges, non-native timeframes and pairs
        for exchange in exchanges:
            timeframes = exchange.get_non_native_timeframes()
            for target_tf in timeframes:
                pairs = exchange.get_all_pairs()
                for pair in pairs:

                    # resample existing data to target timeframe and
                    # create new datastores from existing saved data
                    data.create_new_datastore(
                        pair,
                        exchange.get_name(),
                        target_tf,
                        data.resample_data(
                            pair,
                            exchange.get_name(),
                            target_tf))

    def update_datastores():
        """ Intended to be run manually intermittently
            during development. To be superceded by smarter
            websocket updating (live tick data stream convert to candles)
        """

        # update native timeframes
        for exchange in exchanges:  # iterate through all exchanges
            native_timeframes = exchange.get_native_timeframes()
            for timeframe in native_timeframes:  # & all local timeframes
                pairs = exchange.get_all_pairs()
                for pair in pairs:  # & all pairs
                    data.update_existing_datastore(
                        pair,
                        exchange.get_name(),
                        timeframe,
                        exchange.get_new_candles(
                            pair,
                            timeframe,
                            int(data.get_last_stored_timestamp(
                                pair, timeframe))))
                    data.remove_duplicate_entries(
                        pair,
                        exchange.get_name(),
                        timeframe)

        # update non-native timeframes
        for exchange in exchanges:
            non_native_timeframes = exchange.get_non_native_timeframes()
            print(non_native_timeframes)
            for timeframe in non_native_timeframes:
                pairs = exchange.get_all_pairs()
                print(pairs)
                for pair in pairs:

                    # resample from the native data just updated
                    print("origin data for " + timeframe)
                    df = data.resample_data(
                        pair,
                        exchange.get_name(),
                        timeframe)

                    # overwrite existing non_native CSV's
                    df.to_csv(
                        './data/' + exchange.get_name() + '/' + pair +
                        '_' + exchange.get_name() + '_' + timeframe + '.csv')

                    data.remove_duplicate_entries(
                        pair,
                        exchange.get_name(),
                        timeframe)

    def load_exchanges():
        """ Returns a list of all exchange objects
        """

        # load list of desired exchanges from file
        with open("exchanges.txt", "r") as f:
            names = f.read()

    def load_required_timeframes():



    """ Current tasks
        1. Build all Bitfinex datastores
        2. Add websocket update capability to Bitfinex
        3. Create "Exchange" interface
        4. Bitfinex to inherit "Exchange" interface
        5. Create baseline Bitmex class to further test Exchange interface
        6. Move completed exchange classes to a library
    """
