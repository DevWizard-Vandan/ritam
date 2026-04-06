# Task 001 — Zerodha Kite Connect Setup
**Assigned to:** Codex
**Status:** TODO
**Phase:** 1 — Data Pipeline
**Depends on:** Nothing (first task)

## Goal
Build src/data/kite_client.py — a reusable Kite Connect client that:
- Loads API credentials from .env (KITE_API_KEY, KITE_API_SECRET)
- Handles the daily access token login flow
- Exposes a single `get_client()` function that returns an authenticated KiteConnect instance
- Handles token expiry gracefully (logs error, does not crash)

## Inputs
- .env file with KITE_API_KEY and KITE_API_SECRET

## Outputs
- src/data/kite_client.py
- tests/data/test_kite_client.py (mock the API, test token loading)

## Definition of Done
- [ ] kite_client.py written with get_client() function
- [ ] Credentials loaded exclusively from .env
- [ ] 5 unit tests written and passing
- [ ] STATUS.md updated
- [ ] No hardcoded keys anywhere

