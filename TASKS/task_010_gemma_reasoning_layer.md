# Task 010 — Gemma 4 Reasoning Layer
**Assigned to:** Claude Code
**Status:** TODO
**Phase:** 3 — Reasoning Engine
**Depends on:** Task 001 (env setup must be working)

## Prerequisites (Manual — Vandan does this once)
```bash
# 1. Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh   # Mac/Linux
# Windows: download installer from ollama.ai

# 2. Pull models
ollama pull gemma4:2b       # ~2.5 GB — always-on quick reasoning
ollama pull gemma4:26b      # ~15 GB  — deep historical analog (needs good GPU or Colab)

# 3. Start Ollama server (keep running in background)
ollama serve
# Ollama now listens at http://localhost:11434
```

## Goal
Build src/reasoning/gemma_client.py that:
- Connects to Ollama at localhost:11434 using the openai Python SDK
  (Ollama exposes an OpenAI-compatible API endpoint)
- Exposes two functions:
  1. `quick_reason(prompt: str) -> str` — uses gemma4:2b, max 512 tokens, fast
  2. `deep_reason(prompt: str) -> str` — uses gemma4:26b, max 2048 tokens, slower
- Checks if Ollama is running at startup via health check
- Falls back to Gemini 2.5 Flash API if Ollama is unavailable
- Logs which model was used for every call

## Also Build
src/reasoning/analog_finder.py that:
- Takes current market conditions as input:
  {regime, vix_level, sentiment_score, gift_nifty_gap, macro_event (str or None)}
- Builds a natural language prompt describing today's conditions
- Calls deep_reason() with the prompt:
  "Given these market conditions: [conditions]. Find the 3 most historically similar
   scenarios from market history (any global market, any era). For each, describe:
   scenario name, approximate date, what the market did over next 5 sessions,
   and why conditions were similar."
- Parses the response into structured output:
  [{match, date_approx, similarity_description, expected_outcome, confidence}]

src/reasoning/regime_classifier.py that:
- Takes last 20 candles + current VIX + today's news count
- Calls quick_reason() to classify current regime:
  "crisis" / "recovery" / "trending_up" / "trending_down" / "choppy" / "baseline"

## Outputs
- src/reasoning/gemma_client.py
- src/reasoning/analog_finder.py
- src/reasoning/regime_classifier.py
- tests/reasoning/test_gemma_client.py (mock Ollama responses)
- tests/reasoning/test_analog_finder.py
- tests/reasoning/test_regime_classifier.py

## Definition of Done
- [ ] gemma_client.py connects to Ollama or falls back to Gemini
- [ ] Health check gracefully handles Ollama being offline
- [ ] analog_finder returns structured list of 3 analogs
- [ ] regime_classifier returns one of 6 regime strings
- [ ] All tests mock Ollama (no real API calls in tests)
- [ ] STATUS.md updated

