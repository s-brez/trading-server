"""
trading-server is a multi-asset, multi-strategy, event-driven execution
and backtesting platform (OEMS) for trading common markets.

Copyright (C) 2020  Sam Breznikar <sam@sdbgroup.io>

Licensed under GNU General Public License 3.0 or later.

Some rights reserved. See LICENSE.md, AUTHORS.md.
"""


class Features:
    """
    Model feature library.
    """

    def trending(self, lookback_period: int, bars: list):
        """
        Identigy if price action (bars) forming successive higher or
        lower swings.
        """

        return trending

    def new_trend(self, bars: list):
        """
        Return True if price has formed a new trend, False if not
        """

        return new_trend

    def j_curve(self, bars: list):
        """
        Identify optimal price action geometry (j-curve) for trends.
        """

        return j_curve

    def small_bar(self, bars: list, n: int):
        """
        Identify if the current bar is "small" relative to the last n bars.

        """

        small_bar

    def reversal_bar(self, bars: list, n: int):
        """
        Identify if the last n bars contain a reversal pattern.
        """

        return reversal_bar

    def convergent(self, lookback_period: int, bars: list, indicator: list):
        """ Return True if price and indicator swings are convergent."""

        return convergent

    def sr_levels(self, bars: list):
        """
        Return levels of support and resistance in given period.
        """

        return levels

    def MA(self, period: int, bars: int):
        """
        Simple moving average of previous n bars close price.

        SMA = (sum of all closes in period) / period.
        """

        return ma

    def EMA(self, period: int, bars: list):
        """
        Exponential moving average of previous n bars close price.

        EMA = price(t) * k + EMA(y) * ( 1 − k )

        where:
            t = today (current bar for any period)
            y = yesterday (previous bar close price)
            N = number of bars (period)
            k = 2 / (N + 1) (weight factor)
        """

        return ema

    def MACD(self, bars: list):
        """
        Return MACD for given time series. Bars list must be 26 bars
        in length (last 26 bars for period).

        MACD = EMA(12) - EMA(26)
        """

        return macd

    def CCI(self, period: int, bars: list):
        """
        Return CCI (Commodity Chanel Index) for n bars close price.
​
        CCI = (Typical Price − MA) / 0.015 * Mean Deviation

        where:
            Typical Price = ∑P((H + L + C) / 3))
            P = number of bars (period)
            MA = Moving Average = (∑P Typical Price) / P
            Mean Deviation=(∑P | Typical Price - MA |) / P
        """

        return cci
