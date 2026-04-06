# Task 008 — Reinforcement Learning Weight Updater
**Assigned to:** Claude Code
**Status:** TODO
**Phase:** 5 — Learning Engine
**Depends on:** Task 007 (error scores must exist in DB)

## Goal
Build src/learning/rl_trainer.py using Stable-Baselines3 that:
- Runs every Sunday at 6:00 AM IST (using APScheduler)
- Reads last week's prediction_errors from DB
- Trains a PPO agent where:
  - State: [avg_sentiment_score, gift_nifty_gap, fii_flow, vix_value, hour_of_day, day_of_week]
  - Action: agent weights [w1, w2, w3, w4] (must sum to 1.0)
  - Reward: direction_accuracy_pct for that week
- Saves new weights to config/agent_weights.json
- Aggregator reads config/agent_weights.json at startup

## Config Format
```json
{
  "updated_at": "2026-04-06T06:00:00+05:30",
  "weights": {
    "sentiment_agent": 0.28,
    "gift_nifty_agent": 0.35,
    "macro_agent": 0.22,
    "volatility_agent": 0.15
  },
  "week_accuracy": 0.71
}
```

## Outputs
- src/learning/rl_trainer.py
- config/agent_weights.json (initial: equal weights 0.25 each)
- tests/learning/test_rl_trainer.py

## Definition of Done
- [ ] rl_trainer.py runs without error
- [ ] Weights update and save to JSON
- [ ] Aggregator picks up new weights on next run
- [ ] 5+ unit tests
- [ ] STATUS.md updated

