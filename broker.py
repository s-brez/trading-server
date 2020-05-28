"""
trading-server is a multi-asset, multi-strategy, event-driven execution
and backtesting platform (OEMS) for trading common markets.

Copyright (C) 2020  Sam Breznikar <sam@sdbgroup.io>

Licensed under GNU General Public License 3.0 or later.

Some rights reserved. See LICENSE.md, AUTHORS.md.
"""
import traceback


class Broker:
    """
    Broker consumes Order events, executes orders, then creates and places
    Fill events in the main event queue post-transaction.
    """

    def __init__(self, exchanges, logger, db_other, db_client, live_trading):
        self.exchanges = {i.get_name(): i for i in exchanges}
        self.logger = logger
        self.db_other = db_other
        self.db_client = db_client
        self.live_trading = live_trading

        # Container for order batches. {trade_id: [order objects]}
        self.orders = {}

    def new_order(self, events, order_event):
        """
        Process incoming order event, place orders with venues and generate
        a fill event post-execution.

        Args:
            events: event queue object.
            event: new market event.

        Returns:
           None.

        Raises:
            None.
        """

        new_order = order_event.get_order_dict()

        # Store incoming orders under trade ID {trade_id: [orders]}
        try:
            self.orders[new_order['trade_id']].append(new_order)

            to_remove = []

            for trade_id in self.orders.keys():
                order_count = len(self.orders[trade_id])
                venue = self.orders[trade_id][0]['venue']

                # If batch complete, submit order batch for execution.
                if order_count == new_order['batch_size']:

                    self.logger.debug(
                        "Trade " + str(trade_id) + " order batch ready.")

                    print(self.exchanges[venue].place_bulk_orders(
                        self.orders[trade_id]))

                    # Flag orders for removal from self.orders.
                    to_remove.append(trade_id)

            # Remove sent orders after iteration complete.
            for t_id in to_remove:
                del self.orders[t_id]

        except KeyError as ke:
            self.orders[new_order['trade_id']] = [new_order]
            # print(traceback.format_exc())
