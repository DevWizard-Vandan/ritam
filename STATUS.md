# RITAM - Project Status
# Last Updated: April 15, 2026 - L4 RL Weight Updater live, L5–L9 roadmap corrected
# Updating Agent: Vandan

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
- [x] L0: Gemini 7-key routing ✅ merged PR #31
- [x] L1: Auto-Scheduler ✅ APScheduler every 5 min, built into server lifespan
- [x] L2: Macro Signal Agents ✅ 9 agents, parallel execution
- [x] L3: 15-min Intraday ⚠️ 80% — Issue #43 assigned to Jules
  - `intraday_candles` table seeded from Kite (15-min OHLCV)
  - `src/data/intraday_seeder.py` — incremental sync, runs on server startup
  - `src/learning/intraday_resolver.py` — resolves predictions after 5 candles (75 min), sets `resolved=1` and `signal`
  - `src/learning/weight_updater.py` — RL weight update every Sunday
  - **Missing**: `find_intraday_analogs()` in `analog_finder.py` — Jules on Issue #43
    - Must use `read_intraday_candles()` with 20-candle windows, 5-candle outcomes
    - `AnalogAgent` needs fallback: intraday if ≥20 candles available, else daily
- [x] L4: RL Weight Updater ✅ merged PR #41
  - Per-agent accuracy tracked (7d + 30d windows)
  - Weights update every Sunday at 00:00 IST (first run: Apr 19, 2026)
  - Live weights loaded into `_weighted_fallback` on every cycle
  - `/api/agents/stats`, `/api/weights/history`, `/api/weights/update` endpoints live
  - 25 candles synced today, 17 predictions resolved with outcomes

---

## In Progress
- Issue #43 — Jules working on L3 completion (`find_intraday_analogs()`). PR incoming.
- PR #42 — Copilot working on Live Dashboard wiring (React frontend → live backend). Maps to **L7** in corrected plan. Review carefully before merging — do NOT let it block L5 Paper Trading.

---

## Blocked / Issues
- `tests/api/test_server.py::test_candles_endpoint_returns_200` — pre-existing failure (candles table not initialised in test DB)

---

## Up Next

### Pending Layers (Corrected Definitions — Apr 15, 2026)

- [x] **L5: Paper Trading Engine**
    - Wire BUY/SELL/HOLD signal → Zerodha paper trading (no real money)
    - Track P&L, Sharpe ratio, win-rate separately from prediction accuracy
    - Builds a verifiable live track record
    - Use Kite's paper trading mode or simulate with a local engine tracking virtual positions
    - Assign to Jules or Copilot after Issue #43 PR merges

- [ ] **L6: Signal Quality + Backtesting**
    - Run 3-month historical backtest on stored predictions + outcomes
    - Compare RL-weighted agent accuracy vs equal-weight baseline
    - Output: win rate, Sharpe ratio, drawdown, equity curve
    - Report saved to `reports/backtest_YYYY-MM-DD.html`
    - Walk-forward validation (re-weight weekly, test next week)

- [ ] **L7: Live Prediction Chart Dashboard**
    - Full React dashboard: live Nifty 50 candlestick + RITAM prediction zone overlay
    - 9 agent signal bars with live weights, accuracy tracker
    - WebSocket real-time updates
    - Deploy locally at `localhost:5173`. Stretch: Vercel deploy
    - PR #42 is a head start on this layer

- [ ] **L8: Invite-Only Deploy**
    - Docker + `docker-compose up` starts API + frontend + scheduler
    - Deploy API to Fly.io, frontend to Vercel
    - Migrate SQLite → PostgreSQL
    - Auth layer (invite-only)
    - `/health` endpoint with DB ping + last cycle timestamp
    - Sentry/Logfire error tracking

- [ ] **L9: Public + Pricing**
    - Stripe integration
    - User tiers: free = delayed signals, paid = live
    - Public launch

---

## Task Tracker
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
