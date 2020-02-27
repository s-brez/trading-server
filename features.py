"""
trading-server is a multi-asset, multi-strategy, event-driven execution
and backtesting platform (OEMS) for trading common markets.

Copyright (C) 2020  Sam Breznikar <sam@sdbgroup.io>
Copyright (C) 2020  Marc Goulding <gouldingmarc@gmail.com >

Licensed under GNU General Public License 3.0 or later.

Some rights reserved. See LICENSE.md, AUTHORS.md.
"""

from scipy.signal import savgol_filter as smooth
import matplotlib.pyplot as plt
import talib as ta
import pandas as pd
import numpy as np


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
        Return True if price has formed a new trend, False if not.
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

    def sr_levels(bars, smoothing_factor, tolerance):
        """
        Return suport and resistance levels in a given period.

        Args:
            bars: series containing close prices.
            smoothing_factor: smoothing factor. lower is more sensitive.
            tolerance: acceptable variance between points to be considered
               a level.

        Returns:
            support: list of support levels
            resistance: list of resistance levels

        Raises:
            None.

        """

        # Convert n to the next even number.
        if smoothing_factor % 2 != 0:
            smoothing_factor += 1

        n_ltp = bars.shape[0]

        # Smooth the data.
        ltp_s = smooth(bars, (smoothing_factor + 1), 3)

        # taking a simple derivative
        ltp_d = np.zeros(n_ltp)
        ltp_d[1:] = np.subtract(ltp_s[1:], ltp_s[:-1])

        resistance = []
        support = []

        for i in range(n_ltp - n):
            arr_sl = ltp_d[i:(i + n)]
            first = arr_sl[:int((n / 2))]  # first half
            # first = arr_sl[:4]  # first half
            last = arr_sl[int((n / 2)):]  # second half

            r_1 = np.sum(first > 0)
            r_2 = np.sum(last < 0)

            s_1 = np.sum(first < 0)
            s_2 = np.sum(last > 0)

            # local maxima detection
            if (r_1 == (n / 2)) and (r_2 == (n / 2)):
                resistance.append(ltp[i + (int((n / 2)) - 1)])

            # local minima detection
            if (s_1 == (n / 2)) and (s_2 == (n / 2)):
                support.append(ltp[i + (int((n / 2)) - 1)])

        levels = np.sort(np.append(support, resistance))
        tmp_levels = levels
        for i in range(1, len(levels)):
            if levels[i]-levels[i-1] > tolerance * levels[i]:
                tmp_levels = tmp_levels[tmp_levels != levels[i]]

        return support, resistance

    def SMA(self, period: int, bars: int):
        """
        Simple moving average of previous n bars close price.

        SMA = (sum of all closes in period) / period.
        """
        self.check_bars_type(bars)

        ma = ta.MA(bars['close'], timeperiod=period, matype=0)

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

        self.check_bars_type(bars)

        ema = ta.EMA(bars['close'], timeperiod=period)

        return ema

    def MACD(self, name,  bars: list):
        """
        Return MACD for given time series. Bars list must be 26 bars
        in length (last 26 bars for period).

        MACD = EMA(12) - EMA(26)

        Note we only use the MACD, not signal or histogram.
        """

        self.check_bars_type(bars)

        macd, signal, hist = ta.MACD(
            bars['close'], fastperiod=12, slowperiod=26, signalperiod=9)

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

        self.check_bars_type(bars)

        cci = ta.CCI(
            bars['high'], bars['low'], bars['close'], timeperiod=period)

        return cci

    def BB(self, bars, period: int):
        """
        Return top, bottom and mid Bollinger Bands for n bars close price.
        It is assumed that:
        -- Bollinger Bands are desired at 2 standard deviation's from the mean.
        -- moving average used is a simple moving average
        """

        self.check_bars_type(bars)

        upperband, middleband, lowerband = ta.BBANDS(
            close, timeperiod=period, nbdevup=2, nbdevdn=2, matype=0)

        return upperband, middleband, lowerband

    def fractals(self, bars, window: int = 5):
        """
        Returns a list of size len(bars) containing a value for each bar.
        The value will state whether its corresponding bar is a top
        fractal or a bottom fractal. Returns 1 for top fractals, 0 for
        non-fractals, -1 for bottom fractals.

        The Formulas for Fractals Are:
            Bearish Fractal (-1)=
            High(N)>High(N−2) and
            High(N)>High(N−1) and
            High(N)>High(N+1) and
            High(N)>High(N+2)

            ﻿Bullish Fractal (1) =
            Low(N)<Low(N−2) and
            Low(N)<Low(N−1) and
            Low(N)<Low(N+1) and
            Low(N)<Low(N+2)

        where N is center bar in window and (N+-1) (N+-2) are bars on either
        side of the center bar.
​
        """
        self.check_bars_type(bars)

        # df.shape[0] is more logical but has a slower runtime, so I went with
        # len(df.index) instead:
        bars_length = len(bars.index)
        frac = np.zeros(bars_length).flatten()

        for bar in range(2, bars_length - 2):
            if (bars['high'][bar] > bars['high'][bar-2]
                    and bars['high'][bar] > bars['high'][bar-1]
                    and bars['high'][bar] > bars['high'][bar+1]
                    and bars['high'][bar] > bars['high'][bar+2]):

                frac[bar] = 1

            elif (bars['low'][bar] < bars['low'][bar-2]
                    and bars['low'][bar] < bars['low'][bar-1]
                    and bars['low'][bar] < bars['low'][bar+1]
                    and bars['low'][bar] < bars['low'][bar+2]):

                frac[bar] = -1

        return frac

    def check_bars_type(self, bars):

        assert isinstance(bars, pd.DataFrame)
