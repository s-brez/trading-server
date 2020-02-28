import matplotlib.pyplot as plt
import pandas as pd
import numpy as np


def sr_levels(bars, n, t, s):
    """
    Find support and resistance levels using smoothed close price.

    Args:
        bars: OHLCV dataframe.
        n: bar window size.
        t: tolerance, % variance between min/maxima to be considered a level.
        s: smoothing factor. lower is more sensitive.

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

    # Identify levels.
    for i in range(n_ltp - n):

        # Get window for current bar.
        arr_sl = ltp_delta[i:(i + n)]

        # Split window in half.
        first = arr_sl[:int((n / 2))]  # first half
        last = arr_sl[int((n / 2)):]  # second half

        # Find highs and lows for both halves of window.
        # First/last being higher or lower indicates asc/desc price.
        r_1 = np.sum(first > 0)
        r_2 = np.sum(last < 0)
        s_1 = np.sum(first < 0)
        s_2 = np.sum(last > 0)

        # Detect local maxima. If two points match, its a level.
        if r_1 == (n / 2) and r_2 == (n / 2):
            resistance.append(bars.close.values[i + (int((n / 2)) - 1)])

        # Detect local minima. If two points match, its a level.
        if s_1 == (n / 2) and s_2 == (n / 2):
            support.append(bars.close.values[i + (int((n / 2)) - 1)])

    # Identify initial level clusters.
    levels = np.sort(np.append(support, resistance))
    temp_levels = []
    for lvl_1 in levels:
        for lvl_2 in levels:
            range_max = lvl_1 + lvl_1 * t
            range_min = lvl_1 - lvl_1 * t

            # Record levels within t% of each other.
            if lvl_2 >= range_min and lvl_2 <= range_max:
                cluster = sorted([lvl_1, lvl_2])
                if lvl_2 != lvl_1:
                    if cluster not in temp_levels:
                        temp_levels.append(cluster)

    # Identify strong clusters of 3 or more levels.
    flattened = [item for sublist in temp_levels for item in sublist]
    c_count = 0
    to_append = []
    for cluster in temp_levels:
        for lvl_1 in cluster:
            range_max = lvl_1 + lvl_1 * t
            range_min = lvl_1 - lvl_1 * t

            for lvl_2 in flattened:

                # Record levels within t% of each other.
                if lvl_2 >= range_min and lvl_2 <= range_max:
                    to_append.append([c_count, lvl_2])
        c_count += 1

    # Add levels to their respective clusters and remove duplicates
    for pair in to_append:
        temp_levels[pair[0]].append(pair[1])
        temp_levels[pair[0]] = sorted(list(set(temp_levels[pair[0]])))

    # Aggregate similar levels and remove temp levels.
    agg_levels = [(sum(i) / len(i)) for i in temp_levels]
    to_remove = [i for cluster in temp_levels for i in cluster]
    final_levels = [i for i in levels.tolist() if i not in to_remove]

    print("Levels:")
    for level in levels:
        print(level)

    print("\nLevel clusters:")
    for level in temp_levels:
        print(level)

    print("\nAggregate levels:")
    for level in list(set(agg_levels)):
        print(level)

    print("\nFinal levels:")
    for level in final_levels:
        print(level)

    return agg_levels + final_levels


lookback = 200
n = 8
t = 0.02
s = 3

bars = pd.read_csv("XBTUSD1D.csv", delimiter=',').tail(lookback)

levels = sr_levels(bars, n, t, s)

# Plot high and low values.
plt.plot(bars.high.values)
plt.plot(bars.low.values)

# Plot levels.
for i in range(len(levels)):
    plt.hlines(levels[i], 0, lookback)


# plt.hlines(2900, 0, 150, colors='r')


plt.show()
