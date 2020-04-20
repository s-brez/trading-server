import matplotlib.pyplot as plt
import pandas as pd
import numpy as np


def cluster_filter(levels: list, t: float, multipass: bool):
    """
    Given a list  of prices, identify groups of levels within t% of each other.

    Args:
        levels: list of price levels.
        t: tolerance, % variance between min/maxima to be considered a level.
        multipass: if True, run the filter for cluster sizes=3 or more. If
                   False, filter only once (will pick up clusters size=2).
    Returns:

    Raises:

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

    # Catch second-pass np.array > list conversion error
    if type(levels) != list:
        final_levels = [i for i in levels.tolist() if i not in to_remove]
    else:
        final_levels = [i for i in levels if i not in to_remove]

    # print("Levels:")
    # for level in levels:
    #     print(level)

    # print("\nLevel clusters:")
    # for level in temp_levels:
    #     print(level)

    # print("\nAggregate levels:")
    # for level in sorted(list(set(agg_levels))):
    #     print(level)

    # print("\nFinal levels:")
    # for level in sorted(list(set(final_levels))):
    #     print(level)

    return final_levels + agg_levels


def sr_levels(bars, n=8, t=0.02, s=3, f=3):
    """
    Find support and resistance levels using smoothed close price.

    Args:
        bars: OHLCV dataframe.
        n: bar window size.
        t: tolerance, % variance between min/maxima to be considered a level.
        s: smoothing factor. lower is more sensitive.
        f: number of filter passes.

    Returns:
        support: list of support levels
        resistance: list of resistance levels

    Raises:
        None.

    """
    from scipy.signal import savgol_filter as smooth

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


lookback = 200
n = 10
t = 0.02
s = 3
f = 3

bars = pd.read_csv("XBTUSD1D.csv", delimiter=',').tail(lookback)

levels = sr_levels(bars, n, t, s, f)

# Plot high and low values.
plt.plot(bars.high.values)
plt.plot(bars.low.values)

# Plot levels.
for i in range(len(levels)):
    plt.hlines(levels[i], 0, lookback)


# plt.hlines(2900, 0, 150, colors='r')


plt.show()
