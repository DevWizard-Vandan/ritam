# RITAM - Project Status
# Last Updated: April 13, 2026 - React dashboard (frontend/) built with Vite + Tailwind CSS
# Updating Agent: Antigravity (feature/dashboard-v1)

---

## Current Phase
**Phase 1 - Data Pipeline**  
Goal: Get real Nifty 50 OHLCV data flowing into the local database.

---

## Completed
- [x] Project scaffold created (v2 architecture)
- [x] `AGENTS.md` - full v2 vision and architecture documented
- [x] `DECISIONS.md` - 11 ADRs documented
- [x] All 12 task files created (Phases 1-7)
- [x] `requirements.txt` - all dependencies listed
- [x] `src/config/settings.py` - env loader
- [x] `src/data/kite_client.py` - live Kite Connect path enabled when credentials exist, with yfinance fallback (`^NSEI` / `^NSEBANK`) and multi-index candle parsing fix
- [x] `scripts/seed_historical.py` and `scripts/verify_db.py` - repo-root bootstrap added so `python scripts/...` works without manual `PYTHONPATH`
- [x] `src/data/kite_feed.py` - real Kite historical seeding now chunks long day ranges into provider-safe windows
- [x] `src/data/db.py` - SQLite helpers (write/read candles)
- [x] `src/data/kite_feed.py` - OHLCV fetcher boilerplate
- [x] `src/sentiment/preprocessor.py` - headline cleaner
- [x] `src/sentiment/scorer.py` - FinBERT scorer (full implementation)
- [x] `src/agents/aggregator.py` - master signal aggregator
- [x] `src/reasoning/gemma_client.py` - Gemma 4 E2B/26B via Ollama + Gemini fallback
- [x] `src/reasoning/analog_finder.py` - historical analog finder (Gemma-powered)
- [x] `src/reasoning/regime_classifier.py` - regime classifier (Gemma-powered)
- [x] `src/api/server.py` - FastAPI WebSocket server
- [x] `src/api/websocket_manager.py` - WebSocket connection manager
- [x] `config/agent_weights.json` - initial equal weights
- [x] `src/data/news_fetcher.py` - NewsAPI + RSS ingestion with APScheduler job and SQLite `news_raw` persistence
- [x] `tests/data/test_news_fetcher.py` - mocked unit tests for news ingestion pipeline
- [x] Initial test suite - Phase 1
- [x] `scripts/seed_historical.py` - Historical DB seeding script
- [x] `scripts/verify_db.py` - DB verification script
- [x] `src/backtest/engine.py` - Backtrader engine with SMA crossover, trade log, and performance metrics
- [x] `tests/backtest/test_engine.py` - synthetic-candle unit tests (no DB calls)
- [x] `src/reasoning/analog_finder.py` - DB-driven historical window matcher (cosine/DTW) with next-5-day outcome
- [x] `tests/reasoning/test_analog_finder.py` - mocked unit tests for analog matching logic
- [x] `src/reasoning/analog_finder.py` - review fixes: intraday-to-daily collapse, symbol parameter, bounded history range
- [x] `src/rl/trading_env.py` - Gymnasium `NiftyTradingEnv` (20-candle normalized OHLCV, discrete actions, PnL reward)
- [x] `src/rl/trainer.py` - PPO training pipeline with DB candle loader and model save to `models/ppo_nifty.zip`
- [x] `tests/rl/test_trading_env.py` - synthetic-candle unit tests for reset/step/invalid action/date normalization
- [x] `src/orchestrator/agent.py` - `MarketOrchestrator.run_cycle()` with news -> sentiment -> regime -> analogs and buy/sell/hold signal logic
- [x] `tests/orchestrator/test_agent.py` - mocked unit tests for result shape, signal decisions, and empty-headline fallback
- [x] `README.md` - redesigned with project narrative, architecture, setup, and usage guidance
- [x] `src/feedback/tracker.py` - SQLite-backed prediction/outcome tracker with accuracy stats
- [x] `tests/feedback/test_tracker.py` - unit tests for prediction recording, outcome resolution, and accuracy metrics
- [x] `src/api/server.py` - added `/accuracy` and `/outcome` endpoints powered by feedback tracker
- [x] `src/feedback/tracker.py` - hardened with `feedback_predictions` table, conflict-safe inserts, and missing-outcome guard
- [x] `src/api/server.py` - moved feedback routes to `/api/feedback/accuracy` and `/api/feedback/outcome` with 404 on unknown timestamp
- [x] Fixed Gemma 4 empty content bug on Ollama by bypassing openai client, setting `{"think": False}` in generation options, and extracting via a robust fallback chain in `src/reasoning/gemma_client.py`.
- [x] Shortened regime classifier prompt to stay within token limits.
- [x] `frontend/` — React + Vite + TypeScript dashboard with Tailwind CSS (4 panels: Signal, Accuracy, Analogs, Explanation)
- [x] `frontend/README.md` — dashboard setup and usage guide
- [x] Root `README.md` updated with Frontend section
- [x] Hotfix: 3 agent runtime errors resolved
  - `SectorRotationAgent`: replaced missing `get_kite` with correct `get_client`; wrapped `collect()` in try/except for graceful degradation
  - `OptionsChainAgent`: robust warm-up headers, full try/except fallback with `available` flag, fixed max_pain comment
  - `MarketBreadthAgent`: multi-endpoint fallback, Content-Type check, `isinstance` guard for string items, `available` flag
  - `GlobalMarketAgent`: replaced per-ticker loop with batch `yf.download` + exponential backoff (3 attempts)

---

## In Progress
- `task_006` - multi-agent orchestrator foundation [Codex]

---

## Blocked / Issues
- `tests/api/test_server.py::test_candles_endpoint_returns_200` — pre-existing failure (candles table not initialised in test DB, unrelated to agent hotfix)

---

## Up Next
- [x] L0: Gemini dual-key routing ✅ merged PR #31
- [ ] L1: Scheduler + 7-key expansion + agent scaffold — open PR #32
- [x] L2: Macro Signal Agents ✅ merged (9 agents, parallel execution)
- [x] L3: 15-min intraday data ✅ merged PR #35
    - intraday_candles table seeded
    - dual resolution mode active
    - outcomes resolve every 75 minutes
    - RL updater learns 35x faster
- [x] L4: RL Weight Updater ✅ merged
    - Per-agent accuracy tracked (7d + 30d windows)
    - Weights update every Sunday at 00:00 IST
    - Live weights loaded into _weighted_fallback on every cycle
    - /api/agents/stats endpoint live
- [x] `task_007` - Feedback loop implemented
- [x] `task_008` - RL weight updater
- [ ] `task_010` - Gemma reasoning layer
- [x] `task_011` - Analog agent integration

---

## Ollama Setup Status
- [x] Ollama installed on dev machine
- [x] `gemma4:2b` pulled (~9.6 GB)
- [ ] `gemma4:26b` pulled (~19 GB, optional, needs GPU)
- [x] `ollama serve` running in background

---

## Branch Status
| Branch | Status | PR |
| --- | --- | --- |
| `main` | Clean | - |
| `feature/backtesting-engine` | `task_005` complete (backtesting engine) | pending |
| `feature/tests-backtest-edge-cases` | `task_005.1` complete (backtest engine edge case tests) | pending |
| `work` | `task_006` foundation (orchestrator agent scaffold + tests) | pending |
| `fix/gemma4-ollama-empty-response` | `task` fix empty content bug from Ollama API | pending |
| `feature/feedback-loop` | `task_007` complete (feedback loop to resolve predictions) | pending |
| `feature/dashboard-v1` | React dashboard with 4 premium panels | pending |
| `feature/gemini-dual-key-routing` | implemented Gemini dual key routing | pending |

---

## Monthly Cost Tracker
| Tool | Cost |
| --- | --- |
| Kite Connect | Rs500 |
<!-- | Claude Code (Pro) | Rs1,670 | -->
| OpenAI Codex | Rs0 |
| Jules | Rs0 |
| Gemma 4 (Ollama) | Rs0 |
| Gemini API | Rs0 |
| **Total** | **Rs500** |
