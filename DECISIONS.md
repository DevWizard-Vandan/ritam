# Architecture Decision Records (DECISIONS.md)
# READ BEFORE MAKING ANY STRUCTURAL CHANGES
# Add a new entry every time a major technical decision is made.

---

## ADR-001: Database — SQLite (Dev) → TimescaleDB (Production)
- **Decision:** Use SQLite locally during development. Migrate to TimescaleDB on cloud at Phase 7.
- **Reason:** Zero setup for development, TimescaleDB handles time-series at scale in production.
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

## ADR-004: Agent Framework — LangGraph
- **Decision:** Use LangGraph for multi-agent orchestration.
- **Reason:** Supports parallel agent execution, state management, and conditional routing natively.
- **Alternative rejected:** CrewAI (less control over state), plain Python threads (no observability)
- **Date:** Project start

---

## ADR-005: Prediction Output Format
- **Decision:** Every prediction output must be a dict with this exact schema:
```python
{
  "timestamp": "2026-04-05T15:30:00+05:30",  # IST
  "predicted_direction": "up" | "down" | "neutral",
  "predicted_move_pct": 0.42,                 # e.g., +0.42%
  "confidence": 0.74,                         # 0 to 1
  "timeframe_minutes": 20,
  "signals_used": ["sentiment", "gift_nifty", "macro", "volatility"],
  "regime": "event_driven" | "baseline"
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

## ADR-008: Local LLM — Gemma 4 via Ollama (NOT direct HuggingFace)
- **Decision:** Run Gemma 4 E2B and 26B via Ollama (ollama.ai), not raw HuggingFace transformers.
- **Reason:** Ollama handles model download, quantization (4-bit for memory savings), and exposes
  a simple REST API (localhost:11434) compatible with OpenAI SDK. Zero extra code to manage GPU/CPU.
- **Usage:** `ollama pull gemma4:2b` and `ollama pull gemma4:26b` — then call via openai Python SDK.
- **Fallback chain:** Gemma 4 E2B (local) → Gemma 4 26B (local, on demand) → Gemini 2.5 Flash (cloud)
- **Date:** v2 architecture

---

## ADR-009: Dashboard Stack — FastAPI WebSocket + Flutter
- **Decision:** Backend = FastAPI with native WebSocket support. Frontend = Flutter Web.
- **Reason:** FastAPI streams live predictions every 60 seconds with minimal latency.
  Flutter is already in our stack (Vandan's expertise), reuses Dart skills, single codebase for
  web + mobile later.
- **Alternative rejected:** React (adds JavaScript/TypeScript to the stack unnecessarily)
- **WebSocket endpoint:** ws://localhost:8000/ws/predictions
- **Date:** v2 architecture

---

## ADR-010: New Agent — AnalogAgent (5th agent, Gemma-powered)
- **Decision:** Add a 5th agent: AnalogAgent, powered exclusively by Gemma 4 26B.
- **Responsibility:** Given today's conditions (regime, macro state, news type, VIX level),
  find the 3 most similar historical scenarios from training data and report what markets did.
- **Output:** {match_name, similarity_score, analog_outcome, confidence}
- **Weight in aggregator:** Starts at 0.15 (lower than others — builds trust over time via RL)
- **Date:** v2 architecture

---

## ADR-011: Ollama Must Be Running Before RITAM Starts
- **Decision:** RITAM's startup sequence checks if Ollama is running on localhost:11434.
  If not, it logs a warning and disables AnalogAgent + Gemma reasoning, falling back to
  FinBERT-only mode. System never crashes due to missing Ollama — degrades gracefully.
- **Date:** v2 architecture

