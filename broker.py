"""
trading-server is a multi-asset, multi-strategy, event-driven execution
and backtesting platform (OEMS) for trading common markets.

Copyright (C) 2020  Sam Breznikar <sam@sdbgroup.io>

Licensed under GNU General Public License 3.0 or later.

Some rights reserved. See LICENSE.md, AUTHORS.md.
"""

from messaging_clients import Telegram
from event_types import FillEvent
from threading import Thread
from time import sleep
import traceback
import datetime
import json
import sys


class Broker:
    """
    Broker consumes Order events, executes orders, then creates and places
    Fill events in the main event queue post-transaction.
    """

    def __init__(self, exchanges, logger, portfolio, db_other, db_client,
                 live_trading):
        self.exchanges = {i.get_name(): i for i in exchanges}
        self.logger = logger
        self.pf = portfolio
        self.db_other = db_other
        self.db_client = db_client
        self.live_trading = live_trading
        self.tg = Telegram(logger, portfolio)

        # Container for order batches {trade_id: [order objects]}.
        self.orders = {}

        # Start FillAgent.
        self.fill_agent = FillAgent(self.logger, self.pf, self.exchanges)

    def new_order(self, events, order_event):
        """
        Process incoming order events and place orders with venues.

        Create fill notifications as order fill confirmations are received.

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

                    for order in self.orders[trade_id]:
                        print(json.dumps(order))

                    # TODO: Get trade confirmation from user.

                    # Place orders.
                    order_confs = self.exchanges[venue].place_bulk_orders(
                        self.orders[trade_id])

                    # Update portfolio state with order placement details.
                    if order_confs:
                        self.pf.new_order_conf(order_confs, events)

                    # Flag sent orders for removal from self.orders.
                    to_remove.append(trade_id)

            # Remove sent orders after iteration complete.
            for t_id in to_remove:
                del self.orders[t_id]

        except KeyError as ke:
            self.orders[new_order['trade_id']] = [new_order]
            # print(traceback.format_exc())

    def check_fills(self, events):
        """
        Check orders have been filled by comparing portfolio and venue order
        states. Create fill events when orders have been filled.
        """

        if self.fill_agent.fills:
            for fill_event in self.fill_agent.fills:
                events.put(fill_event)

            self.fill_agent.fills = []

        return events


class FillAgent:
    """
    Check for new fills in separate thread on specified intervals/conditions.
    """

    # Check for fills on the (60 - CHECK_INTERVAL)th second of each minute.
    CHECK_INTERVAL = 25

    def __init__(self, logger, portfolio, exchanges):
        self.logger = logger
        self.pf = portfolio.load_portfolio()
        self.exchanges = exchanges

        self.fills = []

        thread = Thread(target=lambda: self.start(portfolio), daemon=True)
        thread.start()

        self.logger.debug("Started FillAgent.")

    def start(self, portfolio):
        """
        """

        sleep(self.seconds_til_next_minute())

        while True:
            sleep(60 - self.CHECK_INTERVAL)

            self.pf = portfolio.load_portfolio()

            # Get snapshot of orders saved locally.
            active_venues = set()
            portfolio_order_snapshot = []
            for t_id in self.pf['trades'].keys():
                if self.pf['trades'][t_id]['active']:

                    active_venues.add(self.pf['trades'][t_id]['venue'])

                    for o_id in self.pf['trades'][t_id]['orders'].keys():
                        portfolio_order_snapshot.append((
                            # (v_id, o_id, status, venue name)
                            self.pf['trades'][t_id]['orders'][o_id][
                                'venue_id'],
                            o_id,
                            self.pf['trades'][t_id]['orders'][o_id]['status'],
                            self.pf['trades'][t_id]['orders'][o_id]['venue']))

            # Get orders from all venues with active trades.
            orders = []
            for venue in list(active_venues):
                orders = orders + self.exchanges[venue].get_orders()

            # Snapshot actual order state.
            actual_order_snapshot = []
            for order in portfolio_order_snapshot:
                for conf in orders:
                    if conf['venue_id'] == order[0]:
                        actual_order_snapshot.append((
                            conf['venue_id'],
                            conf['order_id'],
                            conf['status'],
                            conf))

            # print("Portfolio:", portfolio_order_snapshot)
            # print("Actual:", actual_order_snapshot)

            # Compare actual order state to local portfolio state.
            for port, actual in zip(
                    portfolio_order_snapshot, actual_order_snapshot):
                if port[0] == actual[0]:
                    if port[2] != actual[2]:

                        # Order has been filled or cancelled.
                        if (
                            actual[2] == "FILLED" or actual[2] == "PARTIAL"
                                or actual[2] == "CANCELLED"):

                            # Derive the trade ID from order id.
                            fill_conf = actual[3]
                            fill_conf['trade_id'] = actual[1].partition("-")[0]

                            # Store the new fill event.
                            self.fills.append(FillEvent(fill_conf))

                        else:
                            # Something wrong with code if status is wrong.
                            raise Exception(
                                "Order status code error:", actual[2])

                else:
                    # Something critically wrong if theres a missing venue ID.
                    raise Exception("Order ID mistmatch. Portfolio v_id:",
                                    port[0], "Actual v_id:", actual[0])

            # Wait til next minute elapses.
            sleep(self.seconds_til_next_minute())

    def seconds_til_next_minute(self):
        now = datetime.datetime.utcnow().second
        delay = 60 - now
        return delay
