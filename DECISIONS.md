# Architecture Decision Records (DECISIONS.md)
# Read before structural changes.
# Existing ADRs are retained; new ADRs are appended.

---

## ADR-001: Database - SQLite (Dev) to PostgreSQL-Compatible Production Path

- Decision: Use SQLite locally during development and evaluation. Keep DB helpers PostgreSQL-compatible for deployment.
- Reason: SQLite is simple and reliable for local paper evaluation. PostgreSQL handles production concurrency later.
- Date: Project start, reaffirmed Apr 2026.
- Do not change without discussion.

---

## ADR-002: Sentiment Model - FinBERT Local Cache

- Decision: Use ProsusAI/finbert from HuggingFace, downloaded and cached locally.
- Reason: No per-call API cost, works offline during market hours, purpose-built for financial text.
- Alternative rejected: paid general LLM calls for every headline.
- Date: Project start.

---

## ADR-003: Backtesting Framework - Backtrader

- Decision: Use Backtrader for historical backtesting.
- Reason: Event-driven testing helps avoid look-ahead bias.
- Alternatives rejected: Zipline due maintenance risk; vectorized-only approaches due look-ahead risk.
- Date: Project start.

---

## ADR-004: Agent Framework - Custom Async Parallelism

- Decision: Use custom parallel execution via asyncio/FastAPI instead of LangGraph.
- Reason: 9 agents run every cycle and direct asyncio gives control with less framework overhead.
- Date: v2 architecture.

---

## ADR-005: Prediction Output Format

- Decision: Every prediction output must preserve this schema:

```python
{
    "timestamp": "2026-04-15T15:30:00+05:30",
    "predicted_direction": "up",  # up / down / neutral
    "predicted_move_pct": 0.42,
    "confidence": 0.74,
    "timeframe_minutes": 15,
    "signals_used": ["sentiment", "fii_derivative", "options_chain", "macro", "analog"],
    "regime": "trending_up"
}
```

- Reason: Standardized prediction records allow scoring, comparison, and feedback loops.
- Date: Project start.
- Do not change without a migration plan.

---

## ADR-006: Error Scoring - 3-Dimensional

- Decision: Score prediction errors by direction correctness, magnitude error, and timing error.
- Reason: Specific error attribution is more useful than a generic wrong/right label.
- Date: Project start.

---

## ADR-007: Market Hours and Timestamps - IST

- Decision: Store and process market timestamps in IST (`Asia/Kolkata`).
- Reason: Avoid DST confusion and align with NSE/BSE market hours.
- Date: Project start.

---

## ADR-008: Local LLM - Superseded by ADR-013

- Original decision: Use Gemma through Ollama as local primary LLM.
- Status: Superseded.
- Date: v2 architecture original.

---

## ADR-009: Dashboard Stack - React + Vite + TypeScript + Tailwind

- Decision: Frontend uses React, Vite, TypeScript, and Tailwind. Backend streams through FastAPI WebSocket.
- Reason: Web-first delivery, fast development, simple Vercel deployment path.
- WebSocket endpoint: `ws://localhost:8000/ws/predictions`.
- Date: v2 architecture, updated Apr 2026.

---

## ADR-010: AnalogAgent - Intraday 15-Minute Windows

- Decision: AnalogAgent uses `find_intraday_analogs()` with 20-candle windows and 5-candle outcomes when enough intraday data exists. Falls back to daily analogs otherwise.
- Reason: Intraday resolution provides more feedback and more relevant short-horizon matches.
- Date: L3 completion, Apr 2026.

---

## ADR-011: RL Weight Update Schedule - Sunday 00:00 IST

- Decision: PPO weight update fires every Sunday at 00:00 IST through APScheduler.
- Reason: Weekly cadence balances learning with operational stability and avoids mid-market changes.
- Date: L4 completion, Apr 2026.

---

## ADR-012: Production Database - PostgreSQL, Not TimescaleDB

- Decision: Use PostgreSQL for production deployment path rather than TimescaleDB.
- Reason: Current data volume and query patterns do not justify TimescaleDB operational complexity.
- Date: Apr 2026.

---

## ADR-013: Primary LLM - Gemini 2.5 Flash with 7-Key Rotation

- Decision: Gemini 2.5 Flash is the primary reasoning LLM. Gemini Flash-Lite handles quick reasoning. Gemma/Ollama is removed from the active stack.
- Reason: 7-key rotation gives enough throughput with lower operational complexity than local model hosting.
- Date: Apr 2026.

---

## ADR-014: Paper Trading - Local Virtual Engine

- Decision: Use a local `PaperTradingEngine` instead of broker-side paper trading.
- Reason: Local execution is deterministic, testable, and keeps evaluation independent of broker paper-mode limitations.
- Trade size: configured through `PAPER_LOT_SIZE`.
- Starting capital: configured through `PAPER_CAPITAL`.
- Date: L5, Apr 2026.

---

## ADR-015: TradeGate - Deterministic Decision Layer Before Execution

- Decision: Insert `TradeGate` between agent prediction and paper execution.
- Runtime flow: `Agents -> Aggregator -> TradeGate -> Paper Execution or Skip`.
- Reason: Predictions are not trades. A deterministic gate is required to enforce regime, time, confidence, and PCR discipline.
- TradeGate output must include `decision`, `reason_code`, `reason`, `signal`, and `details`.
- Date: Apr 2026.

---

## ADR-016: Valid Trading Regimes - Explicit Trending Regimes Only

- Decision: TradeGate only considers `trending_up` and `trending_down` valid trading regimes.
- Reason: Avoid implicit substring checks and prevent trades in ranging, crisis, recovery, or undefined regimes.
- Date: Apr 2026.

---

## ADR-017: PCR Integration - NSE Option Chain with Deterministic Handling

- Decision: Fetch Nifty PCR from NSE option-chain data using total PE OI divided by total CE OI.
- Requirements: browser-like headers, cookie warmup, retry logic, TTL cache, stale detection, and explicit fallback behavior.
- Decision rule: neutral PCR allows confidence unchanged; outer bands apply deterministic confidence penalty; extreme PCR blocks trading.
- Reason: PCR is market-structure context, not a new predictive model. It must be deterministic and auditable.
- Date: Apr 2026.

---

## ADR-018: Evaluation Mode - Frozen Configuration for 4 Weeks

- Decision: Evaluation mode freezes strategy parameters for a 4-week paper run.
- Frozen constants: confidence threshold `0.65`, PCR neutral band `(0.8, 1.3)`, max trades/day `3`, no-tweak mode enabled.
- Reason: Premature tuning destroys evidence quality and creates overfitting risk.
- Date: Apr 2026.

---

## ADR-019: Expectancy Tracking - SQLite Trade Journal and Daily Metrics

- Decision: Persist trades, NO_TRADE decisions, equity-after, daily summaries, and evaluation state in SQLite.
- Required trade fields: trade ID, timestamp, signal, confidence, regime, PCR value, decision, profit/loss, and cumulative equity.
- Reason: The system must be measurable. Profitability claims require trade-level auditability and daily metrics.
- Date: Apr 2026.

---

## ADR-020: Data Freshness - Explicit Health Check Before Trusting Runtime Decisions

- Decision: Expose `check_data_freshness()` and `/api/data/health` to report source, last candle timestamp, delay, and OK/STALE status.
- Reason: A correct strategy running on stale data is still unsafe. Data freshness must be observable.
- Date: Apr 2026.

---

## ADR-021: Live Evaluation Execution - Paper Only

- Decision: Current evaluation mode must not place live broker orders.
- Reason: The system is still collecting 4-week evidence. Broker execution belongs after evaluation, risk review, and explicit approval.
- Date: Apr 2026.
