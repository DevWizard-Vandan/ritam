# RITAM — Project Status
# Last Updated: April 9, 2026 — Task 003 news ingestion pipeline implemented
# Updating Agent: Codex (feature/data-pipeline)

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

---

## 🔄 In Progress
- task_002 — OHLCV historical + live pipeline [Codex]

---

## ❌ Blocked / Issues
- None

---

## 📋 Up Next (Assign These in Order)
1. task_002 — OHLCV historical + live pipeline [Codex]
2. task_004 — FinBERT scorer (complete implementation) [Claude Code]
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
| feature/news-pipeline | task_003 complete (news ingestion pipeline) | pending |

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
