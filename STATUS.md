# RITAM - Project Status
# Last Updated: April 11, 2026 - prediction feedback tracker added
# Updating Agent: Codex (work)

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
- [x] `src/data/kite_client.py` - Kite-compatible client implemented with yfinance (`^NSEI` / `^NSEBANK`)
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

---

## In Progress
- `task_006` - multi-agent orchestrator foundation [Codex]

---

## Blocked / Issues
- None

---

## Up Next
1. `task_007` - Feedback loop [Claude Code]
2. `task_008` - RL weight updater [Claude Code]
3. `task_010` - Gemma reasoning layer (after Ollama installed) [Claude Code]
4. `task_011` - Analog agent integration [Claude Code]

---

## Ollama Setup Status
- [ ] Ollama installed on dev machine
- [ ] `gemma4:2b` pulled (~2.5 GB)
- [ ] `gemma4:26b` pulled (~15 GB, optional, needs GPU)
- [ ] `ollama serve` running in background

---

## Branch Status
| Branch | Status | PR |
| --- | --- | --- |
| `main` | Clean | - |
| `feature/backtesting-engine` | `task_005` complete (backtesting engine) | pending |
| `feature/tests-backtest-edge-cases` | `task_005.1` complete (backtest engine edge case tests) | pending |
| `work` | `task_006` foundation (orchestrator agent scaffold + tests) | pending |

---

## Monthly Cost Tracker
| Tool | Cost |
| --- | --- |
| Kite Connect | Rs500 |
| Claude Code (Pro) | Rs1,670 |
| OpenAI Codex | Rs1,670 |
| Jules | Rs0 |
| Gemma 4 (Ollama) | Rs0 |
| Gemini API | Rs0 |
| **Total** | **Rs3,840** |
