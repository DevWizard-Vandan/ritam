# RITAM — Master Project Context (AGENTS.md)
# Ṛtam (ऋतम्) — The cosmic truth-order underlying all market movement
# READ THIS FIRST — EVERY SESSION — BEFORE DOING ANYTHING

---

## Vision

RITAM doesn't predict markets by luck — it perceives Ṛtam,
the underlying pattern of how markets truly move.

Build a self-improving AI system that:
- Maps every major historical economic/geopolitical event to its market reaction
- Uses local LLMs (Gemma 4) to reason about news, history, and market conditions
- Analyzes real-time sentiment via FinBERT and Gemma 4 E2B
- Finds historical analogs — "today resembles March 2020 at 73% similarity"
- Models relationships between GIFT Nifty, Nifty 50, and US markets
- Makes real-time probabilistic predictions of Nifty 50 moves in the next 15–30 minutes
- Continuously compares predictions to actual moves and learns from every error
- Displays everything live on a real-time dashboard — charts, agent signals, prediction zones

Ultimate output: "74% probability Nifty 50 rises 0.3–0.6% in the next 20 minutes"
— statistically right more often than not, across all market regimes.

Tagline: "Not prediction. Perception."

---

## System Architecture — RITAM v2 (5 Layers)

```
┌──────────────────────────────────────────────────────────────────┐
│  LAYER 1: DATA PERCEPTION                                        │
│  Zerodha Kite API       → Nifty 50 OHLCV (minute candles)       │
│  GIFT Nifty feed        → Overnight gap vs NSE open             │
│  NewsAPI + RSS          → MoneyControl, ET Markets headlines     │
│  NSE website scraper    → FII/DII flow data                     │
│  Kite API (VIX)         → India VIX, options PCR                │
│  External APIs          → USD/INR, Crude Oil, Dow/Nasdaq        │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│  LAYER 2: REASONING ENGINE (LLM-POWERED)                         │
│                                                                  │
│  Gemma 4 E2B (local, 2.5GB, always running)                     │
│  → Quick signal interpretation: "Is this news bullish?"          │
│  → Headline context enrichment before FinBERT scoring           │
│  → 128K token context window, chain-of-thought reasoning        │
│                                                                  │
│  Gemma 4 26B MoE (local/Colab, on-demand)                       │
│  → Deep historical analog matching (find past situations)        │
│  → Market regime classification (Crisis/Boom/Chop/Recovery)     │
│  → Complex causal reasoning about macro events                  │
│                                                                  │
│  FinBERT (local, specialized)                                   │
│  → Precision financial sentiment scoring (-1 to +1)              │
│                                                                  │
│  Gemini 2.5 Flash API (cloud fallback, free tier)               │
│  → Weekly RL analysis reports                                    │
│  → Backtest narrative generation                                 │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│  LAYER 3: MULTI-AGENT PREDICTION                                 │
│  Each agent has a Gemma 4 E2B reasoning sub-layer               │
│                                                                  │
│  SentimentAgent    → News mood last 24h (FinBERT + Gemma)       │
│  GIFTNiftyAgent    → Overnight gap + gap fill probability        │
│  MacroAgent        → FII/DII flows + RBI/Fed event detection    │
│  VolatilityAgent   → India VIX + options OI + PCR              │
│  AnalogAgent (NEW) → Gemma 4 26B historical scenario matcher    │
│                                                                  │
│  Master Aggregator → RL-weighted signal fusion → Prediction     │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│  LAYER 4: FEEDBACK + LEARNING ENGINE                             │
│  Every 20 min: Predict → Compare actual → Score 3-dim error     │
│  direction_correct (bool) + magnitude_error + timing_error      │
│  Weekly: RL trainer (Stable-Baselines3) updates agent weights   │
│  config/agent_weights.json updated every Sunday 6:00 AM IST     │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│  LAYER 5: LIVE DASHBOARD (Flutter / React Web)                   │
│  Panel 1: Live Nifty 50 candlestick + RITAM prediction zone     │
│  Panel 2: 5 agent signals with live confidence bars             │
│  Panel 3: Prediction vs reality tracker (live accuracy %)       │
│  Panel 4: Gemma-powered historical analog viewer                │
│  WebSocket backend: updates every 60 seconds during mkt hours   │
└──────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack — Full

| Component            | Tool / Library                   | Notes                          |
|----------------------|----------------------------------|--------------------------------|
| Language             | Python 3.11+                     | Core backend                   |
| Market Data          | Zerodha Kite Connect v3          | ₹500/month                     |
| Sentiment NLP        | FinBERT (ProsusAI/finbert)       | Local cache, free              |
| Local LLM (small)    | Gemma 4 E2B via Ollama           | 2.5GB, runs on laptop, free    |
| Local LLM (large)    | Gemma 4 26B MoE via Ollama       | ~12GB VRAM, or Google Colab    |
| Cloud LLM fallback   | Gemini 2.5 Flash API             | Free tier: 250 req/day         |
| Agent Framework      | LangGraph                        | Parallel agents + state        |
| Backtesting          | Backtrader 1.9.x                 | Event-driven, no look-ahead    |
| RL Training          | Stable-Baselines3 2.x            | PPO, weekly weight updates     |
| Time-Series DB       | SQLite (dev) → TimescaleDB (prod)| Migrate at Phase 7             |
| News Ingestion       | NewsAPI v2 + feedparser (RSS)    | Free tier sufficient for dev   |
| LLM Serving (local)  | Ollama                           | Runs Gemma locally, free       |
| Dashboard UI         | Flutter 3.x (or React + Recharts)| WebSocket real-time updates    |
| WebSocket Server     | FastAPI + WebSockets             | Streams live predictions       |
| Testing              | pytest + pytest-cov              | Jules manages this             |
| Scheduler            | APScheduler 3.x                  | Market-hours task scheduling   |

---

## Folder → Agent Territory Map

| Folder                  | Primary Agent   | What Lives There                        |
|-------------------------|-----------------|-----------------------------------------|
| src/data/               | Codex           | Kite feed, news ingestion, DB helpers   |
| src/reasoning/          | Claude Code     | Gemma 4 E2B/26B, Gemini API wrappers    |
| src/sentiment/          | Claude Code     | FinBERT scorer, preprocessor            |
| src/backtest/           | Codex           | Backtrader engine, scenario runner      |
| src/agents/             | Claude Code     | LangGraph orchestrator, all 5 agents    |
| src/learning/           | Claude Code     | Feedback loop, RL trainer, error log    |
| src/api/                | Claude Code     | FastAPI WebSocket server for dashboard  |
| src/config/             | Any             | Settings, constants, weight loader      |
| tests/                  | Jules           | All unit + integration tests            |
| dashboard/              | Claude Code     | Flutter or React UI (Phase 6)           |
| TASKS/                  | You (Vandan)    | Task assignment files — assign + review |

---

## Phase Roadmap

| Phase | Target                  | Key Modules                                | Est. Duration |
|-------|-------------------------|--------------------------------------------|---------------|
| 1     | Data Pipeline           | kite_client, kite_feed, news_feed, db      | 2–3 weeks     |
| 2     | Sentiment Engine        | scorer.py, preprocessor.py                | 1–2 weeks     |
| 3     | Gemma Reasoning Layer   | gemma_client.py, analog_finder.py          | 2–3 weeks     |
| 4     | Backtesting Engine      | engine.py, scenario_runner.py              | 3–4 weeks     |
| 5     | Multi-Agent System      | orchestrator.py, all 5 agents              | 3–4 weeks     |
| 6     | Feedback + RL Loop      | feedback_loop.py, rl_trainer.py            | 2–3 weeks     |
| 7     | Live Dashboard          | FastAPI WS server + Flutter/React UI       | 3–4 weeks     |
| 8     | Cloud Deployment        | Docker, CI/CD, TimescaleDB migration       | Ongoing       |

---

## Rules for ALL Agents (Non-Negotiable)

1. NEVER delete existing tests or working code
2. Every new module MUST have a corresponding test file in tests/
3. ALWAYS update STATUS.md after completing any work
4. ALL API keys go ONLY in .env — never hardcoded anywhere
5. Use snake_case for all Python files and functions
6. Branch naming: feature/module-name (e.g., feature/gemma-reasoning)
7. NEVER modify AGENTS.md, DECISIONS.md, or .env
8. Read STATUS.md before starting any task to understand current state
9. Read DECISIONS.md before making any architectural choices
10. If blocked, write the blocker in STATUS.md under "Blocked" and stop
11. Gemma 4 E2B (via Ollama) is the default local LLM — use it before any paid API
12. Never call Gemini API for tasks Gemma 4 E2B can handle locally

---

## Prediction Output Format (ADR-005 — DO NOT CHANGE)

```python
{
  "timestamp": "2026-04-06T10:30:00+05:30",
  "predicted_direction": "up",        # up / down / neutral
  "predicted_move_pct": 0.42,
  "confidence": 0.74,
  "timeframe_minutes": 20,
  "signals_used": ["sentiment", "gift_nifty", "macro", "volatility", "analog"],
  "regime": "event_driven",           # event_driven / baseline
  "historical_analog": {
    "match": "March 2020 COVID bounce",
    "similarity": 0.73,
    "analog_outcome": "+8% over 10 sessions"
  }
}
```

---

## Definition of Done (Any Module)

- [ ] Core logic file written
- [ ] Test file with minimum 5 test cases
- [ ] All tests pass: `pytest tests/` shows no failures
- [ ] STATUS.md updated
- [ ] No hardcoded API keys or absolute file paths
- [ ] Errors handled gracefully (timeouts, empty input, API failures)
- [ ] Gemma used locally before falling back to Gemini API

