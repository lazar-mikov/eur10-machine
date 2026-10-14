# eur10-machine

Private working repo for Lazar's EUR 10 experiment. The scheduled Claude runs (operator, builder, auditor) and plain scripts work here. The rules live in the Constitution tab of the "EUR 10 Growth Map" doc.

## What runs here

- `builds/trading-bot/`: paper-trading bot, every hour through GitHub Actions. Fake money only. Read `builds/trading-bot/state/summary.md` for results.
- `builds/backtest/`: the earlier backtest scripts (daily prices since 2020).
- `ledger/money.csv`: every real euro in or out.

## Rules

- No code here places real orders. Going live is Lazar's decision and his step.
- No keys or passwords in this repo, ever.
