# Task 005 — Backtesting Engine + 2008 Crisis Test
**Assigned to:** Codex
**Status:** TODO
**Phase:** 3 — Backtesting
**Depends on:** Task 002 (historical OHLCV data in DB)

## Goal
Build src/backtest/engine.py using Backtrader that:
- Loads Nifty 50 OHLCV data from SQLite for a given date range
- Implements a configurable strategy (start with: buy when sentiment > 0.6, sell when < -0.6)
- Runs backtest for a given scenario (e.g., 2008-01-01 to 2009-12-31)
- Outputs a result dict:
  {total_return_pct, sharpe_ratio, max_drawdown_pct, win_rate, total_trades, equity_curve (list)}
- Saves result to backtest/results/{scenario_name}.json

Also build src/backtest/scenario_runner.py that:
- Has pre-defined scenarios: crisis_2008, dotcom_2000, covid_2020, ukraine_2022, demonetization_2016
- Runs engine.py for each scenario
- Generates a comparison table

## Outputs
- src/backtest/engine.py
- src/backtest/scenario_runner.py
- backtest/results/ (auto-created folder for JSON results)
- tests/backtest/test_engine.py

## Definition of Done
- [ ] engine.py runs without error on 2008 data
- [ ] scenario_runner.py runs all 5 scenarios
- [ ] Results saved to JSON
- [ ] 5+ unit tests passing
- [ ] STATUS.md updated

