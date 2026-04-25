# RITAM - Project Status
# Last Updated: April 25, 2026 — Evaluation mode launch-ready
# Updating Agent: Codex

---

## Vision
**"Not prediction. Perception."**
Self-improving multi-agent AI system for real-time Nifty 50 prediction.
9 specialist agents act as sensors. Gemini 2.5 Flash (7-key rotation) acts as the reasoning brain.
The system gets smarter every week via RL weight updates and grows its analog memory with every resolved prediction.

---

## Architecture Notes
- **LLM Brain:** Gemini 2.5 Flash (primary) + Gemini Flash-Lite (quick reasoning). Gemma/Ollama fully removed.
- **Key Rotation:** 7 Google account Gemini API keys with round-robin fallback â€” effectively unlimited free throughput, exceeds paid tier.
- **9 Agents:** FIIDerivativeAgent, OptionsChainAgent, SectorRotationAgent, MarketBreadthAgent, GlobalMarketAgent, SentimentAgent, RegimeClassifierAgent, AnalogAgent, MacroAgent â€” run in parallel every cycle.
- **Prediction cycle:** Every 5 minutes (reducible to 1-min in future â€” compute is not the bottleneck, only Kite API rate limits).
- **Self-improvement loops:**
  1. Weekly RL weight update (PPO, every Sunday 00:00 IST) â€” right agents get more voting power
  2. Analog memory growth â€” every resolved prediction adds to historical pattern library
  3. Gemini in-context learning â€” reasoning over recent prediction history + outcomes
- **Recalibration:** Currently weekly. Future: emergency re-weight on 3 consecutive wrong calls or regime flip.

---

## Completed
- [x] Project scaffold (v2 architecture)
- [x] `AGENTS.md` â€” full v2 vision and architecture
- [x] `DECISIONS.md` â€” 11 ADRs documented
- [x] `src/config/settings.py` â€” env loader + `PAPER_CAPITAL`, `PAPER_LOT_SIZE`
- [x] `src/data/kite_client.py` â€” Kite Connect + yfinance fallback
- [x] `src/data/db.py` â€” SQLite helpers (candles, intraday, news, predictions, agent weights, paper trades)
- [x] `src/data/kite_feed.py` â€” OHLCV fetcher with chunked date range seeding
- [x] `src/data/news_fetcher.py` â€” NewsAPI + RSS ingestion, APScheduler job, `news_raw` table
- [x] `src/data/intraday_seeder.py` â€” 15-min candle incremental sync, runs on server startup
- [x] `src/sentiment/preprocessor.py` â€” headline cleaner
- [x] `src/sentiment/scorer.py` â€” FinBERT scorer
- [x] `src/reasoning/analog_finder.py` â€” `find_analogs()` (daily) + `find_intraday_analogs()` (15-min, 20-candle window, 5-candle outcome)
- [x] `src/reasoning/regime_classifier.py` â€” Gemini-powered regime classifier
- [x] `src/agents/analog_agent.py` â€” intraday/daily fallback routing (â‰¥20 candles â†’ intraday, else daily)
- [x] `src/agents/aggregator.py` â€” master signal aggregator
- [x] `src/orchestrator/agent.py` â€” `MarketOrchestrator.run_cycle()` wired to PaperTradingEngine
- [x] `src/learning/intraday_resolver.py` â€” resolves predictions after 5 candles (75 min), sets `resolved=1` + `signal`
- [x] `src/learning/weight_updater.py` â€” RL weight update (Sunday 00:00 IST), normalize + clamp
- [x] `src/learning/accuracy_calculator.py` â€” per-agent 7d + 30d accuracy windows
- [x] `src/feedback/tracker.py` â€” prediction/outcome tracker, `feedback_predictions` table
- [x] `src/paper_trading/engine.py` â€” `PaperTradingEngine` class (open/close/get_stats), single position, no pyramiding
- [x] `paper_trades` DB table â€” signal, entry/exit price+time, P&L, outcome, Sharpe contribution
- [x] `src/api/server.py` â€” FastAPI + WebSocket + APScheduler + all endpoints incl. `/api/paper/trades` + `/api/paper/stats`
- [x] `src/api/websocket_manager.py` â€” WebSocket connection manager
- [x] `src/rl/trading_env.py` â€” Gymnasium `NiftyTradingEnv`
- [x] `src/rl/trainer.py` â€” PPO training pipeline
- [x] `src/backtest/engine.py` â€” Backtrader engine (SMA crossover baseline)
- [x] `config/agent_weights.json` â€” baseline equal weights (DB overrides on every cycle)
- [x] `frontend/` â€” React + Vite + TypeScript + Tailwind CSS dashboard
  - SignalPanel (WebSocket primary, 30s REST fallback, WS/REST badge)
  - AccuracyPanel (wired to `/api/feedback/accuracy`)
  - AnalogPanel, ExplanationPanel
  - AgentWeightsPanel (weight bars, 7d/30d accuracy, sorted by weight desc)
  - PredictionChart (lightweight-charts candlesticks, prediction zone, confidence meter, live regime badge)
  - `VITE_API_BASE_URL` env var â€” no hardcoded localhost
- [x] `frontend/.env.example` â€” environment config template
- [x] `frontend/` Sandbox UI â€” tab toggle, timeline slider + milestones, animated scenario chart, confidence bar, sandbox API integration
- [x] `frontend/` dashboard redesign â€” premium light theme, Inter typography, Framer Motion transitions, white chart surfaces, refreshed sandbox controls, and unified card styling
- [x] `frontend/` auth + settings enhancement â€” login page gate added, settings tab added, dark mode switch with local persistence, and logout flow to return to login
- [x] All agent runtime hotfixes (SectorRotation, OptionsChain, MarketBreadth, GlobalMarket)
- [x] `scripts/seed_historical.py`, `scripts/verify_db.py`, `scripts/seed_intraday.py`
- [x] Full test suite across all modules incl. `tests/paper_trading/test_engine.py`
- [x] PostgreSQL compatibility hotfixes â€” startup `init_db()` in API lifespan, cross-DB insert-ignore handling, `news_raw` partial dedup indexes, and positional `executemany` args for DB wrapper compatibility
- [x] `src/trading/` Phase 1 â€” deterministic `TradeGate`, NSE PCR fetcher with retries/cache, and SQLite `PerformanceTracker`
- [x] `tests/trading/` coverage for PCR caching/retries, trade gating, and expectancy/drawdown tracking
- [x] `src/orchestrator/agent.py` â€” TradeGate integration between synthesis and execution, with sampled `NO_TRADE` logging
- [x] `tests/orchestrator/test_trade_gate_integration.py` â€” verifies trade execution/skip wiring
- [x] `src/trading/` evaluation mode â€” metrics snapshot, daily summary generator, trade journal export, frozen evaluation config, and safety guardrails
- [x] `src/data/db.py` â€” `daily_metrics` table + SQLite-safe helpers for evaluation summaries
- [x] `src/api/server.py` â€” evaluation endpoints for metrics, trade export, and daily summary generation
- [x] `src/api/server.py` â€” data health endpoint for live candle freshness monitoring
- [x] `tests/trading/test_evaluation_mode.py` â€” evaluation metrics, daily summary, journal export, and safety guardrails
- [x] `src/data/market_health.py` + `tests/data/test_market_health.py` â€” freshness checks, live quote fallback, and stale-data detection
- [x] local import fallbacks â€” `psycopg2`, `sentry_sdk`, and `loguru` fallbacks added where needed for evaluation runtime
- [x] final launch checks â€” `validate_system_ready()`, first-run marker, startup summary log, and daily summary snapshot log

---

## Layer Status

| Layer | Name | Status | PR |
|---|---|---|---|
| Core | 9 Agents + Orchestrator + Gemini Brain | âœ… Done | â€” |
| L0 | Gemini 7-Key Rotation | âœ… Done | PR #31 |
| L1 | Auto-Scheduler (5-min cycles) | âœ… Done | â€” |
| L2 | 9 Macro Agents Parallel | âœ… Done | â€” |
| L3 | 15-min Intraday Analog Finder | âœ… Done | PR #44 |
| L4 | RL Weight Updater | âœ… Done | PR #41 |
| L5 | Paper Trading Engine | âœ… Done | PR #45 |
| L6 | Signal Quality + Backtesting | âœ… Done | Codex |
| L7 | Live Prediction Chart Dashboard | âœ… Done | Copilot |
| L8 | Sandbox â€” "What If" Time Machine | âœ… Frontend Complete | Copilot |
| L9 | Landing Page + Waitlist + Invite Deploy | âœ… Done | â€” |
| L10 | Public Pricing + Launch | â³ Pending | â€” |

---

## In Progress
- Nothing currently. Evaluation mode is wired and validated.

---

## Pending Layer Definitions

### L6 â€” Signal Quality + Backtesting *(Codex)*
- Run 3-month historical backtest on `feedback_predictions` where `resolved=1`
- Compare RL-weighted accuracy vs equal-weight baseline
- Metrics: win rate, Sharpe ratio, max drawdown, equity curve
- Report: `reports/backtest_YYYY-MM-DD.html` (self-contained, no CDN)
- Walk-forward validation: re-weight weekly, test next week
- CLI: `python scripts/run_backtest.py --from 2026-01-01 --to 2026-04-16`
- Endpoint: `GET /api/backtest/latest`

### L7 â€” Live Prediction Chart Dashboard *(Copilot â€” completed Apr 2026)*
- Full candlestick chart: live Nifty 50 OHLCV + RITAM prediction zone overlay
- Prediction moves 15 minutes ahead of market, continuously self-corrects
- Confidence meter (based on analog similarity scores)
- Pre-market prediction cycle at 9:00 AM using GIFT Nifty + global cues
- 9 agent signal bars with live RL weights
- Regime badge: `ðŸ”´ Crisis` / `ðŸŸ¡ Ranging` / `ðŸŸ¢ Trending Up`
- Event overlay toggle (historical: rate hikes, elections, wars)
- WebSocket real-time updates
- Stack: TradingView Lightweight Charts or Recharts, Framer Motion
- Color palette: `#0A0F1E` background, `#3B82F6` accents, green/red signals
- PR #42 is groundwork (panel wiring) â€” this layer builds the chart itself

### L8 â€” Sandbox: "What If" Time Machine *(Copilot + Vandan)*
- Timeline roller: user picks any date (e.g., "Jan 2008", "Mar 1962")
- Condition input: "What if RBI cuts rates by 1%" or "China attacked India"
- Condition parser: NLP â†’ structured event `{type, magnitude, date}`
- Scenario engine: overrides live data with hypothetical, runs analog + regime + macro
- Animated chart: replays predicted Nifty path frame by frame
- Portfolio simulator: user enters holdings, sees predicted impact
- Comparison mode: overlay 2008 crash vs current market
- Collaborative: multiple users add conditions simultaneously
- Export to PDF: scenario analysis download
- Build scenario list from early Discord user feedback â€” don't build blindly

### L9 â€” Landing Page + Waitlist + Invite-Only Deploy *(Vandan + Copilot)*
- Landing page structure:
  - Hero: "Predict the Market. Understand History." + animated Nifty chart
  - Demo video: 60-second sandbox screen recording
  - Waitlist: email + "What would you use this for?"
  - Discord invite: curated early users
- Discord channels: `#predictions` (auto-post daily signal), `#sandbox-demos`, `#feedback`
- Deploy: Docker + `docker-compose up` (API + frontend + scheduler)
- API â†’ Fly.io, Frontend â†’ Vercel
- Migrate SQLite â†’ PostgreSQL
- Auth layer (invite-only token)
- `/health` endpoint + Sentry/Logfire error tracking
- Stack: Next.js 14 (App Router) + Tailwind + Framer Motion for landing page

### L10 â€” Public Pricing + Launch *(Vandan)*
- Stripe integration
- Tiers: Free = delayed signals, Paid = live signals + sandbox access
- API access tier: developers query predictions programmatically
- Alert system: Telegram/WhatsApp notify on regime change or signal flip
- Public launch

---

## Blocked / Issues
- `tests/api/test_server.py::test_candles_endpoint_returns_200` â€” pre-existing failure (candles table not initialised in test DB, unrelated to main logic)

---

## Monthly Cost Tracker
| Tool | Cost |
|---|---|
| Kite Connect | Rs500 |
| Gemini API (7 keys, free tier) | Rs0 |
| Jules | Rs0 |
| Copilot | Rs0 |
| Codex | Rs0 |
| Ollama / Gemma | Removed |
| **Total** | **Rs500** |

---

## Branch Status
| Branch | Status | PR |
|---|---|---|
| `main` | Clean | â€” |

