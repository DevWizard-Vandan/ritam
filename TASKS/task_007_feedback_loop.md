# Task 007 — Predict vs Reality Feedback Loop
**Assigned to:** Claude Code
**Status:** TODO
**Phase:** 5 — Learning Engine
**Depends on:** Task 006 (orchestrator must produce predictions)

## Goal
Build src/learning/feedback_loop.py that:
- Every 20 minutes during market hours:
  1. Calls orchestrator to get current prediction
  2. Saves prediction to DB: predictions table (see schema below)
  3. 20 minutes later, fetches the actual Nifty move
  4. Scores the prediction across 3 dimensions (see DECISIONS.md ADR-006):
     - direction_correct (bool)
     - magnitude_error (float): abs(predicted_pct - actual_pct)
     - timing_error (int): always 0 for now (fixed 20-min window)
  5. Saves error scores to DB: prediction_errors table
- Generates daily accuracy report: reports/daily_{date}.json
  {predictions_made, direction_accuracy_pct, avg_magnitude_error, best_setup, worst_setup}

## DB Schema
```sql
-- predictions table
CREATE TABLE predictions (
  id INTEGER PRIMARY KEY,
  timestamp TEXT,           -- ISO8601 IST
  predicted_direction TEXT, -- up/down/neutral
  predicted_move_pct REAL,
  confidence REAL,
  timeframe_minutes INTEGER,
  regime TEXT
);

-- prediction_errors table
CREATE TABLE prediction_errors (
  id INTEGER PRIMARY KEY,
  prediction_id INTEGER REFERENCES predictions(id),
  actual_direction TEXT,
  actual_move_pct REAL,
  direction_correct INTEGER, -- 0 or 1
  magnitude_error REAL,
  scored_at TEXT
);
```

## Outputs
- src/learning/feedback_loop.py
- src/learning/error_scorer.py
- src/learning/report_generator.py
- tests/learning/test_feedback_loop.py

## Definition of Done
- [ ] Predictions saved to DB with correct schema
- [ ] Error scores calculated and saved 20 min later
- [ ] Daily report generated as JSON
- [ ] 5+ unit tests passing
- [ ] STATUS.md updated

