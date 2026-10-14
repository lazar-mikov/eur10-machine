"""Download daily candles since 2020 from Binance's public data API into ./data."""
import time
from pathlib import Path

import pandas as pd
import requests

BASE = "https://data-api.binance.vision/api/v3/klines"
DATA = Path(__file__).resolve().parent / "data"


def fetch(symbol, interval, start_ms):
    rows, t = [], start_ms
    while True:
        r = requests.get(BASE, params=dict(symbol=symbol, interval=interval, startTime=t, limit=1000), timeout=30)
        r.raise_for_status()
        d = r.json()
        if not d:
            break
        rows += d
        t = d[-1][0] + 1
        if len(d) < 1000:
            break
        time.sleep(0.15)
    df = pd.DataFrame(rows, columns="open_time o h l c v close_time qv n tb tq ig".split())
    df["time"] = pd.to_datetime(df.open_time, unit="ms")
    for c in "ohlcv":
        df[c] = df[c].astype(float)
    return df[["time", "o", "h", "l", "c", "v"]].set_index("time")


if __name__ == "__main__":
    DATA.mkdir(exist_ok=True)
    start = int(pd.Timestamp("2020-01-01").timestamp() * 1000)
    for sym in ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT"]:
        df = fetch(sym, "1d", start)
        df.to_csv(DATA / f"{sym}_1d.csv")
        print(sym, len(df), df.index[0].date(), "->", df.index[-1].date())
