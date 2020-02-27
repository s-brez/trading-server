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

        fractals = self.fractals(bars[lookback_period:],window=window)
        highs = np.multiply(bars.high.values,fractals)
        highs = highs[highs>0]
        lows = np.multiply(bars.low.values,fractals)
        lows = lows[lows<0]*(-1)

        trending = False
        direction = 0

        if highs[-1]>highs[-2] and highs[-2]>highs[-3] and lows[-1]>lows[-2] and lows[-2]>lows[-3]:
        	trending = True
        	direction = 1
        elif highs[-1]<highs[-2] and highs[-2]<highs[-3] and lows[-1]<lows[-2] and lows[-2]<lows[-3]:
        	trending = True
        	direction = -1
        else:
        	trending=False
        	direction=0

        return trending, direction

    def convergent(self, bars, lookback_period: int, indicator: list):
        """ Return True if price and indicator swings are convergent."""

        self.check_bars_type(bars)

        convergent = False
        return convergent

    def sr_levels(self, bars, nbounces: int=2, tolerance: int=0.02, window=5):
        """Inputs:

        Return:
        -- levels of support and resistance in given period.
        -- times the level has been tested (both as a support or as a resistance)
        -- last time it was tested. Older levels are less relevant now.

        Steps:
        1) Obtain fractals to find local maxima an minima
        2) Define distance margin between fractals that will be allowed (they won't be at exactly the same price).
        3) Find fractals located around the same price. Define those as possible sr levels.
        4) How many fractals are located at that level to determine the num of times it was tested.
        5) If times tested > nbounces -> it's a valid sr level
        6) ?
        """

        # TODO: works properly when no levels are found?

        self.check_bars_type(bars)

        fractals = self.fractals(bars,window=window)
        # obtain prices for fractals (high if top, low if bottom):
        # levels = bars.mul(fractals, axis='index')
        # highs = levels[levels.high > 0].high.values
        # lows  = levels[levels.low  < 0].low.mul(-1,axis='index').values

        highs = np.multiply(bars.high.values,fractals)
        highs = highs[highs>0]
        lows = np.multiply(bars.low.values,fractals)
        lows = lows[lows<0]*(-1)
        
        possible_levels = np.append(highs,lows)
        
        # group levels within tolerance % of each other:
        possible_levels = np.sort(possible_levels)
        cluster = [possible_levels[0]]
        k = 0
        for i in range(1,len(possible_levels)):
            # if abs(possible_levels[i-1]-possible_levels[i])<tolerance*possible_levels[i-1]:
            if abs(possible_levels[i-1]-possible_levels[i])<tolerance*max(possible_levels[i-1],possible_levels[i]):

                cluster.append(possible_levels[i])

            else:

                mean = np.mean(cluster)
                for j in range(k,i):
                    possible_levels[j] = mean
                k=i
                cluster = [possible_levels[i]]

        # remove duplicates:
        val = np.unique(possible_levels).tolist()
        # check times each level was tested:
        levels = []
        for level in val:
            if possible_levels.tolist().count(level)>=nbounces:
                levels.append(level)
        # return levels
        return val
    def supres(ltp, n):
        """
        This function takes a numpy array of last traded price
        and returns a list of support and resistance levels 
        respectively. n is the number of entries to be scanned.
        """
        from scipy.signal import savgol_filter as smooth

        # converting n to a nearest even number
        if n % 2 != 0:
            n += 1
        print(type(int((n / 2))))

        n_ltp = ltp.shape[0]

        # smoothening the curve
        ltp_s = smooth(ltp, (n + 1), 3)

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

        levels = np.sort(np.append(support,resistance))
        tmp_levels = levels
        for i in range(1,len(levels)):
        	if levels[i]-levels[i-1]>0.02*levels[i]:
        		tmp_levels = tmp_levels[tmp_levels!=levels[i]]
        return support, resistance

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
        if (window%2 != 1):
        	window+=1


        # df.shape[0] is more logical but has a slower runtime, so I went with len(df.index) instead:
        bars_length = len(bars.index)
        frac = np.zeros(bars_length).flatten()

        for bar in range((window-1)/2,bars_length-(window-1)/2):
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
