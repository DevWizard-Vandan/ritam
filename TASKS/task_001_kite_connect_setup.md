# Task 001 — Kite-Compatible Client Setup (yfinance backend)
**Assigned to:** Codex
**Status:** DONE
**Phase:** 1 — Data Pipeline
**Depends on:** Nothing (first task)

## Goal
Build src/data/kite_client.py as a reusable Kite-compatible client that:
- Preserves the public `get_client()` entrypoint used by downstream modules
- Implements the client using `yfinance` until Zerodha API keys are available
- Maps Nifty 50 and Bank Nifty instrument tokens to `^NSEI` and `^NSEBANK`
- Handles data fetch errors gracefully (logs error, does not crash)

## Inputs
- .env file (optional compatibility keys already supported by settings)

## Outputs
- src/data/kite_client.py
- tests/data/test_kite_client.py (mock the API, test token loading)

## Definition of Done
- [x] kite_client.py written with get_client() function
- [x] yfinance-backed compatibility client implemented for current phase
- [x] Nifty symbol mapping set to ^NSEI and ^NSEBANK
- [x] 5+ unit tests written (test module contains 6 tests)
- [x] STATUS.md updated
- [x] No hardcoded keys anywhere
