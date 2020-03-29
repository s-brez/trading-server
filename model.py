"""
trading-server is a multi-asset, multi-strategy, event-driven execution
and backtesting platform (OEMS) for trading common markets.

Copyright (C) 2020  Sam Breznikar <sam@sdbgroup.io>

Licensed under GNU General Public License 3.0 or later.

Some rights reserved. See LICENSE.md, AUTHORS.md.
"""

from abc import ABC, abstractmethod
from features import Features as f
from event import SignalEvent
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import numpy as np
import re


class Model(ABC):
    """
    Base class for strategy models.
    """

    def __init__(self):
        super().__init__()

    def get_operating_timeframes(self):
        """
        Return list of operating timeframes.
        """

        return self.operating_timeframes

    def get_lookback(self):
        """
        Return model's required lookback (number of
        previous bars to analyse) for a given timeframe.
        """

        return self.lookback

    def get_features(self):
        """
        Return list of features in use by the model.
        """

        return self.features

    def get_name(self):
        """
        Return model name.
        """

        return self.name

    def get_instruments(self):
        """
        Return dict of instrument amd venues the model is applicable to.
        """

        return self.instruments

    @abstractmethod
    def run(self):
        """
        Run model with given data.
        """

    @abstractmethod
    def get_required_timeframes(self, timeframes, result=False):
        """
        Given a list of operating timeframes, append additional required
        timeframe strings to the list (amend in-place, no new list created).

        To be overwritten in each model.

        Args:
            timeframes: list of current-period operating timeframes.
            result: boolean, if True, return a new list. Othewise append req
                    timeframes to the list passed in (timeframes).

        Returns:
            None.

        Raises:
            None.
        """


class EMACrossTestingOnly(Model):
    """
    For testing use only.

    Rules:
        1. When EMA values cross, enter with market order.

    Supplementary factors (higher probability of success):
        1. N/A

    Entry:
        1. Market entry when rules all

    Stop-loss:
        At previous swing high/low.

    Positon management:
        T1: 1R, close 50% of position. Trade is now risk free.
        T2: Stay in trade until stop-out. As price continues to trend, move
            stop-loss to each new swing high/low.
    """

    name = "EMA Cross Testing-only"

    instruments = {
        "BitMEX": {
            "XBTUSD": "XBTUSD",
            # "ETHUSD": "ETHUSD",
            # "XRPUSD": "XRPUSD",
            },

        "Binance": {

            },

        "FTX": {

            }}

    # Timeframes that the strategy runs on.
    operating_timeframes = [
        "1Min", "5Min", "15Min", "30Min", "1H", "2H", "3H", "4H",
        "6H", "8H", "12H", "16H", "1D", "2D", "3D", "4D", "7D", "14D"]

    # Need to tune each timeframes ideal lookback, 150 default for now.
    lookback = {
        "1Min": 150, "3Min": 150, "5Min": 150, "15Min": 150, "30Min": 150,
        "1H": 150, "2H": 150, "3H": 150, "4H": 150, "6H": 150, "8H": 150,
        "12H": 150, "16H": 150, "1D": 150, "2D": 150, "3D": 150, "4D": 150,
        "7D": 150, "14D": 150}

    # First tuple element in tuple is feature type.
    # Second tuple element is feature function.
    # Third tuple element is feature param.
    features = [
        ("indicator", f.EMA, 10),
        ("indicator", f.EMA, 20)]

    def __init__(self, logger):
        super()

        self.logger = logger

    def run(self, op_data: dict, req_data: list, timeframe: str, symbol: str,
            exchange):
        """
        Run the model with the given data.

        Args:
            None:

        Returns:
            SignalEvent if signal is produced, otherwise None.

        Raises:
            None.

        """

        self.logger.debug(
            "Running " + str(timeframe) + " " + self.get_name() + ".")

        print("Timeframe:", timeframe, " \n", op_data[timeframe])

        if timeframe == "1Min":
            chart = go.Figure(

                # Bars.
                data=[go.Ohlc(
                    x=op_data[timeframe].index,
                    open=op_data[timeframe]['open'],
                    high=op_data[timeframe]['high'],
                    low=op_data[timeframe]['low'],
                    close=op_data[timeframe]['close']),

                    # EMA's.
                    go.Scatter(
                    x=op_data[timeframe].index,
                    y=op_data[timeframe].EMA10,
                    line=dict(color='orange', width=1)),
                    go.Scatter(
                    x=op_data[timeframe].index,
                    y=op_data[timeframe].EMA20,
                    line=dict(color='blue', width=1))])

            title = timeframe + " " + symbol + " " + exchange.get_name()

            chart.update_layout(
                title_text=title,
                title={
                    'y': 0.9,
                    'x': 0.5,
                    'xanchor': 'center',
                    'yanchor': 'top'},
                xaxis_rangeslider_visible=False,
                xaxis_title="Time",
                yaxis_title="Price (USD)")

            chart.show()

        # TODO: model logic

        # if signal:
        #     return SignalEvent(symbol, datetime, direction)
        # else:
        #     return None

        return None

    def get_required_timeframes(self, timeframes: list, result=False):
        """
        No additional (other than current) timeframes required for this model.
        """

        if result:
            return timeframes
        else:
            pass
