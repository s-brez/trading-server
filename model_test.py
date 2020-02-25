import re


timeframes = ["1D"]


def required_timeframes(timeframes):
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


required_timeframes(timeframes)

print(timeframes)
