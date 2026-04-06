# Task 002 — OHLCV Data Pipeline (Historical + Live)
**Assigned to:** Codex
**Status:** TODO
**Phase:** 1 — Data Pipeline
**Depends on:** Task 001 (kite_client.py must be complete)

## Goal
Build src/data/kite_feed.py that:
- Uses kite_client.get_client() to authenticate
- Fetches historical Nifty 50 OHLCV data (minute candles) for past 10 years
- Fetches live Nifty 50 minute candles during market hours (9:15 AM – 3:30 PM IST)
- Saves all data to SQLite at data/market.db using SQLAlchemy
- Table schema: (id, symbol, timestamp_ist, open, high, low, close, volume)
- Runs as a scheduler — fetches new candles every 1 minute during market hours

## Inputs
- kite_client.get_client()
- DB_PATH from .env

## Outputs
- src/data/kite_feed.py
- src/data/db.py (database write/read helpers)
- tests/data/test_kite_feed.py

## Definition of Done
- [ ] Historical fetch works and saves to SQLite
- [ ] Live fetch scheduler runs correctly
- [ ] db.py has write_candles() and read_candles(symbol, from_date, to_date) functions
- [ ] 5+ unit tests (mock Kite API responses)
- [ ] STATUS.md updated

