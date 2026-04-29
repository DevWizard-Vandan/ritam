# RITAM - Project Status
# Last Updated: April 29, 2026 - v2 documentation realignment
# Updating Agent: Codex

---

## Current State

RITAM v2 has been refactored from a prediction-only system into an intraday paper-trading evaluation system.

Active flow:

```text
Data -> Agents -> Aggregator Prediction -> TradeGate -> Paper Execution or Skip -> Expectancy Tracking -> Evaluation Metrics
```

The system is in launch/evaluation preparation state. Strategy thresholds are frozen. The next operational goal is clean 4-week paper-trading evidence, not optimization.

---

## Completed

### Core Intelligence

- [x] 9-agent architecture implemented
- [x] Gemini 2.5 Flash 7-key rotation implemented
- [x] Gemini Flash-Lite quick reasoning path available
- [x] FinBERT sentiment pipeline implemented
- [x] Regime classifier implemented
- [x] Analog finder supports daily and intraday 15-minute analogs
- [x] Aggregator fuses agent outputs
- [x] Prediction output format governed by ADR-005

### Data Pipeline

- [x] Kite Connect client path implemented
- [x] yfinance fallback implemented for local/dev resilience
- [x] Intraday candle seeding/sync implemented
- [x] NewsAPI + RSS ingestion implemented
- [x] NSE PCR fetcher implemented with browser headers, retries, TTL cache, and stale detection
- [x] Data freshness health check implemented in `src/data/market_health.py`
- [x] `/api/data/health` endpoint implemented

### Trading Layer

- [x] `src/trading/trade_gate.py` implemented
- [x] Valid trading regimes explicitly defined: `trending_up`, `trending_down`
- [x] Restricted trade windows enforced: 09:15-09:30 IST and 15:00-15:30 IST
- [x] Confidence threshold frozen at `0.65`
- [x] PCR neutral/penalty/extreme handling deterministic
- [x] Structured TradeGate output with `decision`, `reason_code`, `reason`, `signal`, and `details`
- [x] `src/orchestrator/agent.py` routes `Agents -> TradeGate -> Execution or Skip`
- [x] TradeGate does not modify agent logic

### Paper Execution and Tracking

- [x] Local `PaperTradingEngine` implemented
- [x] Virtual execution only; no live broker order placement
- [x] `PerformanceTracker` persists trades and NO_TRADE decisions
- [x] Trade journal includes trade ID, timestamp, signal, confidence, regime, PCR, decision, P&L, and equity-after
- [x] Expectancy, win rate, average win/loss, daily metrics, and drawdown calculated
- [x] NO_TRADE logging sampled/aggregated to avoid excessive log volume

### Evaluation Mode

- [x] `src/trading/evaluation_config.py` created with frozen constants
- [x] `NO_TWEAK_MODE = True`
- [x] `MAX_TRADES_PER_DAY = 3` safety warning implemented
- [x] PCR unavailable-too-long guard implemented
- [x] `get_system_metrics()` implemented
- [x] `generate_daily_summary()` implemented
- [x] `export_trade_log()` implemented
- [x] `validate_system_ready()` implemented
- [x] First-run marker records evaluation start date and starting equity
- [x] Startup summary logging implemented
- [x] Daily summary snapshot logging implemented
- [x] `daily_metrics` and `evaluation_state` persistence implemented

### API and Runtime

- [x] FastAPI server implemented
- [x] APScheduler integration implemented
- [x] WebSocket prediction stream implemented
- [x] Evaluation endpoints implemented:
  - [x] `GET /api/evaluation/metrics`
  - [x] `GET /api/evaluation/trades`
  - [x] `GET /api/evaluation/daily/latest`
  - [x] `POST /api/evaluation/daily-summary/run`
- [x] Paper endpoints implemented:
  - [x] `GET /api/paper/trades`
  - [x] `GET /api/paper/stats`
- [x] Scheduler status endpoint implemented
- [x] Render/startup hardening added so optional external readiness checks do not crash startup

### Dashboard and Supporting Layers

- [x] React + Vite + TypeScript frontend exists
- [x] Signal, accuracy, analog, explanation, agent weights, chart, and sandbox UI components exist
- [x] Backtest engine exists
- [x] RL environment/trainer exists
- [x] Weekly RL weight updater exists

### Documentation

- [x] `AGENTS.md` realigned to current trading/evaluation architecture
- [x] `README.md` realigned to current runtime flow and endpoints
- [x] `DECISIONS.md` updated with trading/evaluation ADRs
- [x] `DEPLOY.md` expanded for local/evaluation/deployment operations
- [x] `STATUS.md` updated for v2 paper-trading evaluation state

---

## Frozen Evaluation Constants

| Constant | Value |
|---|---:|
| `CONFIDENCE_THRESHOLD` | `0.65` |
| `PCR_BANDS` | `(0.8, 1.3)` |
| `NO_TWEAK_MODE` | `True` |
| `MAX_TRADES_PER_DAY` | `3` |
| `PCR_UNAVAILABLE_MAX_MINUTES` | `30` |
| `SUMMARY_EVERY_N_CYCLES` | `5` |

Do not change these during the 4-week evaluation unless the system is formally stopped for a safety incident.

---

## Layer Status

| Layer | Name | Status |
|---|---|---|
| Core | 9 agents + orchestrator + Gemini brain | Done |
| L0 | Gemini 7-key rotation | Done |
| L1 | Auto-scheduler | Done |
| L2 | 9 macro/market agents | Done |
| L3 | 15-minute intraday analog finder | Done |
| L4 | RL weight updater | Done |
| L5 | Paper trading engine | Done |
| L6 | Signal quality + backtesting | Done |
| L7 | Live prediction dashboard | Done/iterating |
| L8 | Sandbox - What If Time Machine | Frontend complete / backend present |
| Trading v2 | TradeGate + PCR + expectancy | Done |
| Evaluation | Metrics + daily summary + safeguards | Done |
| Launch | Data health + readiness checks | Done |

---

## Current Operational Mode

- Backend: FastAPI + scheduler + WebSocket
- Execution: paper trading only
- Data: Kite preferred, yfinance fallback available
- News: NewsAPI + RSS fallback
- PCR: NSE option-chain endpoint
- Storage: SQLite locally; PostgreSQL-compatible helpers for deployment path
- Monitoring: API/logs first, dashboard optional

---

## Essential Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /health` | API health |
| `GET /api/scheduler/status` | Scheduler active state |
| `GET /api/data/health` | Live/cached data freshness |
| `GET /api/evaluation/metrics` | Evaluation metrics snapshot |
| `GET /api/evaluation/daily/latest` | Latest daily summary |
| `GET /api/evaluation/trades` | Trade journal export |
| `GET /api/paper/trades` | Paper trade list |
| `GET /api/paper/stats` | Paper engine statistics |
| `WS /ws/predictions` | Live prediction stream |

---

## Known Constraints

- No live broker order placement is implemented or intended during evaluation.
- yfinance fallback may be delayed and should not be treated as equal to Kite for live evaluation.
- NSE PCR may occasionally fail; stale/unavailable state is explicitly surfaced.
- 4-week evaluation requires discipline: no threshold tuning, no new signals, no strategy changes.
- Some older docs/tasks may reference prediction-only architecture and should be treated as historical unless updated.

---

## Blocked / Issues

- None currently blocking v2 documentation alignment.

---

## Next Actions

1. Run final pre-market launch checklist before Day 1.
2. Confirm `/api/data/health` is `OK` during live market hours.
3. Confirm `/api/evaluation/metrics` returns initialized state.
4. Observe Day 1 without changing code or thresholds.
5. Review daily summary and trade journal after market close.

---

## Monthly Cost Tracker

| Tool | Cost |
|---|---:|
| Kite Connect | Rs500 |
| Gemini API via free-tier key rotation | Rs0 |
| Local FinBERT | Rs0 |
| SQLite local evaluation | Rs0 |
| Jules / Copilot / Codex | Rs0 |
| Total | Rs500 |

---

## Branch Status

| Branch | Status |
|---|---|
| `main` | Documentation realigned for RITAM v2 evaluation mode |
