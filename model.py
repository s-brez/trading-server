"""
trading-server is a multi-asset, multi-strategy, event-driven execution
and backtesting platform (OEMS) for trading common markets.

Copyright (C) 2020  Sam Breznikar <sam@sdbgroup.io>

Licensed under GNU General Public License 3.0 or later.

Some rights reserved. See LICENSE.md, AUTHORS.md.
"""

from abc import ABC, abstractmethod
from features import Features as f
import re


class Model(ABC):
    """
    Base class for strategy models.
    """

    def __init__(self):
        super.__init__()

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
    def get_required_timeframes(self, timeframes):
        """
        Given a list of operating timeframes, append additional required
        timeframe strings to the list (amend in-place, no new list created).

        To be overwritten in each model.

        Args:
            timeframes: list of current-period operating timeframes.

        Returns:
            None.

        Raises:
            None.
        """


class TrendFollowing(Model):
    """
    Long-short trend-following model based on EMA's and MACD.

    Rules:
        1: Price must be trending on trigger timeframe.
        2: Price must be trending on doubled trigger timeframe.
        3. MACD swings convergent with trigger timeframe swings.
        4. Price must have pulled back to the 10/20 EMA EQ.
        5. Small reversal bar must be present in the 10/20 EMA EQ.
        6. There is no old S/R level between entry and T1.

    Supplementary factors (higher probability of success):
        1: Price has pulled back into an old S/R level.
        2: First pullback in a new trend.

    Entry:
        Buy when price breaks the high/low of the trigger bar.
        Execute buyStop when reversal bar closes with 1 bar expiry.

    Stop-loss:
        At swing high/low of the trigger bar.

    Positon management:
        T1: 1R, close 50% of position. Trade is now risk free.
        T2: Stay in trade until stop-out. As price continues to trend, move
            stop-loss to each new swing high/low.
    """

    name = "10/20 EMA EQ Trend-following"

    # Instruments and venues the model runs on.
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

    # First tuple element in tuple is feature function.
    # Second tuple element is feature param.
    # Third tuple element is feature type.
    features = [
        ("indicator", f.EMA, 10),
        ("indicator", f.EMA, 20),
        ("indicator", f.MACD, None)
        # f.trending,
        # f.convergent,
        # f.j_curve,
        # f.sr_levels,
        # f.small_bar,
        # f.reversal_bar,
        # f.new_trend
        ]

    def __init__(self):
        super()

    def run(self):
        """
        Run the model.

        Args:
            None:

        Returns:
            SignalEvent if signal is produced, otherwise None.

        Raises:
            None.

        """

        pass

    def get_required_timeframes(self, timeframes):
        """
        Add the equivalent doubled timeframe for each timeframe in
        the given list of operating timeframes.

        eg. if "1H" is present, add "2H" to the list.
        """

        to_add = []

        for timeframe in timeframes:

            # 1Min use 3Min as the "doubled" trigger timeframe.
            if timeframe == "1Min":
                if "3Min" not in timeframes and "3Min" not in to_add:
                    to_add.append("3Min")

            # 3Min use 5Min as the "doubled" trigger timeframe.
            elif timeframe == "3Min":
                if "5Min" not in timeframes and "5Min" not in to_add:
                    to_add.append("5Min")

            # 5Min use 15Min as the "doubled" trigger timeframe.
            elif timeframe == "5Min":
                if "15Min" not in timeframes and "15Min" not in to_add:
                    to_add.append("15Min")

            # 12H and 16H use 1D as the "doubled" trigger timeframe.
            elif timeframe == "12H" or timeframe == "16H":
                if "1D" not in timeframes and "1D" not in to_add:
                    to_add.append("1D")

            # 30Min use 1H as the "doubled" trigger timeframe.
            elif timeframe == "30Min":
                if "1H" not in timeframes and "1H" not in to_add:
                    to_add.append("1H")

            # All other timeframes just double the numeric value.
            else:
                num = int(''.join(filter(str.isdigit, timeframe)))
                code = re.findall("[a-zA-Z]+", timeframe)
                to_add.append((str(num * 2) + code[0]))

        for new_item in to_add:
            timeframes.append(new_item)
