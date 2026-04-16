# Architecture Decision Records (DECISIONS.md)
# READ BEFORE MAKING ANY STRUCTURAL CHANGES
# Add a new entry every time a major technical decision is made.
# NEVER modify or delete existing ADRs.

---

## ADR-001: Database — SQLite (Dev) → PostgreSQL (Production)
- **Decision:** Use SQLite locally during development. Migrate to PostgreSQL at L8 deploy.
- **Reason:** Zero setup for development. PostgreSQL handles concurrent connections and scale in production.
- **Note:** Originally planned TimescaleDB — simplified to PostgreSQL (ADR-012).
- **Date:** Project start
- **DO NOT change without discussion.**

---

## ADR-002: Sentiment Model — FinBERT Local Cache
- **Decision:** Use ProsusAI/finbert from HuggingFace, downloaded and cached locally.
- **Reason:** No per-call API cost, works offline during Indian market hours, purpose-built for financial text.
- **Alternative rejected:** OpenAI GPT-4o API (too expensive per call at scale, latency too high for real-time)
- **Date:** Project start

---

## ADR-003: Backtesting Framework — Backtrader
- **Decision:** Use Backtrader for all backtesting.
- **Reason:** Actively maintained, event-driven (not vectorized), prevents look-ahead bias, free.
- **Alternative rejected:** Zipline (poorly maintained), VectorBT (vectorized = look-ahead risk)
- **Date:** Project start

---

## ADR-004: Agent Framework — Custom Parallel (asyncio)
- **Decision:** Use custom parallel execution via asyncio/FastAPI, not LangGraph.
- **Reason:** 9 agents run in parallel every 5 minutes. Direct asyncio gives full control, no framework overhead.
- **Original decision:** LangGraph — superseded by actual implementation.
- **Date:** v2 architecture

---

## ADR-005: Prediction Output Format
- **Decision:** Every prediction output must be a dict with this exact schema:
```python
{
  "timestamp": "2026-04-15T15:30:00+05:30",  # IST
  "predicted_direction": "up" | "down" | "neutral",
  "predicted_move_pct": 0.42,
  "confidence": 0.74,
  "timeframe_minutes": 15,
  "signals_used": ["sentiment", "fii_derivative", "options_chain", "macro", "analog"],
  "regime": "trending_up" | "crisis" | "ranging" | "recovery"
}
```
- **Reason:** Standardized output allows consistent error scoring and model comparison.
- **Date:** Project start

---

## ADR-006: Error Scoring — 3-Dimensional
- **Decision:** Every prediction error is scored across 3 dimensions:
  1. `direction_correct` (bool) — did we predict up/down correctly?
  2. `magnitude_error` (float) — how far off was the % move prediction?
  3. `timing_error` (int minutes) — how far off was the timing?
- **Reason:** Generic "you were wrong" teaches nothing. Specific error attribution enables targeted learning.
- **Date:** Project start

---

## ADR-007: Market Hours — IST
- **Decision:** All timestamps stored and processed in IST (Asia/Kolkata, UTC+5:30).
- **Reason:** Avoids DST confusion, aligns with NSE/BSE market hours (9:15 AM – 3:30 PM IST).
- **Date:** Project start

---

## ADR-008: Local LLM — SUPERSEDED by ADR-013
- **Original decision:** Gemma 4 via Ollama as primary local LLM.
- **Status:** Superseded. See ADR-013.
- **Date:** v2 architecture (original)

---

## ADR-009: Dashboard Stack — React + Vite + TypeScript + Tailwind
- **Decision:** Frontend = React + Vite + TypeScript + Tailwind CSS. Backend = FastAPI WebSocket.
- **Reason:** FastAPI streams live predictions every 5 minutes with minimal latency.
  React chosen over Flutter for web-first delivery and easier Vercel deployment.
- **Original decision:** Flutter Web — superseded by actual implementation.
- **WebSocket endpoint:** ws://localhost:8000/ws/predictions
- **Chart library:** TradingView Lightweight Charts or Recharts (L7)
- **Animations:** Framer Motion (L7)
- **Date:** v2 architecture (updated Apr 2026)

---

## ADR-010: AnalogAgent — Intraday 15-min Windows (20 candles)
- **Decision:** AnalogAgent uses `find_intraday_analogs()` with 20-candle windows and 5-candle outcomes when ≥20 intraday candles are available. Falls back to daily `find_analogs()` otherwise.
- **Reason:** 15-min resolution gives 35x more training signal per day vs daily candles. Faster RL learning.
- **Output key:** `next_5candle_return` (not `next_5day_return`) to distinguish intraday from daily.
- **Date:** L3 completion (Apr 2026)

---

## ADR-011: RL Weight Update Schedule — Sunday 00:00 IST
- **Decision:** PPO weight update fires every Sunday at 00:00 IST via APScheduler.
- **Reason:** Weekly cadence balances learning speed vs stability. Weekend update avoids mid-market disruption.
- **Emergency recalibration (future):** Trigger early weight update if 3 consecutive wrong calls detected.
- **Date:** L4 completion (Apr 2026)

---

## ADR-012: Production Database — PostgreSQL (not TimescaleDB)
- **Decision:** Migrate from SQLite to PostgreSQL at L8, not TimescaleDB.
- **Reason:** TimescaleDB adds operational complexity with marginal benefit at our data volume.
  PostgreSQL with a `timestamp` index is sufficient for RITAM's query patterns.
- **Migration target:** L8 Invite-Only Deploy.
- **Date:** Apr 2026

---

## ADR-013: Primary LLM — Gemini 2.5 Flash (7-Key Rotation), Gemma Removed
- **Decision:** Gemini 2.5 Flash is the primary reasoning LLM. Gemma/Ollama fully removed from the stack.
- **Reason:** 7 Google account API keys with round-robin fallback gives effectively unlimited free throughput — exceeds paid tier capacity. Local Gemma setup added operational complexity (Ollama server, GPU memory, model pulls) with no cost benefit given the free Gemini throughput available.
- **Key rotation:** key_1 → key_2 → ... → key_7 → key_1. On rate limit or failure, immediately falls back to next key.
- **Quick reasoning:** Gemini Flash-Lite for fast/cheap calls. Gemini 2.5 Flash for deep reasoning.
- **Scalability:** Can add another 7 keys (14 total) if throughput needs grow.
- **Alternative rejected:** Gemma 4 via Ollama (removed), OpenAI GPT-4o (paid, unnecessary)
- **Date:** Apr 2026

---

## ADR-014: Paper Trading — Local Virtual Engine (not Zerodha Paper Mode)
- **Decision:** Implement a local `PaperTradingEngine` class tracking virtual positions in SQLite, not Zerodha's paper trading mode.
- **Reason:** Zerodha paper trading requires broker-side setup and has API limitations. Local engine gives full control over position logic, P&L calculation, and Sharpe ratio tracking. Deterministic and testable.
- **Trade size:** 1 lot = 50 units (Nifty standard). Configurable via `settings.PAPER_LOT_SIZE`.
- **Starting capital:** 100,000 INR. Configurable via `settings.PAPER_CAPITAL`.
- **One position at a time:** No pyramiding.
- **Date:** L5 (Apr 2026)
