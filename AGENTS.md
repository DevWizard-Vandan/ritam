# RITAM — Master Project Context (AGENTS.md)
# Ṛtam (ऋतम्) — The cosmic truth-order underlying all market movement
# READ THIS FIRST — EVERY SESSION — BEFORE DOING ANYTHING

---

## Vision

RITAM doesn't predict markets by luck — it perceives Ṛtam,
the underlying pattern of how markets truly move.

Build a self-improving AI system that:
- Maps every major historical economic/geopolitical event to its market reaction
- Uses Gemini 2.5 Flash (7-key rotation) to reason about news, history, and market conditions
- Analyzes real-time sentiment via FinBERT
- Finds historical analogs — "today resembles March 2020 at 73% similarity"
- Models relationships between GIFT Nifty, Nifty 50, and US markets
- Makes real-time probabilistic predictions of Nifty 50 moves in the next 15 minutes
- Continuously compares predictions to actual moves and learns from every error
- Displays everything live on a real-time dashboard — charts, agent signals, prediction zones
- Provides a "What If" Sandbox — time machine for scenario analysis

Ultimate output: "74% probability Nifty 50 rises 0.3–0.6% in the next 15 minutes"
— statistically right more often than not, across all market regimes.

Tagline: "Not prediction. Perception."

---

## System Architecture — RITAM v2

```
┌──────────────────────────────────────────────────────────────────┐
│  LAYER 1: DATA PERCEPTION                                        │
│  Zerodha Kite API       → Nifty 50 OHLCV (15-min candles)       │
│  GIFT Nifty feed        → Overnight gap vs NSE open              │
│  NewsAPI + RSS          → MoneyControl, ET Markets headlines     │
│  NSE website scraper    → FII/DII flow data                      │
│  Kite API (VIX)         → India VIX, options PCR                │
│  External APIs          → USD/INR, Crude Oil, Dow/Nasdaq        │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│  LAYER 2: REASONING ENGINE                                       │
│                                                                  │
│  Gemini 2.5 Flash (PRIMARY — 7-key round-robin rotation)        │
│  → Deep reasoning: regime classification, analog matching        │
│  → Complex causal reasoning about macro events                  │
│  → 7 Google account API keys = effectively unlimited throughput  │
│  → Fallback chain: key_1 → key_2 → ... → key_7                 │
│                                                                  │
│  Gemini Flash-Lite (quick reasoning)                            │
│  → Fast signal interpretation: "Is this news bullish?"          │
│  → Headline context enrichment before FinBERT scoring           │
│                                                                  │
│  FinBERT (local, specialized)                                   │
│  → Precision financial sentiment scoring (-1 to +1)             │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│  LAYER 3: MULTI-AGENT PREDICTION (9 Agents, parallel)           │
│  Each agent has a Gemini reasoning sub-layer                    │
│                                                                  │
│  SentimentAgent       → News mood last 24h (FinBERT + Gemini)  │
│  FIIDerivativeAgent   → FII/DII flow + derivative positioning   │
│  OptionsChainAgent    → OI, PCR, max pain, options flow         │
│  SectorRotationAgent  → Sector strength + rotation signals      │
│  MarketBreadthAgent   → Advance/decline, breadth indicators     │
│  GlobalMarketAgent    → US markets, Dow/Nasdaq, USD/INR, crude  │
│  MacroAgent           → RBI/Fed event detection, macro state    │
│  RegimeClassifierAgent→ Crisis/Boom/Chop/Recovery regime        │
│  AnalogAgent          → 15-min intraday analog matcher (20-win) │
│                          Falls back to daily if <20 candles     │
│                                                                  │
│  Master Aggregator → RL-weighted signal fusion → Prediction     │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│  LAYER 4: FEEDBACK + LEARNING ENGINE                             │
│  Every 5 min: new prediction cycle                              │
│  Every 75 min (5 candles): resolve prediction → score outcome   │
│  direction_correct (bool) + magnitude_error + timing_error      │
│  Weekly (Sunday 00:00 IST): PPO updates agent weights           │
│  3 self-improvement loops:                                      │
│    1. RL weight update (right agents get more voting power)     │
│    2. Analog memory growth (more history = better matching)     │
│    3. Gemini in-context learning over prediction history        │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│  LAYER 5: LIVE DASHBOARD + SANDBOX                               │
│  Panel 1: Live Nifty 50 candlestick + RITAM prediction zone     │
│           15-min ahead prediction, self-correcting, confidence  │
│  Panel 2: 9 agent signals with live RL weight bars              │
│  Panel 3: Prediction vs reality tracker (live accuracy %)       │
│  Panel 4: Historical analog viewer                              │
│  Panel 5: Agent weights (7d/30d accuracy, sorted by weight)     │
│  Sandbox: "What If" time machine — scenario analysis            │
│  WebSocket: updates every 5 min during market hours             │
└──────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack — Full

| Component | Tool / Library | Notes |
|---|---|---|
| Language | Python 3.11+ | Core backend |
| Market Data | Zerodha Kite Connect v3 | ₹500/month |
| Sentiment NLP | FinBERT (ProsusAI/finbert) | Local cache, free |
| Primary LLM | Gemini 2.5 Flash | 7-key round-robin, free tier |
| Quick LLM | Gemini Flash-Lite | Fast reasoning, free tier |
| Agent Framework | Custom parallel (FastAPI + asyncio) | 9 agents, parallel execution |
| Backtesting | Backtrader 1.9.x | Event-driven, no look-ahead |
| RL Training | Stable-Baselines3 2.x | PPO, weekly weight updates |
| Database | SQLite (dev) → PostgreSQL (L8) | Migrate at L8 deploy |
| News Ingestion | NewsAPI v2 + feedparser (RSS) | Free tier |
| Dashboard UI | React + Vite + TypeScript + Tailwind | localhost:5173 |
| Chart Library | TradingView Lightweight Charts / Recharts | L7 |
| Animations | Framer Motion | L7 |
| WebSocket Server | FastAPI + WebSockets | Streams live predictions |
| Scheduler | APScheduler 3.x | Every 5 min market-hours |
| Testing | pytest + pytest-cov | Jules manages |
| Deploy (API) | Fly.io | L8 |
| Deploy (Frontend) | Vercel | L8 |

---

## Layer Roadmap

| Layer | Name | Status |
|---|---|---|
| Core | 9 Agents + Orchestrator + Gemini Brain | ✅ Done |
| L0 | Gemini 7-Key Rotation | ✅ Done |
| L1 | Auto-Scheduler (5-min cycles) | ✅ Done |
| L2 | 9 Macro Agents Parallel | ✅ Done |
| L3 | 15-min Intraday Analog Finder | ✅ Done |
| L4 | RL Weight Updater (Sunday 00:00 IST) | ✅ Done |
| L5 | Paper Trading Engine | 🔄 In Progress |
| L6 | Signal Quality + Backtesting | ⏳ Next |
| L7 | Live Prediction Chart Dashboard | ⏳ Pending |
| L8 | Sandbox — "What If" Time Machine | ⏳ Pending |
| L9 | Landing Page + Waitlist + Invite Deploy | ⏳ Pending |
| L10 | Public Pricing + Launch | ⏳ Pending |

---

## Folder → Agent Territory Map

| Folder | Primary Agent | What Lives There |
|---|---|---|
| src/data/ | Codex | Kite feed, news ingestion, DB helpers |
| src/reasoning/ | Copilot/Codex | Gemini client, analog finder, regime classifier |
| src/sentiment/ | Codex | FinBERT scorer, preprocessor |
| src/backtest/ | Codex | Backtrader engine, signal backtester |
| src/agents/ | Copilot | All 9 agents |
| src/learning/ | Jules | Feedback loop, RL trainer, weight updater |
| src/paper_trading/ | Jules | Paper trading engine |
| src/api/ | Copilot | FastAPI server, all endpoints |
| src/config/ | Any | Settings, constants, weight loader |
| src/orchestrator/ | Copilot | MarketOrchestrator.run_cycle() |
| tests/ | Jules | All unit + integration tests |
| frontend/ | Copilot | React dashboard |
| TASKS/ | Vandan | Task assignment files |

---

## Rules for ALL Agents (Non-Negotiable)

1. NEVER delete existing tests or working code
2. Every new module MUST have a corresponding test file in tests/
3. ALWAYS update STATUS.md after completing any work
4. ALL API keys go ONLY in .env — never hardcoded anywhere
5. Use snake_case for all Python files and functions
6. Branch naming: feature/module-name (e.g., feature/paper-trading-engine)
7. NEVER modify AGENTS.md, DECISIONS.md, or .env
8. Read STATUS.md before starting any task
9. Read DECISIONS.md before making any architectural choices
10. If blocked, write the blocker in STATUS.md under "Blocked" and stop
11. Gemini 2.5 Flash (7-key rotation) is the primary LLM — use it for all reasoning
12. Gemini Flash-Lite for quick/fast reasoning tasks
13. DB changes must be additive only — never ALTER or DROP existing tables

---

## Prediction Output Format (ADR-005 — DO NOT CHANGE)

```python
{
  "timestamp": "2026-04-15T10:30:00+05:30",
  "predicted_direction": "up",        # up / down / neutral
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

## Definition of Done (Any Module)

- [ ] Core logic file written
- [ ] Test file with minimum 5 test cases
- [ ] All tests pass: `pytest tests/` shows no failures
- [ ] STATUS.md updated
- [ ] No hardcoded API keys or absolute file paths
- [ ] Errors handled gracefully (timeouts, empty input, API failures)
- [ ] Gemini 2.5 Flash used for reasoning (7-key rotation via `src/reasoning/gemini_client.py`)
