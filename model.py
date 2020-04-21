"""
trading-server is a multi-asset, multi-strategy, event-driven execution
and backtesting platform (OEMS) for trading common markets.

Copyright (C) 2020  Sam Breznikar <sam@sdbgroup.io>

Licensed under GNU General Public License 3.0 or later.

Some rights reserved. See LICENSE.md, AUTHORS.md.
"""

from abc import ABC, abstractmethod
from features import Features as f
from event_types import SignalEvent
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

    Entry:
        Market entry when EMA's cross

    Stop-loss:
        None.

    Take-profit:
        Close trade and re-open in opposite direction on opposing signal.
    """

    name = "EMA Cross - Testing only"

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

    # Timeframes the strategy runs on.
    operating_timeframes = [
        "1Min"]

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

        if timeframe in self.operating_timeframes:

            features = list(zip(
                op_data[timeframe].index, op_data[timeframe]['open'],
                op_data[timeframe].EMA10, op_data[timeframe].EMA20))

            longs = {'price': [], 'time': []}
            shorts = {'price': [], 'time': []}

            # Check for EMA crosses.
            for i in range(len(op_data[timeframe].index)):
                fast = features[i][2]
                slow = features[i][3]
                fast_minus_1 = features[i - 1][2]
                slow_minus_1 = features[i - 1][3]
                fast_minus_2 = features[i - 2][2]
                slow_minus_2 = features[i - 2][3]

                if fast is not None and slow is not None:

                    # Short cross
                    if slow > fast:
                        if slow_minus_1 < fast_minus_1 and slow_minus_2 < fast_minus_2:
                            shorts['price'].append(features[i][1])
                            shorts['time'].append(features[i][0])

                    # Long cross
                    elif slow < fast:
                        if slow_minus_1 > fast_minus_1 and slow_minus_2 > fast_minus_2:
                            longs['price'].append(features[i][1])
                            longs['time'].append(features[i][0])

            if longs or shorts:

                signal = False

                # Generate trade signal if current bar has an entry.
                if features[-1][0] == longs['time'][-1]:
                    direction = "long"
                    entry_price = longs['price'][-1]
                    entry_ts = longs['time'][-1]
                    signal = True

                elif features[-1][0] == shorts['time'][-1]:
                    direction = "short"
                    entry_price = shorts['price'][-1]
                    entry_ts = shorts['time'][-1]
                    signal = True

                if signal:

                    # Plot the signal.
                    chart = go.Figure(
                        data=[

                            # Bars.
                            go.Ohlc(
                                x=op_data[timeframe].index,
                                open=op_data[timeframe]['open'],
                                high=op_data[timeframe]['high'],
                                low=op_data[timeframe]['low'],
                                close=op_data[timeframe]['close'],
                                name="Bars",
                                increasing_line_color='black',
                                decreasing_line_color='black'),

                            # EMA10.
                            go.Scatter(
                                x=op_data[timeframe].index,
                                y=op_data[timeframe].EMA10,
                                line=dict(color='gray', width=1),
                                name="EMA10"),

                            # EMA20.
                            go.Scatter(
                                x=op_data[timeframe].index,
                                y=op_data[timeframe].EMA20,
                                line=dict(color='black', width=1),
                                name="EMA20"),

                            # Longs.
                            go.Scatter(
                                x=longs['time'],
                                y=longs['price'],
                                mode='markers',
                                name="Long",
                                marker_color="green",
                                marker_size=10),

                            # Shorts.
                            go.Scatter(
                                x=shorts['time'],
                                y=shorts['price'],
                                mode='markers',
                                name="Short",
                                marker_color="red",
                                marker_size=10)])

                    title = str(
                        timeframe + " " + self.get_name() + " " +
                        symbol + " " + exchange.get_name())

                    chart.update_layout(
                        title_text=title,
                        title={
                            'y': 0.9,
                            'x': 0.5,
                            'xanchor': 'center',
                            'yanchor': 'top'},
                        xaxis_rangeslider_visible=False,
                        xaxis_title="Time",
                        yaxis_title="Price (USD)",
                        paper_bgcolor='white',
                        plot_bgcolor='white',
                        xaxis_showgrid=True,
                        yaxis_showgrid=True)

                    chart.show()

                    return SignalEvent(symbol, int(entry_ts.timestamp()),
                                       direction, timeframe, self.name,
                                       exchange, entry_price, "Market", None,
                                       None, None, None)
                else:
                    return None

    def get_required_timeframes(self, timeframes: list, result=False):
        """
        No additional (other than current) timeframes required for this model.
        """

        if result:
            return timeframes
        else:
            pass
