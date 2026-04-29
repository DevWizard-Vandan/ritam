# RITAM - Master Project Context (AGENTS.md)
# Ritam - the truth-order beneath market movement
# Read this first before making project changes.

---

## Current Product State

RITAM v2 is no longer only a market prediction engine. It is now a disciplined intraday paper-trading evaluation system for Nifty 50 options direction.

Current runtime flow:

```text
Live/Cached Data -> 9 Agents -> Aggregator Prediction -> TradeGate -> Paper Execution or Skip -> Expectancy Tracking -> Evaluation Metrics
```

The agents still produce market intelligence. TradeGate decides whether that intelligence is tradable. PerformanceTracker decides whether the system is improving or failing.

Primary operating mode right now: 4-week paper-trading evaluation with frozen configuration and no tuning during the run.

---

## Locked Evaluation Criteria

These criteria are fixed and must not be edited during the 4-week evaluation:

| Metric | Required Threshold |
|---|---:|
| Expectancy | greater than Rs0.50 per Rs1 risked |
| Win rate | greater than 45% |
| Max daily drawdown | less than 5% |
| Max total drawdown | less than 15% |
| Evaluation duration | 4 weeks |
| Parameter tuning | Not allowed during evaluation |

Evaluation config is frozen in `src/trading/evaluation_config.py`:

```python
CONFIDENCE_THRESHOLD = 0.65
PCR_BANDS = (0.8, 1.3)
NO_TWEAK_MODE = True
MAX_TRADES_PER_DAY = 3
PCR_UNAVAILABLE_MAX_MINUTES = 30
SUMMARY_EVERY_N_CYCLES = 5
```

---

## Architecture - RITAM v2 Trading Evaluation Spine

```text
Layer 1: Data Perception
- Zerodha Kite Connect for live/intraday candles when credentials are available
- yfinance fallback for local/dev resilience
- NewsAPI + RSS for market headlines
- NSE option-chain endpoint for Nifty PCR
- SQLite locally, PostgreSQL-compatible path for deployment

Layer 2: Reasoning and Agents
- Gemini 2.5 Flash is the primary reasoning LLM through 7-key rotation
- Gemini Flash-Lite is used for quick/cheap reasoning tasks
- FinBERT scores financial headline sentiment locally
- 9 agents produce regime, analog, macro, sentiment, breadth, options, sector, FII, and global signals

Layer 3: Prediction and Aggregation
- Agent outputs are fused by the aggregator into direction/confidence/regime/analog context
- Prediction output format remains governed by ADR-005

Layer 4: TradeGate
- Deterministic decision layer in `src/trading/trade_gate.py`
- Allows trades only for `trending_up` or `trending_down`
- Blocks restricted windows: 09:15-09:30 IST and 15:00-15:30 IST
- Blocks confidence below 0.65 after PCR adjustment
- Uses PCR neutral/penalty/extreme bands without changing strategy mid-run

Layer 5: Paper Execution and Evaluation
- `src/paper_trading/engine.py` handles virtual positions only
- `src/trading/performance_tracker.py` persists trades and NO_TRADE decisions
- `src/trading/evaluation_mode.py` exposes metrics, daily summaries, trade export, readiness checks, and safeguards
- Evaluation endpoints are served through FastAPI
```

---

## Decision Flow

```text
1. Scheduler or API starts a market cycle.
2. Data layer refreshes intraday candles/news where configured.
3. MarketOrchestrator runs the existing agents.
4. Aggregator creates prediction/confidence/regime.
5. TradeGate evaluates regime, time window, confidence, analog bias, and PCR.
6. If TRADE: paper engine opens/updates virtual execution only.
7. If NO_TRADE: decision is sampled/aggregated to avoid log spam.
8. PerformanceTracker records decisions, trades, equity, expectancy, and drawdown.
9. Evaluation endpoints expose live health and performance state.
```

Do not bypass TradeGate for paper trading.

---

## Key Modules

| Path | Responsibility |
|---|---|
| `src/orchestrator/agent.py` | Main cycle: agents -> TradeGate -> paper execution/skip |
| `src/trading/trade_gate.py` | Deterministic trade/no-trade decision engine |
| `src/trading/pcr_fetcher.py` | NSE Nifty PCR fetch, cache, retry, stale detection |
| `src/trading/performance_tracker.py` | SQLite trade journal, NO_TRADE logging, expectancy, drawdown |
| `src/trading/evaluation_mode.py` | Metrics API helpers, daily summary, readiness, first-run marker, safeguards |
| `src/trading/evaluation_config.py` | Frozen evaluation constants |
| `src/paper_trading/engine.py` | Local paper execution and virtual P&L |
| `src/data/market_health.py` | Candle and quote freshness diagnostics |
| `src/data/kite_client.py` | Kite client with yfinance-compatible fallback |
| `src/api/server.py` | FastAPI endpoints, scheduler, startup readiness logging |
| `src/data/db.py` | Core DB helpers |
| `src/data/db_eval_helpers.py` | Evaluation-specific DB helpers |

---

## Essential API Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /health` | Basic API health |
| `GET /api/scheduler/status` | Scheduler state |
| `GET /api/data/health` | Candle freshness and source status |
| `GET /api/evaluation/metrics` | Total trades, win rate, expectancy, drawdown, equity, NO_TRADE reasons |
| `GET /api/evaluation/daily/latest` | Latest daily evaluation summary |
| `GET /api/evaluation/trades` | Trade journal export |
| `POST /api/evaluation/daily-summary/run` | Manual daily summary generation |
| `GET /api/paper/trades` | Paper trade history |
| `GET /api/paper/stats` | Paper engine stats |
| `WS /ws/predictions` | Live prediction stream |

---

## Tech Stack

| Component | Tool / Library | Notes |
|---|---|---|
| Language | Python 3.11+ | Core backend |
| Market data | Zerodha Kite Connect v3 | Preferred live source |
| Market data fallback | yfinance | Local/dev fallback only; may be delayed |
| PCR | NSE option-chain endpoint | Cached/retried; stale state is explicit |
| Sentiment NLP | FinBERT | Local financial sentiment scoring |
| Primary LLM | Gemini 2.5 Flash | 7-key rotation |
| Quick LLM | Gemini Flash-Lite | Fast reasoning tasks |
| Agent framework | Custom asyncio/FastAPI | 9 agents in parallel |
| Paper execution | Local engine | No broker execution in evaluation mode |
| Performance tracking | SQLite | Trade log, NO_TRADE log, daily metrics, evaluation state |
| API | FastAPI + WebSockets | Backend-only observability plus dashboard support |
| Scheduler | APScheduler | 5-minute market cycles and EOD summary |
| Frontend | React + Vite + TypeScript + Tailwind | Dashboard |
| Backtesting | Backtrader | Signal quality/backtest layer |
| RL | Stable-Baselines3 PPO | Weekly agent weight updates |

---

## Runtime Modes

| Mode | Behavior |
|---|---|
| Local dev | SQLite, yfinance fallback allowed, API at localhost |
| Paper evaluation | Kite preferred, TradeGate active, paper execution only, config frozen |
| Dashboard | Frontend consumes API/WebSocket; trading logic remains backend-side |
| Production deploy | PostgreSQL-compatible path; secrets from deployment platform |

There is no live broker order placement in the current evaluation system.

---

## Non-Negotiable Rules

1. Never delete existing tests or working code.
2. Every new module must have a corresponding test file in `tests/`.
3. Always update `STATUS.md` after completing project work.
4. API keys and tokens go only in `.env` or deployment secrets. Never hardcode secrets.
5. Use `snake_case` for Python files and functions.
6. Branch naming: `feature/module-name` unless the active toolchain requires another prefix.
7. Do not modify `.env`.
8. Do not modify `AGENTS.md` or `DECISIONS.md` unless the project owner explicitly asks for a documentation/architecture update.
9. Read `STATUS.md` before starting work.
10. Read `DECISIONS.md` before structural or architectural changes.
11. If blocked, write the blocker in `STATUS.md` under Blocked and stop.
12. Gemini 2.5 Flash through `src/reasoning/gemini_client.py` remains the primary LLM path.
13. Gemini Flash-Lite is reserved for quick/fast reasoning tasks.
14. DB changes must be additive only. Do not drop tables or remove persisted data.
15. During evaluation mode, do not tune thresholds or add signals.
16. Do not change TradeGate/PCR logic during the 4-week evaluation unless the system is stopped for a safety incident.

---

## Prediction Output Format (ADR-005 - Do Not Change)

```python
{
    "timestamp": "2026-04-15T10:30:00+05:30",
    "predicted_direction": "up",
    "predicted_move_pct": 0.42,
    "confidence": 0.74,
    "timeframe_minutes": 15,
    "signals_used": ["sentiment", "fii_derivative", "options_chain", "macro", "analog"],
    "regime": "trending_up",
    "historical_analog": {
        "match": "March 2020 COVID bounce",
        "similarity": 0.73,
        "analog_outcome": "+8% over 10 sessions"
    }
}
```

---

## TradeGate Output Format

Every TradeGate decision must return:

```python
{
    "decision": "TRADE",
    "reason_code": "TRADE_ALLOWED",
    "reason": "Trade allowed by deterministic gate",
    "signal": "BUY_CALL",
    "details": {
        "regime": "trending_up",
        "confidence_original": 0.72,
        "confidence_adjusted": 0.72,
        "confidence_threshold": 0.65,
        "pcr_value": 1.04,
        "pcr_penalty": 0.0,
        "pcr_is_stale": False
    }
}
```

Reason codes are operational telemetry. Do not replace them with free-form-only strings.

---

## Definition of Done

- [ ] Core logic file written or documentation updated as requested
- [ ] Tests added for new code modules
- [ ] Relevant tests pass
- [ ] `STATUS.md` updated
- [ ] No hardcoded API keys or absolute local paths
- [ ] Errors handled gracefully: timeouts, empty inputs, API failures
- [ ] No strategy parameters changed during evaluation mode
- [ ] For DB work: additive migration only

---

## Current Operational Discipline

For the 4-week paper-trading evaluation:

- Observe, do not optimize.
- Record every TRADE and sampled/aggregated NO_TRADE reason.
- Use `/api/data/health` before trusting a trading day.
- Use `/api/evaluation/metrics` and `/api/evaluation/daily/latest` for monitoring.
- Treat one trade, one day, or one loss as noise unless it exposes a system fault.
- Stop only for safety or infrastructure failures, not for normal losing trades.
