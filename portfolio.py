"""
trading-server is a multi-asset, multi-strategy, event-driven execution
and backtesting platform (OEMS) for trading common markets.

Copyright (C) 2020  Sam Breznikar <sam@sdbgroup.io>

Licensed under GNU General Public License 3.0 or later.

Some rights reserved. See LICENSE.md, AUTHORS.md.
"""

from trade_types import SingleInstrumentTrade, Order, Position, TradeID
from event_types import OrderEvent, FillEvent

from datetime import datetime
import numpy as np
import traceback

import matplotlib
matplotlib.use('qt5agg')

import mplfinance as mpl
import pymongo
import queue
import time
import json
import sys
import os


class Portfolio:
    """
    Portfolio manages the net holdings for all models, issuing order events
    and reacting to fill events to open and close positions as strategies
    dictate.

    Capital allocations to strategies and risk parameters are defined here.
    """

    MAX_SIMULTANEOUS_POSITIONS = 20
    MAX_CORRELATED_POSITIONS = 4
    CORRELATION_THRESHOLD = 0.5     # Level at which instrument considered correlated (-1 to 1)
    MAX_ACCEPTED_DRAWDOWN = 25      # Percentage as integer.
    RISK_PER_TRADE = 0.5              # Percentage as integer or float OR 'KELLY'
    SNAPSHOT_SIZE = 100             # Lookback period for trade snapshot images
    DEFAULT_STOP = 1                # Default (%) stop distance if none provided.
    DEFAULT_START = 1000            # Default portfolio size if none given.  

    def __init__(self, exchanges, logger, db_other, db_client, models,
                 telegram, live_trading):
        self.exchanges = {i.get_name(): i for i in exchanges}
        self.live_trading = live_trading
        self.logger = logger
        self.db_other = db_other
        self.db_client = db_client
        self.models = models
        self.telegram = telegram
        self.broker = None

        self.trades_save_to_db = queue.Queue(0)
        self.id_gen = TradeID(db_other)
        self.pf = self.load_portfolio()
        self.verify_portfolio_state(self.pf)

    def new_signal(self, events, event):
        """
        Convert incoming Signal events to Order events.

        Args:
            events: event queue object.
            event: new market event.

        Returns:
           None.

        Raises:
            None.
        """

        signal = event.get_signal_dict()
        orders = []

        # Generate sequential trade ID for new trade.
        trade_id = self.id_gen.new_id()

        # Handle single-instrument signals:
        if signal['instrument_count'] == 1:

            stop = self.calculate_stop_price(signal),
            size = self.calculate_position_size(stop[0],
                                                signal['entry_price'])
            # Entry order.
            orders.append(Order(
                self.logger,
                trade_id,               # Parent trade ID.
                None,                   # Order ID as used by venue.
                signal['symbol'],       # Instrument ticker code.
                signal['venue'],        # Venue name.
                signal['direction'],    # LONG or SHORT.
                size,                   # Size in native denomination.
                signal['entry_price'],  # Order price.
                signal['entry_type'],   # LIMIT MARKET STOP_LIMIT/MARKET.
                "ENTRY",                # ENTRY, TAKE_PROFIT, STOP.
                stop[0],                # Order invalidation price.
                False,                  # Trail.
                False,                  # Reduce-only order.
                False))                 # Post-only order.


            # Take profit order(s).
            if signal['targets']:

                count = 1
                for target in signal['targets']:

                    # Label final TP order as "FINAL_TAKE_PROFIT".
                    tp_type = "TAKE_PROFIT" if count != len(signal['targets']) else "FINAL_TAKE_PROFIT"
                    count += 1

                    orders.append(Order(
                        self.logger,
                        trade_id,
                        None,
                        signal['symbol'],
                        signal['venue'],
                        event.inverse_direction(),
                        (size / 100) * target[1],
                        target[0],
                        "LIMIT",
                        tp_type,
                        stop[0],
                        False,
                        True,
                        False))

            # Stop order.
            orders.append(Order(
                self.logger,
                trade_id,
                None,
                signal['symbol'],
                signal['venue'],
                event.inverse_direction(),
                size,
                stop[0],
                "STOP",
                "STOP",
                None,
                signal['trail'],
                True,
                False))

            # Set sequential order ID's, based on trade ID.
            count = 1
            for order in orders:
                order.order_id = str(trade_id) + "-" + str(count)
                count += 1

            # Parent trade object:
            trade = SingleInstrumentTrade(
                self.logger,
                signal['direction'],        # Direction
                signal['venue'],            # Venue name.
                signal['symbol'],           # Instrument ticker code.
                signal['strategy'],         # Model name.
                signal['entry_timestamp'],  # Signal timestamp.
                signal['timeframe'],        # Signal timeframe.
                signal['entry_price'],       # Entry price.
                None,                       # Position object.
                {str(i.get_order_dict()['order_id']): i.get_order_dict() for i in orders})  # noqa

            # Finalise trade object. Must be called to set ID + order count
            trade.set_batch_size_and_id(trade_id)

            # Queue the trade for storage.
            self.trades_save_to_db.put(trade.get_trade_dict())

            # Store trade immediately
            self.save_new_trades_to_db()

            # Set order batch size and queue orders for execution.
            batch_size = len(orders)
            for order in orders:
                order.batch_size = batch_size

            within_risk_limits, msg = self.within_risk_limits(signal)

            # Generate static image of trade setup.
            t_dict = trade.get_trade_dict()
            self.generate_trade_setup_image(
                t_dict, signal['op_data'], within_risk_limits, msg)

            # Only raise orders and add to portfilio if within risk limits.
            if within_risk_limits:
                self.pf['trades'][str(trade_id)] = t_dict
                self.save_portfolio(self.pf)
                for order in orders:
                    events.put(OrderEvent(order.get_order_dict()))

        # TODO: handle multi-instrument, multi-venue trades.
        elif signal['instrument_count'] == 2:
            pass

        elif signal['instrument_count'] > 2:
            pass

        self.logger.info("Trade " + str(trade_id) + " registered.")

    def new_fill(self, fill_event):
        """
        Process incoming fill event, update position, trade and order state
        accordingly.

        Args:
            events: event queue object.
            event: new market event.

        Returns:
           None.

        Raises:
            None.
        """

        fill_conf = fill_event.get_order_conf()
        position = Position(fill_conf).get_pos_dict()
        trade_id = str(position['trade_id'])

        if fill_conf['metatype'] == "ENTRY":

            # Create a position record and set trade to active.
            self.pf['trades'][trade_id]['position'] = position
            self.pf['trades'][trade_id]['active'] = True
            self.pf['trades'][trade_id]['exposure'] = 100
            self.pf['trades'][trade_id]['entry_price'] = position['avg_entry_price']
            self.pf['total_active_trades'] += 1

        elif fill_conf['metatype'] == "STOP":

            # Update the now closed postiion, trade is done.
            size = self.pf['trades'][trade_id]['position']['size']
            new_size = size - fill_conf['size']

            # Should be 0
            if new_size > 0:
                raise Exception(new_size)
            # Can be negative if user modifies positions manually
            elif new_size < 0:
                new_size = 0

            self.pf['trades'][trade_id]['position']['size'] = new_size
            self.pf['trades'][trade_id]['position']['status'] = "CLOSED"
            self.pf['trades'][trade_id]['exposure'] = 0

            # If ther order was cancelled there will not be 

            self.trade_complete(trade_id)

        elif fill_conf['metatype'] == "TAKE_PROFIT":

            # Update the modified position.
            size = self.pf['trades'][trade_id]['position']['size']
            new_size = size - fill_conf['size']
            self.pf['trades'][trade_id]['position']['size'] = new_size

            # TODO: Find adjusted exposure
            # what % of the position has been closed vs starting size
            # self.pf['trades'][trade_id]['exposure'] = ?

            if new_size == 0:
                self.trade_complete(trade_id)
            else:
                self.calculate_pnl_by_trade(trade_id, take_profit=True)

        elif fill_conf['metatype'] == "FINAL_TAKE_PROFIT":

            # Update the now closed postiion, trade is done.
            size = self.pf['trades'][trade_id]['position']['size']
            new_size = size - fill_conf['size']
            self.pf['trades'][trade_id]['position']['size'] = new_size
            self.pf['trades'][trade_id]['position']['status'] = "CLOSED"
            self.pf['trades'][trade_id]['exposure'] = 0

            if new_size != 0:
                raise Exception(
                    "Position close size error:", new_size)

            self.trade_complete(trade_id)

        else:
            raise Exception("Order metatype error:", fill_conf['metatype'])

        self.save_portfolio(self.pf)

    def new_order_conf(self, order_confs: list, events):
        """
        Update stored trade and order state to match given order confirmations.

        Args:
            order_confs: list of order dicts containing updated details.
            events:  event queue object.
        Returns:
           None.

        Raises:
            None.
        """

        # Update portfolio state.
        for conf in order_confs:
            trade_id = str(conf['trade_id'])
            o_id = str(conf['order_id'])
            self.pf['trades'][trade_id]['orders'][o_id] = conf

            # Create a fill event if order already filled (e.g. market orders).
            if conf['status'] == "FILLED":
                events.put(FillEvent(conf))

        self.save_portfolio(self.pf)

    def trade_complete(self, trade_id):
        """
        Check all orders and positions are closed, calculate pnl, run post
        trade checks/analytics.
        """

        self.cancel_orders_by_trade_id(trade_id)

        # Close positions if still open.
        if self.check_position_open(trade_id):
            self.close_position_by_trade_id(trade_id)

        # Only update portfolio metrics if trade was accepted by user.
        if self.pf['trades'][trade_id]['consent'] != "SUPERCEEDED" and self.pf['trades'][trade_id]['consent'] is not None:
            self.calculate_pnl_by_trade(trade_id)
            self.post_trade_analysis(trade_id)

        # Reduce active trade count by 1.
        if self.pf['total_active_trades'] > 0:
            self.pf['total_active_trades'] -= 1 

        # Mark trade as inactive
        self.pf['trades'][trade_id]['active'] = False

        # Save updated portfolio state to DB.
        self.save_portfolio(self.pf, output=False)

        # Update trades DB to reflect portfolio state.
        self.update_trades_db(trade_id)

    def cancel_orders_by_trade_id(self, trade_id):
        """
        Cancel all orders matching the given trade ID and update
        local portfolio state.
        """

        t_id = str(trade_id)

        o_ids = list(self.pf['trades'][t_id]['orders'].keys())
        v_ids = [
            self.pf['trades'][t_id]['orders'][o]['venue_id'] for o in o_ids if
            self.pf['trades'][t_id]['orders'][o]['status'] != "FILLED"]

        venue = self.pf['trades'][t_id]['venue']

        cancel_confs = self.exchanges[venue].cancel_orders(v_ids)

        if cancel_confs:
            for v_id in v_ids:

                # Cancellation/fill cases
                try:
                    if cancel_confs[v_id]['venue_id'] in v_ids:
                        if cancel_confs[v_id]['status'] == "CANCELLED" or cancel_confs[v_id]['status'] == "FILLED":
                            self.pf['trades'][t_id]['active'] = False
                            for o in o_ids:
                                # print("Setting new order status:", o, cancel_confs[v_id]['status'])
                                self.pf['trades'][t_id]['orders'][o]['status'] == cancel_confs[v_id]['status']

                            if cancel_confs[v_id]['order_type'] == 'Stop':
                                self.pf['trades'][t_id]['exit_price'] = cancel_confs[v_id]['price']

                        else:
                            print(json.dumps(cancel_confs[v_id], indent=2))
                            raise Exception("Unexpected response format.")

                # Error cases
                except KeyError:
                    try: 
                        if cancel_confs[v_id] == "NOT FOUND":
                            
                            self.logger.warning("Not found error needs to be handled here.")
                            # TODO

                        else:
                            print(json.dumps(cancel_confs[v_id], indent=2))
                            raise Exception("Unexpected response format.")

                    except KeyError:
                        print(json.dumps(cancel_confs[v_id], indent=2))
                        raise Exception("Unexpected response format.")


            # Set price from trade records for cancelled or not foundorders
            # price = self.db_other['trades'].find_one(
            #     {"trade_id": int(trade_id)}, {"_id": 0})['orders'][order_id]['price']

            # self.pf['trades'][trade_id]['orders'][order_id][
            #     'price'] = price

        # No active cancellations or order state modification ocurred
        else:
            pass

    def check_position_open(self, trade_id):
        """
        Return true if position is still open according to local portfolio.
        """

        t_id = str(trade_id)

        if self.pf['trades'][t_id]['position'] is None:
            return False
        elif self.pf['trades'][t_id]['position']['status'] == "OPEN":
            return True
        elif self.pf['trades'][t_id]['position']['status'] == "CLOSED":
            return False
        else:
            raise Exception(
                "Position status error:",
                self.pf['trades'][t_id]['position']['status'])

    def close_position_by_trade_id(self, trade_id):
        """
        This method will close only the remaining amount for the given trade -
        it will not necessarily close an entire position, unless there is only
        one open position in that particular instrument.

        Then, update local portfolio state.

        Use close_position_absolute() to completely close all positions in
        for specifc instrument at a specific venue.
        """

        close = self.exchanges[
            self.pf['trades'][trade_id]['venue']].close_position(
                self.pf['trades'][trade_id]['symbol'],
                self.pf['trades'][trade_id]['position']['size'],
                self.pf['trades'][trade_id]['direction'])

        if close:
            self.pf['trades'][trade_id]['position']['size'] = 0
            self.pf['trades'][trade_id]['position']['status'] = "CLOSED"

    def close_position_absolute(self, venue, symbol):
        """
        Close ALL units of given instrument symbol indiscriminately.
        """

        return self.exchanges[venue].close_position(symbol)

    def calculate_pnl_by_trade(self, trade_id, take_profit=False):
        """
        Calculate pnl for the given trade and update portfolio state.
        """

        trade = self.pf['trades'][trade_id]

        # Get order executions in period from trade signal to current time.
        execs = self.exchanges[trade['venue']].get_executions(
            trade['symbol'],
            trade['signal_timestamp'],
            int(datetime.now().timestamp()))

        total_orders = len(trade['orders'])

        # Two-order trades (Entry and stop).
        if total_orders == 2:
            entry_oid = trade['orders'][trade_id + "-1"]['order_id']
            stop_oid = trade['orders'][trade_id + "-2"]['order_id']

        # 3 or more order trades (Entry, tp(s) and stop).
        elif total_orders >= 3:
            entry_oid = trade['orders'][trade_id + "-1"]['order_id']
            tp_oids = []
            for i in range(2, total_orders - 1):
                tp_oids.append(
                    trade['orders'][trade_id + "-" + str(i)]['order_id'])
            stop_oid = trade['orders'][trade_id + "-" + str(total_orders - 1)]['order_id']

        # Entry executions will match direction of trade and bear the entry order id.
        entries = [i for i in execs if i['direction'] == trade['direction'] and i['order_id'] == entry_oid]

        # API-submitted exit executions should be the reverse
        stops = [i for i in execs if i['direction'] != trade['direction'] and i['order_id'] == stop_oid]
        tps = [i for i in execs if i['direction'] != trade['direction'] and i['order_id'] in tp_oids]
        manual_exit = False

        print("entry_oid", entry_oid)
        print("tps:", tps)
        print("tp_oids", tp_oids)
        if stop_oid:
            print("exit_oid", stop_oid)
        if stops:
            print("stops:", stops)

        # Exit orders placed manually wont bear the order id and cant be evaluated with certainty
        # if there were multiple trades with executions in the same period as the current trade.
        # If manual exit, notify user if the exit total is differnt to entry total.
        if not stops and not tps:
            stops = [i for i in execs if i['direction'] != trade['direction']]
            manual_exit = True

        avg_entry = np.average([i['avg_exc_price'] for i in entries], weights=[i['size'] for i in entries])
        
        # Final pnl figures for 2 order trades and manual exits
        if entries and stops and not tps:
            avg_exit = np.average([i['avg_exc_price'] for i in stops], weights=[i['size'] for i in stops])
            fees = sum(i['total_fee'] for i in (entries + stops))

        # Final pnl for 3+ order trades.
        elif total_orders >= 3 and ((entries and stops) or (entries and tps)):
            avg_exit = np.average([i['avg_exc_price'] for i in stops + tps], weights=[i['size'] for i in stops + tps])
            fees = sum(i['total_fee'] for i in (entries + stops + tps))

        else:
            raise Exception("No entry or exit executions found for trade " + trade_id + ".")

        percent_change = abs((avg_entry - avg_exit) / avg_entry) * 100
        abs_pnl = abs((trade['orders'][trade_id + "-1"]['size'] / 100) * percent_change) - fees

        if trade['direction'] == "LONG":
            final_pnl = abs_pnl if avg_exit > avg_entry + fees else -abs_pnl

        elif trade['direction'] == "SHORT":
            final_pnl = abs_pnl if avg_exit < avg_entry - fees else -abs_pnl

        # Log trade stats
        self.pf['current_balance'] += final_pnl
        self.pf['balance_history'][str(int(time.time()))] = {
            'amt': final_pnl,
            'trade_id': trade_id}
        self.pf['trades'][trade_id]['u_pnl'] = 0
        self.pf['trades'][trade_id]['r_pnl'] = final_pnl
        self.pf['trades'][trade_id]['fees'] = fees
        self.pf['trades'][trade_id]['exposure'] = None
        self.pf['trades'][trade_id]['exit_price'] = avg_exit
        self.pf['trades'][trade_id]['systematic_close'] = False if manual_exit else True

        if final_pnl > 0:
            self.pf['total_winning_trades'] += 1
        elif final_pnl < 0:
            self.pf['total_losing_trades'] += 1

        self.logger.info("Trade " + trade_id + " returned " + str(final_pnl) + " USD.")

        if manual_exit:
            self.logger.warning("Non-systematic postion closure detected for trade " + trade_id + ". Manually verify final pnl figures for this trade and that all orders are closed. Avoid closing positions or cancelling orders manually.")            

    def post_trade_analysis(self, trade_id):
        """
        Conduct post-trade portfolio analytics.
        """

        # 'total_trades'
        self.pf['total_trades'] += 1

        # 'peak_balance'
        # 'low_balance'
        if self.pf['current_balance'] > self.pf['peak_balance']:
            self.pf['peak_balance'] = self.pf['current_balance']
            self.logger.info("New portfolio value all-time-high: " + str(self.pf['current_balance']))
        elif self.pf['current_balance'] < self.pf['low_balance']:
            self.pf['low_balance'] = self.pf['current_balance']
            self.logger.info("New portfolio value all-time-low: " + str(self.pf['current_balance']))        

        balance_history = [i for i in list(self.pf['balance_history'].values())[1:]]

        print(len(balance_history))
        print(json.dumps(balance_history, indent=2))
        if len(balance_history) > 1:


            # 'total_consecutive_wins'
            # 'total_consecutive_losses'
            if balance_history[-1]['amt'] > 0 and balance_history[-2]['amt'] > 0:
                self.pf['total_consecutive_wins'] += 1
            elif balance_history[-1]['amt'] < 0 and balance_history[-2]['amt'] < 0:
                self.pf['total_consecutive_losses'] += 1

            # 'avg_r_per_trade'
            # 'avg_r_per_winner'
            # 'avg_r_per_loser'
            winners_r, losers_r, total_r = [], [], []
            for transaction in balance_history:
                trade = self.pf['trades'][transaction['trade_id']]
                entry = trade['position']['avg_entry_price']
                stop = list(trade['orders'].values())[-1]['price']
                exit = trade["exit_price"]
                rr = (exit - entry) / (entry - stop)
                total_r.append(rr)

                if transaction['amt'] > 0:
                    winners_r.append(rr)

                elif transaction['amt'] < 0:
                    losers_r.append(rr)

            self.pf['avg_r_per_trade'] = round(sum(total_r) / len(total_r), 4)

            if winners_r:
                self.pf['avg_r_per_winner'] = round(sum(winners_r) / len(winners_r), 4)

            if losers_r:
                self.pf['avg_r_per_loser'] = round(sum(losers_r) / len(losers_r), 4)

            # 'win_loss_ratio'
            if self.pf['total_winning_trades'] and self.pf['total_losing_trades']:
                self.pf['win_loss_ratio'] = self.pf['total_winning_trades'] / self.pf['total_losing_trades']
            elif self.pf['total_winning_trades'] and not self.pf['total_losing_trades']:
                self.pf['win_loss_ratio'] = self.pf['total_winning_trades']

    def verify_portfolio_state(self, portfolio):
        """
        Check stored portfolio data matches actual positions and orders.
        """

        # TODO.

        self.save_portfolio(portfolio)
        self.logger.info("Portfolio verification complete.")

    def load_portfolio(self, ID=1):
        """
        Load portfolio matching ID from database or return empty portfolio.
        """

        portfolio = self.db_other['portfolio'].find_one({"id": ID}, {"_id": 0})

        if portfolio:
            return portfolio

        else:
            default_portfolio = {
                'id': ID,
                'balance_history': {
                    str(int(time.time())): {
                        'amt': self.DEFAULT_START,
                        'trade_id': "initial_deposit"}},
                'current_balance': self.DEFAULT_START,
                'starting_balance': self.DEFAULT_START,
                'peak_balance': self.DEFAULT_START,
                'low_balance': self.DEFAULT_START,
                'total_active_trades': 0,
                'total_trades': 0,
                'total_winning_trades': 0,
                'total_losing_trades': 0,
                'total_consecutive_wins': 0,
                'total_consecutive_losses': 0,
                'avg_r_per_winner': 0,
                'avg_r_per_loser': 0,
                'avg_r_per_trade': 0,
                'win_loss_ratio': 0,
                'default_stop': self.DEFAULT_STOP,
                'risk_per_trade': self.RISK_PER_TRADE,
                'max_simultaneous_positions': self.MAX_SIMULTANEOUS_POSITIONS,
                'max_correlated_positions': self.MAX_CORRELATED_POSITIONS,
                'max_accepted_drawdown': self.MAX_ACCEPTED_DRAWDOWN,
                'model_allocations': {  # Equal allocation by default.
                    i.get_name(): (100 / len(self.models)) for i in self.models},
                'trades': {}}

            return default_portfolio

    def save_portfolio(self, portfolio, output=True):
        """
        Save portfolio state to DB.
        """

        result = self.db_other['portfolio'].replace_one(
            {"id": portfolio['id']}, portfolio, upsert=True)

        if result.acknowledged and output:
            self.logger.info("Portfolio save successful.")

        else:
            self.logger.info("Portfolio save unsuccessful.")

    def within_risk_limits(self, signal):
        """
        Return true if signal would not exceed risk limits or cause conflicts when traded.
        """

        # Position limit check.
        if self.pf['total_active_trades'] < self.pf['max_simultaneous_positions']:

            # Drawdown check.
            if self.pf['current_balance'] >= (100 - self.pf['max_accepted_drawdown']) * (self.pf['starting_balance'] / 100):

                # Correlation check.
                if not self.correlated(signal):

                    # Same-asset, same-venue trade conflict checks.
                    trades = [t for t in self.pf['trades'].values()]
                    conflicted_active_trades = [t for t in trades if t['active'] and t['symbol'] == signal['symbol'] and t['venue'] == signal['venue']]
                    conflicted_pending_trades = [t for t in trades if not t['active'] and not t['position'] and t['consent'] != "SUPERCEEDED" and t['symbol'] == signal['symbol'] and t['venue'] == signal['venue']]

                    if conflicted_active_trades:

                        all_trades_risk_off = True
                        for trade in conflicted_active_trades:

                            # If all conflicted trades are risk free and same direction as signal, proceed with signal
                            if trade['exposure'] and trade['direction'] == signal['direction']:
                                all_trades_risk_off = False

                            # If signal opposite direction to trade, notify user but take no action.
                            elif trade['direction'] != signal['direction']:
                                self.logger.info("New signal is opposite direction to existing position.")
                                return False, "New signal is opposite direction to existing position. Check for a possible reversal."

                        if all_trades_risk_off:

                            # Check if signal should superceeds any pending signals.
                            if (signal['symbol'], signal['venue']) not in [(t['symbol'], t['venue']) for t in conflicted_pending_trades]:
                                self.logger.info("Existing position is risk-free. Adding to existing position.")
                                return True, "New trade within risk limits. Compound existing position."

                            # New signal conflicts with older pending signal(s),
                            else:
                                self.superceed_older_signals(signal, conflicted_pending_trades)
                                return True, "New trade within risk limits."
                        else:
                            self.logger.info("Existing position matching new signal is not risk-free.")
                            return False, "An existing position matching new signal is not risk-free."

                    # Check if signal should superceeds any pending signals.
                    else:
                        if (signal['symbol'], signal['venue']) not in [(t['symbol'], t['venue']) for t in conflicted_pending_trades]:
                            # All risk checks cleared, free to action signal as is.
                            self.logger.info("New trade within all risk limits.")
                            return True, "New trade within risk limits."

                        # New signal conflicts with older pending signal(s)
                        else:
                            self.superceed_older_signals(signal, conflicted_pending_trades)
                            return True, "New trade within risk limits."
                else:
                    self.logger.info(
                        "New trade skipped. Correlated position limit reached.")
                    return False, "Correlated position limit reached."
            else:
                self.logger.info("New trade skipped. Drawdown limit reached.")
                return False, "Drawdown limit reached."
        else:
            self.logger.info("New trade skipped. Position limit reached.")
            return False, "Position limit reached."

    def superceed_older_signals(self, signal, conflicted_pending_trades: list):
        """
        Remove pending, unactioned trades that conflict with the given signal.
        """

        for trade in conflicted_pending_trades:

            t_id = str(trade['trade_id'])

            if trade['signal_timestamp'] < signal['entry_timestamp']:

                try:

                    self.pf['trades'][t_id]['consent'] = "SUPERCEEDED"

                    del self.broker.orders[trade['trade_id']]
                    self.trade_complete(t_id)
                    self.logger.info("New signal superceeds a pending trade. Trade " + t_id + " cancelled.")

                except:
                    traceback.print_exc()
                    print("orders:", type(self.broker.orders))
                    print(json.dumps(self.broker.orders, indent=2))

                    print("conflicted trade")
                    print(json.dumps(trade, indent=2))

                    print("conflicted_pending_trades")
                    print(json.dumps(conflicted_pending_trades, indent=2))

                    sys.exit(0)

    def calculate_exposure(self, trade):
        """
        Calculate the currect capital at risk for the given trade.
        """

        # TODO.

    def correlated(self, signal):
        """
        Return true if any active trades would be correlated with trades
        produced by the incoming signal.
        """

        # TODO

        return False

    def calculate_stop_price(self, signal):
        """
        Find stop price for the given signal.
        """

        if signal['stop_price'] is not None:
            return signal['stop_price']

        else:
            if signal['direction'] == "LONG":
                return signal['entry_price'] / 100 * (100 - self.DEFAULT_STOP)

            elif signal['direction'] == "SHORT":
                return signal['entry_price'] / 100 * (100 + self.DEFAULT_STOP)

    def calculate_position_size(self, stop, entry):
        """
        Find appropriate position size according to portfolio risk parameters
        """

        # Fixed percentage per trade risk management.
        if isinstance(self.RISK_PER_TRADE, int) or isinstance(self.RISK_PER_TRADE, float):

            account_size = self.pf['current_balance']
            risked_amt = (account_size / 1000) * self.RISK_PER_TRADE
            position_size = risked_amt // ((stop - entry) / entry)

            return abs(position_size)

        # TOOD: Kelly criteron risk management.
        elif self.RISK_PER_TRADE.upper() == "KELLY":
            pass

        else:
            raise Exception("RISK_PER_TRADE must be an integer or 'KELLY': " + self.RISK_PER_TRADE)

    def update_price(self, events, market_event):
        """
        Check price and time updates against existing positions.

        Args:
            events: event queue object.
            event: new market event.

        Returns:
           None.

        Raises:
            None.
        """

        # TODO.

    def update_trades_db(self, trade_id):
        """
        Update trade DB to reflect trade state of local portfolio
        """

    def save_new_trades_to_db(self):
        """
        Save trades in save-later queue to database.

        Args:
            None.
        Returns:
            None.
        Raises:
            pymongo.errors.DuplicateKeyError.
        """

        count = 0
        while True:

            try:
                trade = self.trades_save_to_db.get(False)

            except queue.Empty:
                if count:
                    self.logger.info(
                        "Wrote " + str(count) + " new trades to database " +
                        str(self.db_other.name) + ".")
                break

            else:
                if trade is not None:
                    count += 1
                    # Store signal in relevant db collection.
                    try:
                        self.db_other['trades'].insert_one(trade)
                    # Skip duplicates if they exist.
                    except pymongo.errors.DuplicateKeyError:
                        continue

                self.trades_save_to_db.task_done()

    def generate_trade_setup_image(self, trade, op_data, within_risk_limits: bool, msg: str):
        """
        Create a snapshot image of trade setup and send to user.
        """

        self.logger.info("Creating signal snapshot image")

        # Create image directory if it doesnt exist
        if not os.path.exists("setup_images"):
            os.mkdir("setup_images")

        # Dump trade data to file for ease of testing next stage
        # Remove from production
        # op_data.to_csv('op_data.csv')
        # with open('trade.json', 'w') as outfile:
        #     json.dump(trade, outfile)

        # Reformat dataframe for mplfinance compatibility
        df = op_data.copy(deep=True)
        df.rename(
            {'open': 'Open', 'high': 'High', 'low': 'Low',
             'close': 'Close', 'volume': 'Volume'}, axis=1,
            inplace=True)
        df = df.tail(self.SNAPSHOT_SIZE)


        # TODO: trim the columns that arent needed for this particular model.
        # e.g testing strategy doesnt need MACD.

        # Get markers for trades triggered by the current bar
        entry_marker = [np.nan for i in range(self.SNAPSHOT_SIZE)]
        entry_marker[-1] = trade['entry_price']
        stop = None
        stop_marker = [np.nan for i in range(self.SNAPSHOT_SIZE)]
        for order in trade['orders'].values():
            if order['order_type'] == "STOP":
                stop = order['price']
                stop_marker[-1] = stop

        # TODO: Trades triggered by interaction with historic bars

        # Create plot figures
        adp, hlines = self.create_addplots(df, mpl, stop, entry_marker,
                                           stop_marker)
        mc = mpl.make_marketcolors(up='w', down='black', wick="w", edge='w')
        style = mpl.make_mpf_style(gridstyle='', base_mpf_style='nightclouds',
                                   marketcolors=mc)
        filename = "setup_images/" + str(trade['trade_id']) + "_" + str(trade['signal_timestamp']) + '_' + trade['model'] + "_" + trade['timeframe']

        try:
            plot = mpl.plot(df, type='candle', addplot=adp, style=style, hlines=hlines,
                            title="\n" + trade['model'] + " - " + trade['timeframe'],
                            datetime_format='%d-%m %H:%M', figscale=1, savefig=filename,
                            tight_layout=False)

        except ValueError:
            traceback.print_exc()
            print(df)
            print(df['Open'])
            sys.exit(0)

        message = "Trade " + str(trade['trade_id']) + " - " + trade['model'] + " " + trade['timeframe'] + "\n\nEntry: " + str(trade['entry_price']) + " \nStop: " + str(stop) + "\n"
        options = [[str(trade['trade_id']) + " - Accept", str(trade['trade_id']) + " - Veto"]]

        try:
            self.telegram.send_image(filename + ".png", message)
            if within_risk_limits is True:
                self.telegram.send_option_keyboard(options)
            else:
                self.telegram.send_message("Trade would exceed risk limits. " + msg)

        except Exception as ex:
            self.logger.info("Failed to send setup image via telegram.")
            print(ex)
            traceback.print_exc()

    def create_addplots(self, df, mpl, stop, entry_marker, stop_marker):
        """
        Helper method for generate_trade_setup_image.
        Formats plot artifacts for mplfinance.
        """

        adps, hlines = [], {'hlines': [], 'colors': [], 'linestyle': '--',
                            'linewidths': 0.5}

        # Add technical feature data (indicator values, etc).
        for col in list(df):
            if (
                col != "Open" and col != "High" and col != "Low"
                    and col != "Close" and col != "Volume"):
                adps.append(mpl.make_addplot(df[col]))

        # Add entry marker
        adps.append(mpl.make_addplot(
            entry_marker, type='scatter', markersize=500, marker="_",
            color='limegreen'))

        # Add stop marker
        if stop:
            adps.append(mpl.make_addplot(
                stop_marker, type='scatter', markersize=500, marker='_',
                color='crimson'))

        return adps, hlines
