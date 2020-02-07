import talib as ta
import pandas as pd

class Features:
    """Model feature library. TA indicators are here."""

    def trending(bars, lookback_period: int):
        """Return trending = True if price action (bars) forming successive higher or
        lower swings. Return direction = -1 for downtrend, 0 for no trend, 1 for
        uptrend."""
        self.check_bars_type(bars)

        trending = False
        direction = None
        return trending, direction

    def convergent(bars, lookback_period: int, indicator: list):
        """ Return True if price and indicator swings are convergent."""

        self.check_bars_type(bars)

        convergent = False
        return convergent

    def sr_levels(bars):
        """Return levels of support and resistance in given period."""

        self.check_bars_type(bars)

        levels = None
        return levels

    def SMA(bars, period:int):
        """Simple moving average of previous n (or period) bars close price.

        SMA = (sum of all closes in period) / period. """

        self.check_bars_type(bars)

        ma = None
        return ma

    def EMA(bars, period:int):
        """Exponential moving average of previous n bars close price.

        EMA = price(t) * k + EMA(y) * ( 1 − k )

        where:
            t = today (current bar for any period)
            y = yesterday (previous bar close price)
            N = number of bars (period)
            k = 2 / (N + 1) (weight factor)"""

        self.check_bars_type(bars)

        ema = None
        return ema

    def MACD(bars):
        """Return MACD for given time series. Bars list must be 26 bars
        in length (last 26 bars for period).

        MACD = EMA(12) - EMA(26)"""

        self.check_bars_type(bars)

        macd = None
        return macd

    def CCI(bars, period: int):
        """ Return CCI (Commodity Chanel Index) for n bars close price.
​
        CCI = (Typical Price − MA) / 0.015 * Mean Deviation

        where:
            Typical Price = ∑P((H + L + C) / 3))
            P = number of bars (period)
            MA = Moving Average = (∑P Typical Price) / P
            Mean Deviation=(∑P | Typical Price - MA |) / P"""

        self.check_bars_type(bars)

        cci = ta.CCI(bars['high'], bars['low'], bars['close'], timeperiod=period)

        return cci

    def BB(bars, period: int):
        """ Return top, bottom and mid Bollinger Bands for n bars close price.

        It is assumed that Bollinger Bands are desired at 2 standard deviation's from the mean.
        """
        
        self.check_bars_type(bars)

        bb = None
        return bb

    def fractals(bars: list, window:int=5):
        """ Returns a list of size len(bars) containing a value for each bar. The value will state whether its corresponding
        bar is a top fractal or a bottom fractal. Returns 1 for top fractals, 0 for non-fractals, -1 for bottom fractals.
        
        The Formulas for Fractals Are:

            Bearish Fractal (-1)=
            High(N)>High(N−2) and
            High(N)>High(N−1) and
            High(N)>High(N+1) and
            High(N)>High(N+2)
            ​    
            ﻿Bullish Fractal (1) = 
            Low(N)<Low(N−2) and
            Low(N)<Low(N−1) and
            Low(N)<Low(N+1) and
            Low(N)<Low(N+2)

        where N is center bar in window and (N+-1) (N+-2) are bars on either side of the center bar.
​   
        """
        self.check_bars_type(bars)

        frac = None
        return frac

    def check_bars_type(bars):
        assert isinstance(bars, pd.DataFrame)
