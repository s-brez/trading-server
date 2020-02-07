class Features:
    """Model feature library."""

    def trending(lookback_period: int, bars: list):
        """Return True if price action (bars) forming successive higher or
        lower swings. Return a -1 for downtrend, 0 for no trend, 1 for
        uptrend."""

        trending = False
        direction = None
        return trending, direction

    def convergent(lookback_period: int, bars: list, indicator: list):
        """ Return True if price and indicator swings are convergent."""

        convergent = False
        return convergent

    def sr_levels(bars: list):
        """Return levels of support and resistance in given period."""

        levels = None
        return levels

    def MA(period: int, bars: int):
        """Simple moving average of previous n (or period) bars close price.

        SMA = (sum of all closes in period) / period. """

        ma = None
        return ma

    def EMA(period: int, bars: list):
        """Exponential moving average of previous n bars close price.

        EMA = price(t) * k + EMA(y) * ( 1 − k )

        where:
            t = today (current bar for any period)
            y = yesterday (previous bar close price)
            N = number of bars (period)
            k = 2 / (N + 1) (weight factor)"""

        ema = None
        return ema

    def MACD(bars: list):
        """Return MACD for given time series. Bars list must be 26 bars
        in length (last 26 bars for period).

        MACD = EMA(12) - EMA(26)"""

        macd = None
        return macd

    def CCI(period: int, bars: list):
        """ Return CCI (Commodity Chanel Index) for n bars close price.
​
        CCI = (Typical Price − MA) / 0.015 * Mean Deviation

        where:
            Typical Price = ∑P((H + L + C) / 3))
            P = number of bars (period)
            MA = Moving Average = (∑P Typical Price) / P
            Mean Deviation=(∑P | Typical Price - MA |) / P"""

        cci = None
        return cci

    def BB(period: int, bars: list):
        """ Return top, bottom and mid Bollinger Bands for n bars close price.

        It is assumed that Bollinger Bands are desired at 2 standard deviation's from the mean.
        """
        bb = None
        return bb
