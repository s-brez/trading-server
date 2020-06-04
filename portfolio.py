"""
trading-server is a multi-asset, multi-strategy, event-driven execution
and backtesting platform (OEMS) for trading common markets.

Copyright (C) 2020  Sam Breznikar <sam@sdbgroup.io>

Licensed under GNU General Public License 3.0 or later.

Some rights reserved. See LICENSE.md, AUTHORS.md.
"""

from trade_types import SingleInstrumentTrade, Order, Position, TradeID
from event_types import OrderEvent, FillEvent
from pymongo import MongoClient, errors
import pymongo
import time
import queue


class Portfolio:
    """
    Portfolio manages the net holdings for all models, issuing order events
    and reacting to fill events to open and close positions as strategies
    dictate.

    Capital allocations to strategies and risk parameters are defined here.
    """

    MAX_SIMULTANEOUS_POSITIONS = 20
    MAX_CORRELATED_TRADES = 1
    MAX_ACCEPTED_DRAWDOWN = 15  # Percentage as integer.
    RISK_PER_TRADE = 1          # Percentage as integer OR 'KELLY'
    DEFAULT_STOP = 3            # Default (%) stop distance if none provided.

    def __init__(self, exchanges, logger, db_other, db_client, models):
        self.exchanges = {i.get_name(): i for i in exchanges}
        self.logger = logger
        self.db_other = db_other
        self.db_client = db_client
        self.models = models

        self.id_gen = TradeID(db_other)
        self.pf = self.load_portfolio()
        self.trades_save_to_db = queue.Queue(0)

    def new_signal(self, events, event):
        """
        Interpret incoming signal events to produce Order Events.

        Args:
            events: event queue object.
            event: new market event.

        Returns:
           None.

        Raises:
            None.
        """

        signal = event.get_signal_dict()

        if self.within_risk_limits(signal):

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

                # Take profit order(s).
                if signal['targets']:
                    for target in signal['targets']:
                        tp_size = (size / 100) * target[1]
                        orders.append(Order(
                            self.logger,
                            trade_id,
                            None,
                            signal['symbol'],
                            signal['venue'],
                            event.inverse_direction(),
                            tp_size,
                            target[0],
                            "LIMIT",
                            "TAKE_PROFIT",
                            stop[0],
                            False,
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
                    signal['venue'],            # Venue name.
                    signal['symbol'],           # Instrument ticker code.
                    signal['strategy'],         # Model name.
                    signal['entry_timestamp'],  # Signal timestamp.
                    None,                       # Position object.
                    {str(i.get_order_dict()['order_id']): i.get_order_dict() for i in orders})  # noqa

                # Finalise trade object. Must be called to set ID + order count
                trade.set_batch_size_and_id(trade_id)

                # Queue the trade for DB storage and update portfolio state.
                self.trades_save_to_db.put(trade.get_trade_dict())
                self.pf['trades'][str(trade_id)] = trade.get_trade_dict()
                self.save_porfolio(self.pf)

            # TODO: handle multi-instrument, multi-venue trades.
            elif signal['instrument_count'] == 2:
                pass

            elif signal['instrument_count'] > 2:
                pass

            # Set order batch size and queue orders for execution.
            batch_size = len(orders)
            for order in orders:
                order.batch_size = batch_size
                events.put(OrderEvent(order.get_order_dict()))

            self.logger.debug("Trade " + str(trade_id) + " registered.")

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
        t_id = str(position['trade_id'])

        if fill_conf['metatype'] == "ENTRY":

            # Create a position record and set trade to active.
            self.pf['trades'][t_id]['position'] = position
            self.pf['trades'][t_id]['active'] = True
            self.calculate_pnl(trade_id)

        elif fill_conf['metatype'] == "STOP":

            # Update the now closed postiion, trade is done.
            self.trade_complete(t_id)

        elif fill_conf['metatype'] == "TAKE_PROFIT":

            # Update the modified position.
            direction = self.pf['trades'][t_id]['position']['direction']
            size = self.pf['trades'][t_id]['position']['size']

            # Update position size.
            new_size = size - fill_conf['size']
            self.pf['trades'][t_id]['position']['size'] = new_size
            if new_size == 0:
                self.trade_complete(t_id)
            else:
                self.calculate_pnl(trade_id)

        elif fill_conf['metatype'] == "FINAL_TAKE_PROFIT":

            # Update the now closed postiion, trade is done.
            self.trade_complete(t_id)

        self.save_porfolio(self.pf)

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
            t_id = str(conf['trade_id'])
            o_id = str(conf['order_id'])
            self.pf['trades'][t_id]['orders'][o_id] = conf

            self.logger.debug(str(self.pf['trades'][t_id]['orders'][o_id]))

            # Create a fill event if the order has already been filled.
            if conf['status'] == "FILLED":
                events.put(FillEvent(conf))

        self.save_porfolio(self.pf)

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
        pass

    def trade_complete(self, trade_id):
        """
        Check all orders and positions are closed, calculate pnl, run post
        trade checks/analytics.
        """

        # Cancel all orders marching trade ID.
        self.cancel_orders_by_trade_id(trade_id)

        # Close positions, if still open.
        self.close_positions_by_trade(trade_id)

        # Calculate trade pnl.
        self.calculate_pnl(trade_id)

        # Save portfolio state.
        self.pf['trades'][t_id]['active'] = False
        self.save_porfolio(self.pf)

        # Run post-trade analytics.
        self.post_trade_analysis(trade_id)

    def cancel_orders_by_trade_id(self, trade_id):
        """
        Cancel all orders matching the given trade ID.
        """
        pass

    def close_positions_by_trade(self, trade_id):
        """
        """
        self.pf['trades'][t_id]['position']['size'] = 0

    def calculate_pnl(self, trade_id):
        """
        Calculate pnl for the given trade.
        """
        pass

    def post_trade_analysis(self, trade_id):
        """
        TODO: conduct post-trade analytics.
        """
        pass

    def load_portfolio(self, ID=1):
        """
        Load portfolio matching ID from database or return empty portfolio.
        """

        portfolio = self.db_other['portfolio'].find_one({"id": ID}, {"_id": 0})

        if portfolio:
            self.verify_portfolio_state(portfolio)
            return portfolio

        else:
            default_portfolio = {
                'id': ID,
                'start_date': int(time.time()),
                'initial_funds': 1000,
                'current_value': 1000,
                'current_drawdown': 0,
                'risk_per_trade': self.RISK_PER_TRADE,
                'max_correlated_trades': self.MAX_CORRELATED_TRADES,
                'max_accepted_drawdown': self.MAX_ACCEPTED_DRAWDOWN,
                'max_simultaneous_positions': self.MAX_SIMULTANEOUS_POSITIONS,
                'default_stop': self.DEFAULT_STOP,
                'model_allocations': {  # Equal allocation by default.
                    i.get_name(): (100 / len(self.models)) for i in self.models},
                'trades': {}}

            self.save_porfolio(default_portfolio)

            return default_portfolio

    def verify_portfolio_state(self, portfolio):
        """
        Check stored portfolio data matches actual positions and orders.
        """

        trades = self.db_other['trades'].find({"active": "True"}, {"_id": 0})

        # If trades marked active exist (in DB), check their orders and
        # positions match actual trade state, update portfoilio if disparate.
        if trades:
            self.logger.debug("Verifying trade records match trade state.")
            for venue in [trade['venue'] for trade in trades]:
                print("Fetched positions and orders.")
                positions = self.exchanges[venue].get_positions()
                orders = self.exchanges[venue].get_orders()

                # TODO: state checking.

        self.save_porfolio(portfolio)
        self.logger.debug("Portfolio verification complete.")

        return portfolio

    def save_porfolio(self, portfolio):
        """
        Save portfolio state to DB.
        """

        result = self.db_other['portfolio'].replace_one(
            {"id": portfolio['id']}, portfolio, upsert=True)

        if result.acknowledged:
            self.logger.debug("Portfolio update successful.")
        else:
            self.logger.debug("Portfolio update unsuccessful.")

    def within_risk_limits(self, signal):
        """
        Return true if the new signal would be within risk limits if traded.
        """

        # TODO: Finish after signal > order > fill logic is done.

        return True

    def calculate_exposure(self, trade):
        """
        Calculate the currect capital at risk for the given trade.
        """
        pass

    def correlated(self, instrument):
        """
        Return true if any active trades are correlated with 'instrument'.
        """
        pass

    def calculate_stop_price(self, signal):
        """
        Find the stop price for the given signal.
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
        Find appropriate position size for the given parameters.
        """

        # Fixed percentage per trade risk management.
        if isinstance(self.RISK_PER_TRADE, int):

            account_size = self.pf['current_value']
            risked_amt = (account_size / 100) * self.RISK_PER_TRADE
            position_size = risked_amt // ((stop - entry) / entry)

            return abs(position_size)

        # TOOD: Kelly criteron risk management.
        elif self.RISK_PER_TRADE.upper() == "KELLY":
            pass


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
                    self.logger.debug(
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