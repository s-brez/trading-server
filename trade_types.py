"""
trading-server is a multi-asset, multi-strategy, event-driven trade execution
and backtesting platform (OEMS) for trading common markets.

Copyright (C) 2020  Sam Breznikar <sam@sdbgroup.io>

Licensed under GNU General Public License 3.0 or later.

Some rights reserved. See LICENSE.md, AUTHORS.md.
"""

from abc import ABC, abstractmethod


class Trade(ABC):
    """
    Trade parent class, different types of trade subclasses must inherit this.

    Trade subclasses are used to generalise a collective set of orders and
    positions that make up a trades management from start to finish.

    Child trade classes may be composed of positons and orders across one or
    multiple instruments and venues.
    """

    def __init__(self):
        self.trade_id = None            # Must be set before saving to DB.
        self.order_count = 0            # Number of component orders.
        self.signal_timestamp = None    # Epoch timestamp of parent signal.
        self.active = False             # True/False.
        self.venue_count = 0            # Number of venues in use.
        self.instrument_count = 0       # Number of instruments in use.
        self.model = None               # Name of model that triggered trade.
        self.u_pnl = 0                  # Total unrealised pnl.
        self.r_pnl = 0                  # Total realised pnl.
        self.fees = 0                   # Total fees/commisions paid.
        self.exposure = None            # Percentage of capital at risk.
        self.consent = None             # If or not user consents to trade.
        self.systematic_close = None    # If or not trade was closed properly.

    @abstractmethod
    def get_trade_dict(self):
        """
        Return all trade variables as a dict for DB storage.
        """

    def set_batch_size_and_id(self, trade_id):
        """
        Must be called after trade object has been prepared.
        Sets the trade ID and order count, and assigns unique ID's to orders.
        """

        self.order_count = len(self.orders)
        self.trade_id = trade_id


class SingleInstrumentTrade(Trade):
    """
    Models the state of a single-instrument, single venue trade.

    Used when trading a single instrument directionally, with take profit
    and stop loss orders.
    """

    def __init__(self, logger, direction, venue, symbol, model, s_ts=None,
                 timeframe=None, entry_price=None, position=None, orders=None):
        super().__init__()
        self.logger = logger
        self.type = "SINGLE_INSTRUMENT"
        self.venue_count = 1
        self.instrument_count = 1
        self.direction = direction          # LONG or SHORT.
        self.signal_timestamp = s_ts        # Epoch timestamp of parent signal.
        self.timeframe = timeframe          # Trade timeframe.
        self.entry_price = entry_price      # Trade entry price.
        self.exit_price = None              # Trade exit price.
        self.venue = venue                  # Exchange or broker traded with.
        self.symbol = symbol                # Instrument ticker code.
        self.model = model                  # Name of triggerstrategy.
        self.position = position            # Position object, if positioned.
        self.orders = orders                # Dict of component orders.

    def get_trade_dict(self):
        return {
            'trade_id': self.trade_id,
            'signal_timestamp': self.signal_timestamp,
            'type': self.type,
            'active': self.active,
            'venue_count': self.venue_count,
            'instrument_count': self.instrument_count,
            'model': self.model,
            'direction': self.direction,
            'timeframe': self.timeframe,
            'entry_price': self.entry_price,
            'exit_price': self.entry_price,
            'systematic_close': self.systematic_close,
            'u_pnl': self.u_pnl,
            'r_pnl': self.r_pnl,
            'fees': self.fees,
            'exposure': self.exposure,
            'venue': self.venue,
            'symbol': self.symbol,
            'position': self.position,
            'consent': self.consent,
            'order_count': self.order_count,
            'orders': self.orders}


class Position:
    """
    Models a single active position, as part of a parent trade.
    """

    def __init__(self, fill_conf):
        self.fill_conf = fill_conf

        # TODO
        self.fees = None

    def __str__(self):
        return str(" ")

    def get_fill_conf(self):
        return self.fill_conf

    def get_pos_dict(self):
        return {
            'trade_id': self.fill_conf['trade_id'],
            'size': self.fill_conf['size'],
            'avg_entry_price': self.fill_conf['avg_fill_price'],
            'symbol': self.fill_conf['symbol'],
            'direction': self.fill_conf['direction'],
            'currency': self.fill_conf['currency'],
            'opening_timestamp': self.fill_conf['timestamp'],
            'opening_size': self.fill_conf['size'],
            'status': "OPEN"}


class Order:
    """
    Models a single order, as part of parent trade.
    """

    def __init__(self, logger, trade_id, order_id, symbol, venue,
                 direction, size, price, order_type, metatype, void_price,
                 trail, reduce_only, post_only, status="UNFILLED"):
        self.logger = logger
        self.trade_id = trade_id        # Parent trade ID.
        self.order_id = None            # Internal use order ID.
        self.timestamp = None           # Order placement timestamp.
        self.avg_fill_price = None      # Actual fill price
        self.currency = None            # Instrument denomination currency.
        self.venue_id = None            # Order ID as used by venue.
        self.symbol = symbol            # Instrument ticker code.
        self.venue = venue              # Venue or exchange traded at.
        self.direction = direction.upper()    # LONG, SHORT.
        self.size = size                # Size in local asset/contract.
        self.price = price              # Order price.
        self.order_type = order_type.upper()  # LIMIT MARKET STOP_LIMIT STOP.
        self.metatype = metatype.upper()      # ENTRY, STOP, TAKE_PROFIT, FINAL_TAKE_PROFIT.
        self.void_price = void_price    # Order invalidation price.
        self.trail = trail              # True or False, only for stops.
        self.reduce_only = reduce_only  # True or False.
        self.post_only = post_only      # True of False.
        self.batch_size = 0             # Batch size for all related orders.
        self.status = status            # FILLED, NEW, PARTIAL.

    def get_order_dict(self):
        """
        Return all order variables as a dict for DB storage.
        """
        return {
            'trade_id': self.trade_id,
            'order_id': self.order_id,
            'timestamp': self.timestamp,
            'avg_fill_price': self.avg_fill_price,
            'currency': self.currency,
            'venue_id': self.venue_id,
            'venue': self.venue,
            'symbol': self.symbol,
            'direction': self.direction,
            'size': self.size,
            'price': self.price,
            'order_type': self.order_type,
            'metatype': self.metatype,
            'void_price': self.void_price,
            'trail': self.trail,
            'reduce_only': self.reduce_only,
            'post_only': self.post_only,
            'batch_size': self.batch_size,
            'status': self.status}


class TradeID():
    """
    Utility class for generating sequential trade ID's from database.
    """

    def __init__(self, db):
        self.db = db

    def new_id(self):
        result = list(self.db['trades'].find({}).sort([("trade_id", -1)]))
        return (int(result[0]['trade_id']) + 1) if result else 1
