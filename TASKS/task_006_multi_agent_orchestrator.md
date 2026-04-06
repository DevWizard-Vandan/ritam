# Task 006 — Multi-Agent Prediction Orchestrator
**Assigned to:** Claude Code
**Status:** TODO
**Phase:** 4 — Multi-Agent System
**Depends on:** Tasks 002, 003, 004 (data + news + sentiment must be working)

## Goal
Build src/agents/orchestrator.py using LangGraph that:
- Spawns 4 specialist agents in parallel:
  1. SentimentAgent (src/agents/sentiment_agent.py)
     - Reads last 24h headlines from DB, calls scorer.py
     - Returns: {direction, strength: 0–1, confidence: 0–1}
  2. GIFTNiftyAgent (src/agents/gift_nifty_agent.py)
     - Fetches GIFT Nifty price, calculates gap vs previous NSE close
     - Returns: {direction, gap_pct, confidence}
  3. MacroAgent (src/agents/macro_agent.py)
     - Reads FII/DII flows from NSE website (scrape or API)
     - Returns: {direction, flow_strength, confidence}
  4. VolatilityAgent (src/agents/volatility_agent.py)
     - Reads India VIX from Kite API
     - Returns: {regime: high/low/normal, vix_value, confidence}

- Master Aggregator (src/agents/aggregator.py):
  - Collects all 4 agent signals
  - Applies configurable weights (start equal: 25% each)
  - Returns final prediction in ADR-005 format (see DECISIONS.md)

## Outputs
- src/agents/orchestrator.py
- src/agents/sentiment_agent.py
- src/agents/gift_nifty_agent.py
- src/agents/macro_agent.py
- src/agents/volatility_agent.py
- src/agents/aggregator.py
- tests/agents/test_orchestrator.py
- tests/agents/test_aggregator.py

## Definition of Done
- [ ] All 4 agents return correct output format
- [ ] Aggregator produces valid prediction dict (ADR-005)
- [ ] Orchestrator runs all agents in parallel (not sequential)
- [ ] 5+ tests per agent file
- [ ] STATUS.md updated

