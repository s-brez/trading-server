import talib as ta
import pandas as pd
import numpy as np

class Features:
    """Model feature library. TA indicators are here."""

    def trending(self, bars, lookback_period: int):
        """Return trending = True if price action (bars) forming successive higher or
        lower swings. Return direction = -1 for downtrend, 0 for no trend, 1 for
        uptrend."""
        self.check_bars_type(bars)

        trending = False
        direction = None
        return trending, direction

    def convergent(self, bars, lookback_period: int, indicator: list):
        """ Return True if price and indicator swings are convergent."""

        self.check_bars_type(bars)

        convergent = False
        return convergent

    def sr_levels(self, bars):
        """Return levels of support and resistance in given period."""

        self.check_bars_type(bars)

        levels = None
        return levels

    def SMA(self, bars, period:int):
        """Simple moving average of previous n (or period) bars close price.

        SMA = (sum of all closes in period) / period. """

        self.check_bars_type(bars)

        ma = ta.MA(bars['close'], timeperiod=period, matype=0)
        return ma

    def EMA(self, bars, period:int):
        """Exponential moving average of previous n bars close price.

        EMA = price(t) * k + EMA(y) * ( 1 − k )

        where:
            t = today (current bar for any period)
            y = yesterday (previous bar close price)
            N = number of bars (period)
            k = 2 / (N + 1) (weight factor)"""

        self.check_bars_type(bars)

        ema = ta.EMA(bars['close'], timeperiod=period)
        return ema

    def MACD(self, bars):
        """Return MACD for given time series. Bars list must be 26 bars
        in length (last 26 bars for period).

        MACD = EMA(12) - EMA(26)"""

        self.check_bars_type(bars)

        macd = None
        return macd

    def CCI(self, bars, period: int):
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

    def BB(self, bars, period: int):
        """ Return top, bottom and mid Bollinger Bands for n bars close price.

        It is assumed that:
        -- Bollinger Bands are desired at 2 standard deviation's from the mean.
        -- moving average used is a simple moving average
        """
        
        self.check_bars_type(bars)

        upperband,middleband,lowerband = ta.BBANDS(close, timeperiod=period, nbdevup=2, nbdevdn=2, matype=0)

        return upperband, middleband, lowerband

    def fractals(self, bars, window:int=5):
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


        # df.shape[0] is more logical but has a slower runtime, so I went with len(df.index) instead:
        bars_length = len(bars.index)
        frac = np.zeros(bars_length).flatten()

        for bar in range(2,bars_length-2):
            if (bars['high'][bar]>bars['high'][bar-2]
                and bars['high'][bar]>bars['high'][bar-1]
                and bars['high'][bar]>bars['high'][bar+1]
                and bars['high'][bar]>bars['high'][bar+2]):

                frac[bar] = 1

            elif (bars['low'][bar]<bars['low'][bar-2]
                and bars['low'][bar]<bars['low'][bar-1]
                and bars['low'][bar]<bars['low'][bar+1]
                and bars['low'][bar]<bars['low'][bar+2]):

                frac[bar] = -1

        return frac

    def check_bars_type(self, bars):
        assert isinstance(bars, pd.DataFrame)
