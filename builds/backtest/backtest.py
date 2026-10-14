"""Backtest the bot's rules on daily data from download.py.

The last 40% of each history is held out as an unseen test period. Positions
are taken the bar after a signal, so there is no look-ahead.
"""
from pathlib import Path

import numpy as np  # noqa: F401  (kept for quick experiments)
import pandas as pd

DATA = Path(__file__).resolve().parent / "data"
OUT = Path(__file__).resolve().parent / "results"
COINS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT"]
COSTS = {"0.1%": 0.001, "0.25%": 0.0025, "1%": 0.01, "10% (EUR1 on EUR10)": 0.10}


def rsi(c, n=14):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)


def state_machine(entry, exit_):
    pos, out = 0, []
    for e, x in zip(entry.values, exit_.values):
        if pos == 0 and e:
            pos = 1
        elif pos == 1 and x:
            pos = 0
        out.append(pos)
    return pd.Series(out, index=entry.index)


def signals(df):
    c = df.c
    s = {"buy_and_hold": pd.Series(1, index=c.index)}
    s["sma_50_200"] = (c.rolling(50).mean() > c.rolling(200).mean()).astype(int)
    s["momentum_30d"] = (c.pct_change(30) > 0).astype(int)
    hi = c.shift(1).rolling(20).max()
    lo = c.shift(1).rolling(10).min()
    s["donchian_20_10"] = state_machine(c > hi, c < lo)
    r = rsi(c)
    s["rsi_dip_30_50"] = state_machine(r < 30, r > 50)
    s["buy_dip10_hold5"] = (c.pct_change() < -0.10).rolling(5).max().fillna(0).astype(int)
    return s


def run(df, pos, cost):
    ret = df.c.pct_change().fillna(0)
    p = pos.shift(1).fillna(0)
    turn = p.diff().abs().fillna(p.abs())
    return p * ret - turn * cost, int(turn.sum())


def stats(net):
    eq = (1 + net).cumprod()
    return eq.iloc[-1] - 1, (eq / eq.cummax() - 1).min()


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    rows = []
    for coin in COINS:
        df = pd.read_csv(DATA / f"{coin}_1d.csv", index_col=0, parse_dates=True)
        cut = df.index[int(len(df) * 0.6)]
        for name, pos in signals(df).items():
            for cname, cost in COSTS.items():
                net, trades = run(df, pos, cost)
                tot, dd = stats(net)
                oos_tot, oos_dd = stats(net[net.index >= cut])
                rows.append(dict(coin=coin, strategy=name, cost=cname, trades=trades // 2, total_ret=tot,
                                 max_dd=dd, oos_ret=oos_tot, oos_dd=oos_dd, oos_start=str(cut.date())))
    R = pd.DataFrame(rows)
    R.to_csv(OUT / "backtest_all.csv", index=False)
    for cname in COSTS:
        sub = R[R.cost == cname].pivot(index="strategy", columns="coin", values="oos_ret")
        print(f"\n=== Out-of-sample return, cost {cname} ===")
        print((sub * 100).round(0))
