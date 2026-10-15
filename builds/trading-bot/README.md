# Paper-trading bot

Runs every hour through GitHub Actions (`.github/workflows/paper-bot.yml`). Fake money only.

GitHub's hourly schedule is best-effort: runs can start late or be skipped. Each run replays every closed bar since the last one, oldest first, so a late run loses no trades.

## Each run

1. Fetches closed hourly and daily price bars for BTC, ETH, SOL and DOGE in euros from Kraken's public API.
2. Applies four rules from the earlier backtest: Donchian 20/10 breakout, 30-bar momentum, 50/200 moving-average cross, and buy after a 10% drop then hold 5 bars.
3. Gives every rule, coin and bar size its own paper account starting at EUR 10, plus a buy-and-hold account per coin and bar size for comparison: 40 accounts in all.
4. Charges 0.5% per trade (set in `config.json`): the taker fee for small EU accounts, since closing-price fills are taker-like.
5. Writes `state/summary.md` (start here), `state/trades.csv`, `state/equity.csv` and `state/paper_state.json`, then commits them.

## Stop it

Add a file named `KILL_SWITCH` to this folder, or disable the workflow under the repo's Actions tab.

## Going live

Not built. A live version gets written only if Lazar decides to go live after the paper results, and switching it on is his step.

## Limits of paper results

- Paper trades fill at the bar's closing price. Real fills differ through spread and slippage.
- Real exchanges have minimum order sizes, which may block EUR 10 orders on some coins.
- A few days of paper trading is noise. It checks that the machinery works; it does not prove an edge.
