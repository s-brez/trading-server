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
                 live_trading, telegram):
        self.exchanges = {i.get_name(): i for i in exchanges}
        self.logger = logger
        self.pf = portfolio
        self.db_other = db_other
        self.db_client = db_client
        self.live_trading = live_trading
        self.tg = telegram

        # Container for order batches {trade_id: [order objects]}.
        self.orders = {}

        # Start FillAgent if in live operation
        if live_trading:
            self.fill_agent = FillAgent(self.logger, self.pf, self.exchanges)
        else:
            self.fill_agent = None

    def new_order(self, events, order_event):
        """
        Process and store incoming order events.

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

        except KeyError:
            self.orders[new_order['trade_id']] = [new_order]
            # traceback.print_exc()

    def check_consent(self, events):
        """
        Place orders if all orders present and user accepts pending trades.

        Args:
            events: event queue object.

        Returns:
           None.

        Raises:
            None.
        """

        if self.orders.keys():

            to_remove = []

            for trade_id in self.orders.keys():

                # Action user responses from telegram, if any
                self.register_telegram_responses(trade_id)

                # Get stored trade state from DB
                trade = dict(self.db_other['trades'].find_one({"trade_id": trade_id}, {"_id": 0}))

                # Count received orders for that trade
                order_count = len(self.orders[trade_id])
                venue = self.orders[trade_id][0]['venue']

                # User has accepted the trade.
                if trade['consent'] is True:
                    if order_count == trade['order_count']:
                        self.logger.info(
                            "Trade " + str(trade_id) + " order batch ready.")

                        # Place orders.
                        order_confs = self.exchanges[venue].place_bulk_orders(
                            self.orders[trade_id])

                        # Update portfolio state with order placement details.
                        if order_confs:
                            self.pf.new_order_conf(order_confs, events)
                            self.logger.info("Orders for trade " + str(trade_id) + " submitted to venue.")

                        else:
                            self.logger.info("Order submission for " + str(trade_id) + " may have failed or only partially succeeded.")
                            # raise Exception("Caution: manual order and position check required for trade " + str(trade_id) + ".")

                        to_remove.append(trade_id)

                    else:
                        self.logger.info("Order batch for trade " + str(trade_id) + " not yet ready.")

                # User has not yet made a decision.
                elif trade['consent'] is None:
                    self.logger.info("Trade " + str(trade_id) + " awaiting user review.")

                # User has rejected the trade.
                elif trade['consent'] is False:
                    self.pf.trade_complete(trade_id)
                    to_remove.append(trade_id)

                # Unkown consent case
                else:
                    raise Exception("Unknown case for trade consent:", trade['consent'])

            # Remove sent orders after iteration complete.
            for t_id in to_remove:
                del self.orders[t_id]

        else:
            pass
            self.logger.info("No trades awaiting review.")

    def check_overdue_trades(self):
        """
        Check for trades that have not been accepted by user and dont have pending orders with Broker.
        This may occur if system crashes and resumes before user accepts or vetos pending trades.

        Args:
            None

        Returns:
           None.

        Raises:
            None.
        """
        pass

    def register_telegram_responses(self, trade_id):
        """
        Check telegram messages to determine acceptance/veto of trade.

        Update DB to reflect users choice.

        Args:
            trade_id: id of trade to check for

        Returns:
           None.

        Raises:
            None.
        """

        for response in self.tg.get_updates():

            u_id = None
            msg_type = None
            t_id = str(trade_id)

            # Message field may be 'message' or 'edited_message'
            try:
                u_id = str(response['message']['from']['id'])
                msg_type = 'message'
            except KeyError:
                u_id = str(response['edited_message']['from']['id'])
                msg_type = 'edited_message'

            # Response must have came from a whitelisted account.
            try:
                if u_id in self.tg.whitelist:

                    # Response ID must match trade ID.
                    if str(response[msg_type]['text'][:len(t_id)]) == t_id:

                        # Response timestamp must be greater than signal trigger time.
                        trade_ts = self.db_other['trades'].find_one({"trade_id": trade_id})['signal_timestamp']
                        response_ts = response[msg_type]['date']
                        if response_ts > trade_ts:

                            try:
                                decision = response[msg_type]['text'].split(" - ", 1)
                                if decision[1] == "Accept":
                                    self.db_other['trades'].update_one({"trade_id": trade_id}, {"$set": {"consent": True}})
                                    self.pf.pf['trades'][t_id]['consent'] = True

                                elif decision[1] == "Veto":
                                    self.db_other['trades'].update_one({"trade_id": trade_id}, {"$set": {"consent": False}})
                                    self.pf.pf['trades'][t_id]['consent'] = False

                                else:
                                    self.logger.info("Unknown input received as response to trade " + t_id + " consent message: " + decision[1])

                            except Exception:
                                traceback.print_exc()

            # Unexpected response format in updates
            except Exception:
                traceback.print_exc()
                print(json.dumps(response))

    def check_fills(self, events):
        """
        Check orders have been filled by comparing portfolio and venue order
        states. Create fill events when orders have been filled.
        """

        if self.fill_agent.fills:
            for fill_event in self.fill_agent.fills:
                events.put(fill_event)

            self.fill_agent.fills = []
            self.logger.info("Parsing order fill messages.")

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

        self.logger.info("Started FillAgent.")

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
                    raise Exception("Order ID mistmatch. \nPortfolio v_id:",
                                    port[0], "Actual v_id:", actual[0])

            # Wait til next minute elapses.
            sleep(self.seconds_til_next_minute())

    def seconds_til_next_minute(self):
        now = datetime.datetime.utcnow().second
        delay = 60 - now
        return delay
