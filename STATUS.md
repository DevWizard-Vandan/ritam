# RITAM — Project Status
# Last Updated: April 9, 2026 — Analog finder reviewed fixes (daily collapse + symbol/date range)
# Updating Agent: Codex (feature/backtesting-engine)

---

## Current Phase
**Phase 1 — Data Pipeline**
Goal: Get real Nifty 50 OHLCV data flowing into local database.

---

## ✅ Completed
- [x] Project scaffold created (v2 architecture)
- [x] AGENTS.md — full v2 vision and architecture documented
- [x] DECISIONS.md — 11 ADRs documented
- [x] All 12 task files created (Phases 1–7)
- [x] requirements.txt — all dependencies listed
- [x] src/config/settings.py — env loader
- [x] src/data/kite_client.py — Kite-compatible client implemented with yfinance (^NSEI / ^NSEBANK)
- [x] src/data/db.py — SQLite helpers (write/read candles)
- [x] src/data/kite_feed.py — OHLCV fetcher boilerplate
- [x] src/sentiment/preprocessor.py — headline cleaner
- [x] src/sentiment/scorer.py — FinBERT scorer (full implementation)
- [x] src/agents/aggregator.py — master signal aggregator
- [x] src/reasoning/gemma_client.py — Gemma 4 E2B/26B via Ollama + Gemini fallback
- [x] src/reasoning/analog_finder.py — historical analog finder (Gemma-powered)
- [x] src/reasoning/regime_classifier.py — regime classifier (Gemma-powered)
- [x] src/api/server.py — FastAPI WebSocket server
- [x] src/api/websocket_manager.py — WS connection manager
- [x] config/agent_weights.json — initial equal weights
- [x] src/data/news_fetcher.py — NewsAPI + RSS ingestion with APScheduler job and SQLite news_raw persistence
- [x] tests/data/test_news_fetcher.py — mocked unit tests for news ingestion pipeline
- [x] tests: initial test suite — Phase 1
- [x] src/backtest/engine.py — Backtrader engine with SMA crossover, trade log, and performance metrics
- [x] tests/backtest/test_engine.py — synthetic-candle unit tests (no DB calls)
- [x] src/reasoning/analog_finder.py — DB-driven historical window matcher (cosine/DTW) with next-5-day outcome
- [x] tests/reasoning/test_analog_finder.py — mocked unit tests for analog matching logic
- [x] src/reasoning/analog_finder.py — review fixes: intraday→daily collapse, symbol param, bounded history range

---

## 🔄 In Progress
- task_005.1 — backtest engine edge cases [Jules]
- task_005.2 — reasoning integration tests [Jules]

---

## ❌ Blocked / Issues
- None

---

## 📋 Up Next (Assign These in Order)
1. task_006 — Multi-agent orchestrator [Claude Code]
2. task_007 — Feedback loop [Claude Code]
3. task_010 — Gemma reasoning layer (after Ollama installed) [Claude Code]

---

## 🧠 Ollama Setup Status
- [ ] Ollama installed on dev machine
- [ ] gemma4:2b pulled (~2.5 GB)
- [ ] gemma4:26b pulled (~15 GB) — optional, needs GPU
- [ ] ollama serve running in background

---

## 📦 Branch Status
| Branch   | Status | PR |
|----------|--------|----|
| main     | Clean  | —  |
| feature/backtesting-engine | task_005 complete (backtesting engine) | pending |
| feature/tests-backtest-edge-cases | task_005.1 complete (backtest engine edge case tests) | pending |
| feature/reasoning-integration-tests | reasoning integration tests added | pending |

---

## 💰 Monthly Cost Tracker
| Tool               | Cost      |
|--------------------|-----------|
| Kite Connect       | ₹500      |
| Claude Code (Pro)  | ₹1,670    |
| OpenAI Codex       | ₹1,670    |
| Jules              | ₹0        |
| Gemma 4 (Ollama)   | ₹0        |
| Gemini API         | ₹0        |
| **Total**          | **₹3,840**|
