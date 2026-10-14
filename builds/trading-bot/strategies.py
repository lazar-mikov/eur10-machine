"""Trading rules from the earlier backtest.

Each function takes a list of closing prices (oldest first, last = most recent
closed bar) and returns 1 to hold the coin or 0 to hold cash. Only past and
current closes are used, so there is no look-ahead.
"""


def sma(values, n):
    if len(values) < n:
        return None
    return sum(values[-n:]) / n


def sma_cross(closes, fast=50, slow=200):
    """Hold while the 50-bar average is above the 200-bar average."""
    f, s = sma(closes, fast), sma(closes, slow)
    if f is None or s is None:
        return 0
    return 1 if f > s else 0


def momentum(closes, lookback=30):
    """Hold while the price is above where it was `lookback` bars ago."""
    if len(closes) <= lookback:
        return 0
    return 1 if closes[-1] > closes[-1 - lookback] else 0


def donchian(closes, entry=20, exit_=10):
    """Buy on a close above the previous 20-bar high; sell on a close below the previous 10-bar low."""
    pos = 0
    for i in range(entry, len(closes)):
        hi = max(closes[i - entry:i])
        lo = min(closes[i - exit_:i])
        if pos == 0 and closes[i] > hi:
            pos = 1
        elif pos == 1 and closes[i] < lo:
            pos = 0
    return pos


def buy_dip(closes, drop=0.10, hold=5):
    """Hold for `hold` bars after any bar that fell more than `drop`."""
    start = max(1, len(closes) - hold)
    for i in range(start, len(closes)):
        if closes[i] / closes[i - 1] - 1 < -drop:
            return 1
    return 0


STRATEGIES = {
    "donchian_20_10": donchian,
    "momentum_30": momentum,
    "sma_50_200": sma_cross,
    "buy_dip10_hold5": buy_dip,
}
