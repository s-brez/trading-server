"""
trading-server is a multi-asset, multi-strategy, event-driven trade execution
and backtesting platform (OEMS) for trading common markets.

Copyright (C) 2020  Sam Breznikar <sam@sdbgroup.io>
Copyright (C) 2020  Marc Goulding <gouldingmarc@gmail.com>

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

    def trending(self, lookback_period: int, bars):
        """
        Return True if price action (bars) forming successive higher or
        lower swings. Return direction = -1 for downtrend, 0 for no trend,
        1 for uptrend.

        Returns:
            trending
        """

        self.check_bars_type(bars)

        fractals = self.fractals(bars[lookback_period:], window=window)
        highs = np.multiply(bars.high.values, fractals)
        highs = highs[highs > 0]
        lows = np.multiply(bars.low.values, fractals)
        lows = lows[lows < 0]*(-1)

        trending = False
        direction = 0

        if (highs[-1] > highs[-2] and highs[-2] > highs[-3]
                and lows[-1] > lows[-2] and lows[-2] > lows[-3]):
            trending = True
            direction = 1

        elif (highs[-1] < highs[-2] and highs[-2] < highs[-3]
                and lows[-1] < lows[-2] and lows[-2] < lows[-3]):
            trending = True
            direction = -1

        else:
            trending = False
            direction = 0

        return trending, direction

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

        self.check_bars_type(bars)

        convergent = False
        return convergent

    def sr_levels(bars, n=8, t=0.02, s=3, f=3):
        """
        Find support and resistance levels using smoothed close price.

        Args:
            bars: OHLCV dataframe.
            n: bar window size.
            t: tolerance, % variance between min/maxima to be considered a level.
            s: smoothing factor. Lower is more sensitive.
            f: number of filter passes.

        Returns:
            support: list of support levels
            resistance: list of resistance levels

        Raises:
            None.

        """

        # Convert n to next even number.
        if n % 2 != 0:
            n += 1

        # Find number of bars.
        n_ltp = bars.close.values.shape[0]

        # Smooth close data.
        ltp_smoothed = smooth(bars.close.values, (n + 1), s)

        # Find delta (difference in adjacent prices).
        ltp_delta = np.zeros(n_ltp)
        ltp_delta[1:] = np.subtract(ltp_smoothed[1:], ltp_smoothed[:-1])

        resistance = []
        support = []

        # Identify initial levels.
        for i in range(n_ltp - n):

            # Get window for current bar.
            window = ltp_delta[i:(i + n)]

            # Split window in half.
            first = window[:int((n / 2))]  # first half
            last = window[int((n / 2)):]  # second half

            # Find highs and lows for both halves of window.
            # First/last being higher or lower indicates asc/desc price.
            r_1 = np.sum(first > 0)
            r_2 = np.sum(last < 0)
            s_1 = np.sum(first < 0)
            s_2 = np.sum(last > 0)

            # Detect local maxima. If two points match, its a level.
            if r_1 == (n / 2) and r_2 == (n / 2):
                try:
                    resistance.append(bars.close.values[i + (int((n / 2)) - 1)])
                # Catch empty list error if no levels are present.
                except Exception as ex:
                    pass

            # Detect local minima. If two points match, its a level.
            if s_1 == (n / 2) and s_2 == (n / 2):
                try:
                    support.append(bars.close.values[i + (int((n / 2)) - 1)])
                # Catch empty list error if no levels are present.
                except Exception as ex:
                    pass

        # Filter levels f times.
        levels = np.sort(np.append(support, resistance))
        filtered_levels = cluster_filter(levels, t, multipass=True)
        for i in range(f - 1):
            filtered_levels = cluster_filter(filtered_levels, t, multipass=True)

        return filtered_levels

    def cluster_filter(levels: list, t: float, multipass: bool):
        """
        Given a list of prices, identify groups of levels within t% of each other.

        Args:
            levels: list of price levels.
            t: tolerance, % variance between min/maxima to be considered a level.
            multipass: if True, run the filter for cluster sizes=3 or more. If
                       False, filter only once (will pick up clusters size=2).
        Returns:
            None.
        Raises:
            None.
        """

        # Identify initial level clusters (single pass).
        temp_levels = []
        for lvl_1 in levels:
            for lvl_2 in levels:
                range_max = lvl_1 + lvl_1 * t
                range_min = lvl_1 - lvl_1 * t
                if lvl_2 >= range_min and lvl_2 <= range_max:
                    cluster = sorted([lvl_1, lvl_2])
                    if lvl_2 != lvl_1:
                        if cluster not in temp_levels:
                            temp_levels.append(cluster)

        # Identify strong clusters of 3 or more levels (multipass).
        if multipass:
            flattened = [item for sublist in temp_levels for item in sublist]
            c_count = 0
            to_append = []
            for cluster in temp_levels:
                for lvl_1 in cluster:
                    range_max = lvl_1 + lvl_1 * t
                    range_min = lvl_1 - lvl_1 * t
                    for lvl_2 in flattened:
                        if lvl_2 >= range_min and lvl_2 <= range_max:
                            to_append.append([c_count, lvl_2])
                c_count += 1

            # Add levels to their respective clusters and remove duplicates.
            for pair in to_append:
                temp_levels[pair[0]].append(pair[1])
                temp_levels[pair[0]] = sorted(list(set(temp_levels[pair[0]])))

        # Aggregate similar levels and remove temp levels.
        agg_levels = [(sum(i) / len(i)) for i in temp_levels]
        to_remove = [i for cluster in temp_levels for i in cluster]

        # Catch second-pass np.array > list conversion error.
        if type(levels) != list:
            final_levels = [i for i in levels.tolist() if i not in to_remove]
        else:
            final_levels = [i for i in levels if i not in to_remove]

        return final_levels + agg_levels

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

    def RSI(self, bars, timeperiod: int = 14):
        """
        Return RSI for given time series.
        """

        self.check_bars_type(bars)

        rsi = ta.RSI(bars['close'], timeperiod)

        return rsi

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
        if (window % 2 != 1):
            window += 1

        # df.shape[0] is more logical but has a slower runtime, so I went with
        # len(df.index) instead:
        bars_length = len(bars.index)
        frac = np.zeros(bars_length).flatten()

        for bar in range((window-1)/2, bars_length-(window-1)/2):
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
