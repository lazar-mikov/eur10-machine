#!/usr/bin/env python3
"""Paper-trading bot for the EUR 10 machine.

Runs every hour from GitHub Actions. This version trades fake money only:
there is no code path that places a real order. Each strategy, coin and bar
size gets its own paper account that starts with EUR 10, next to a
buy-and-hold account for comparison. Results go to state/.
"""
import csv
import datetime as dt
import json
import sys
from pathlib import Path

import requests

from strategies import STRATEGIES

HERE = Path(__file__).resolve().parent
CONFIG = json.loads((HERE / "config.json").read_text())
STATE_DIR = HERE / "state"
STATE_FILE = STATE_DIR / "paper_state.json"
TRADES_FILE = STATE_DIR / "trades.csv"
EQUITY_FILE = STATE_DIR / "equity.csv"
SUMMARY_FILE = STATE_DIR / "summary.md"
KILL_SWITCH = HERE / "KILL_SWITCH"
KRAKEN_OHLC = "https://api.kraken.com/0/public/OHLC"


def now_iso():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_closed_bars(pair, interval):
    """Return (times, closes) for closed bars only. Kraken's last row is still forming."""
    r = requests.get(KRAKEN_OHLC, params={"pair": pair, "interval": interval}, timeout=30)
    r.raise_for_status()
    data = r.json()
    if data.get("error"):
        raise RuntimeError(f"{pair}: {data['error']}")
    key = next(k for k in data["result"] if k != "last")
    rows = data["result"][key][:-1]
    return [int(row[0]) for row in rows], [float(row[4]) for row in rows]


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"started": now_iso(), "accounts": {}}


def get_account(state, key, start):
    return state["accounts"].setdefault(
        key, {"cash": start, "units": 0.0, "pos": 0, "last_bar": 0, "trades": 0, "start": start}
    )


def apply_target(acc, target, price, fee):
    """Move a paper account to the target position at `price`, paying `fee` per trade.
    Returns the trade side ("buy"/"sell") or None."""
    if target == acc["pos"]:
        return None
    if target == 1:
        acc["units"] = acc["cash"] * (1 - fee) / price
        acc["cash"] = 0.0
        side = "buy"
    else:
        acc["cash"] = acc["units"] * price * (1 - fee)
        acc["units"] = 0.0
        side = "sell"
    acc["pos"] = target
    acc["trades"] += 1
    return side


def step_account(acc, rule, times, closes, fee):
    """Apply `rule` to every closed bar the account hasn't seen yet, oldest first, so a
    late or skipped scheduled run loses no bars. A new account starts at the latest bar.
    Returns the trades made as (side, price, bar_time)."""
    new = [i for i, t in enumerate(times) if t > acc["last_bar"]]
    if acc["last_bar"] == 0:
        new = new[-1:]
    made = []
    for i in new:
        target = 1 if rule == 1 else rule(closes[: i + 1])
        side = apply_target(acc, target, closes[i], fee)
        if side:
            made.append((side, closes[i], times[i]))
        acc["last_bar"] = times[i]
    return made


def append_csv(path, header, rows):
    new = not path.exists()
    with path.open("a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(header)
        w.writerows(rows)


def write_summary(state, fee):
    started = dt.datetime.strptime(state["started"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
    days = (dt.datetime.now(dt.timezone.utc) - started).total_seconds() / 86400
    accts = state["accounts"]
    lines = [
        "# Paper results",
        "",
        f"Fake money only. Started {state['started']}, {days:.1f} days ago. Last run {now_iso()}. Fee {fee:.2%} per trade.",
        "Each account started with EUR 10. 'vs hold' compares it with buying the same coin at the start and holding.",
        "",
        "| Account | Equity EUR | Return | vs hold | Position | Trades |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    rows = []
    for key, a in accts.items():
        if key.startswith("hold|"):
            continue
        name, coin, interval = key.split("|")
        hold = accts.get(f"hold|{coin}|{interval}", {})
        eq, heq = a.get("equity", a["start"]), hold.get("equity", a["start"])
        rows.append((eq - heq, key, eq, a))
    for diff, key, eq, a in sorted(rows, reverse=True):
        ret = eq / a["start"] - 1
        lines.append(f"| {key} | {eq:.2f} | {ret:+.1%} | {diff:+.2f} | {'coin' if a['pos'] else 'cash'} | {a['trades']} |")
    lines += ["", "| Buy and hold | Equity EUR | Return |", "| --- | --- | --- |"]
    for key, a in sorted(accts.items()):
        if key.startswith("hold|"):
            eq = a.get("equity", a["start"])
            lines.append(f"| {key} | {eq:.2f} | {eq / a['start'] - 1:+.1%} |")
    beating = [k for d, k, e, a in rows if d > 0]
    lines += ["", f"Accounts beating hold right now: {len(beating)} of {len(rows)}."]
    if days < 3:
        lines.append("Less than 3 days of paper trading: too early to judge anything.")
    SUMMARY_FILE.write_text("\n".join(lines) + "\n")


def main():
    if KILL_SWITCH.exists():
        print("KILL_SWITCH present: doing nothing.")
        return 0
    if CONFIG.get("mode") != "paper":
        print("Only paper mode exists in this version. Refusing to run.")
        return 1
    fee, start = CONFIG["fee"], CONFIG["start_capital_eur"]
    STATE_DIR.mkdir(exist_ok=True)
    state = load_state()
    ts = now_iso()
    trades, equity = [], []
    for coin, pair in CONFIG["pairs"].items():
        for interval in CONFIG["intervals"]:
            try:
                times, closes = fetch_closed_bars(pair, interval)
            except Exception as e:  # one bad pair must not stop the others
                print(f"fetch failed for {coin} {interval}: {e}")
                continue
            price = closes[-1]
            accounts = {f"hold|{coin}|{interval}": 1}
            for name, fn in STRATEGIES.items():
                accounts[f"{name}|{coin}|{interval}"] = fn
            for key, rule in accounts.items():
                acc = get_account(state, key, start)
                for side, fill, bar_time in step_account(acc, rule, times, closes, fee):
                    trades.append([ts, key, side, fill, bar_time])
                acc["equity"] = acc["cash"] + acc["units"] * price
                acc["price"] = price
                equity.append([ts, key, round(acc["equity"], 4), acc["pos"], price])
    STATE_FILE.write_text(json.dumps(state, indent=1, sort_keys=True))
    append_csv(TRADES_FILE, ["time", "account", "side", "price", "bar_time"], trades)
    append_csv(EQUITY_FILE, ["time", "account", "equity_eur", "position", "price"], equity)
    write_summary(state, fee)
    print(f"{ts}: {len(trades)} paper trades, {len(equity)} accounts updated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
