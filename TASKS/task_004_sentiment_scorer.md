# Task 004 — FinBERT Sentiment Scorer
**Assigned to:** Claude Code
**Status:** TODO
**Phase:** 2 — Sentiment Engine
**Depends on:** Task 003 (headlines must be in DB)

## Goal
Build src/sentiment/scorer.py that:
- Downloads and caches ProsusAI/finbert model locally (models/ folder)
- Input: list of headline strings
- Output: list of dicts: {headline, score (float -1 to +1), label (positive/negative/neutral), confidence (float 0–1)}
- Batch processes headlines (batch_size=16 for performance)
- Handles empty input, model load errors, and GPU/CPU fallback

## Input Format
```python
headlines = ["RBI raises repo rate by 25bps", "Nifty hits all-time high"]
results = score_headlines(headlines)
```

## Output Format
```python
[
  {"headline": "RBI raises repo rate by 25bps", "score": -0.62, "label": "negative", "confidence": 0.81},
  {"headline": "Nifty hits all-time high", "score": 0.94, "label": "positive", "confidence": 0.96}
]
```

## Outputs
- src/sentiment/scorer.py
- src/sentiment/preprocessor.py (clean/normalize headlines before scoring)
- tests/sentiment/test_scorer.py

## Definition of Done
- [ ] scorer.py with score_headlines() function
- [ ] preprocessor.py with clean_headline() function
- [ ] Model cached locally in models/finbert/
- [ ] 5+ unit tests passing
- [ ] STATUS.md updated

