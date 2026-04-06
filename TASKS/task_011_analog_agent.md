# Task 011 — AnalogAgent (5th Agent, Gemma-Powered)
**Assigned to:** Claude Code
**Status:** TODO
**Phase:** 5 — Multi-Agent System
**Depends on:** Task 010 (gemma_client must be working), Task 006 (orchestrator exists)

## Goal
Build src/agents/analog_agent.py that:
- Reads current regime from regime_classifier.py
- Reads current sentiment score from latest DB entry
- Reads current GIFT Nifty gap, VIX value, macro event flag
- Calls analog_finder.find_analogs(conditions) → gets top 3 historical matches
- Returns agent signal in standard format:
```python
{
  "direction": "up",         # derived from analog outcomes
  "strength": 0.73,          # = similarity score of best match
  "confidence": 0.68,
  "analog_detail": {
    "top_match": "March 2020 COVID bounce",
    "similarity": 0.73,
    "expected_outcome": "+8% over next 10 sessions"
  }
}
```
- If Ollama is offline, returns {"direction": "neutral", "strength": 0.0, "confidence": 0.0}
  (graceful degradation per ADR-011)

## Update Orchestrator
After building analog_agent.py, update src/agents/orchestrator.py to:
- Add AnalogAgent as the 5th parallel agent
- Update config/agent_weights.json to add "analog_agent": 0.15
  and reduce other weights proportionally so they still sum to 1.0

## Outputs
- src/agents/analog_agent.py
- Updated src/agents/orchestrator.py
- Updated config/agent_weights.json
- tests/agents/test_analog_agent.py

## Definition of Done
- [ ] AnalogAgent returns correct signal format
- [ ] Gracefully returns neutral when Ollama offline
- [ ] Orchestrator runs all 5 agents in parallel
- [ ] Total weights in agent_weights.json = 1.0
- [ ] STATUS.md updated

