# Task 012 — Live Dashboard (FastAPI WebSocket + Flutter Web)
**Assigned to:** Claude Code
**Status:** TODO
**Phase:** 7 — Live Dashboard
**Depends on:** Tasks 001–011 (full prediction pipeline must be working)

## Part A — FastAPI WebSocket Backend
Build src/api/server.py using FastAPI that:
- Runs on localhost:8000
- WebSocket endpoint: ws://localhost:8000/ws/predictions
  - Broadcasts latest prediction dict every 60 seconds during market hours
  - Broadcasts agent signal breakdown (all 5 agents, their scores)
  - Broadcasts latest prediction_vs_actual comparison
- REST endpoints:
  - GET /api/candles?symbol=NIFTY50&limit=100 → last N candles as JSON
  - GET /api/accuracy → current week accuracy stats
  - GET /api/analogs → top 3 historical analogs for current conditions
  - GET /api/agents → current agent weights and last signal

## Part B — Flutter Web Dashboard
Build dashboard/ as a Flutter Web app with 4 panels:

### Panel 1 — Live Candlestick Chart
- Nifty 50 minute candles using fl_chart or syncfusion_flutter_charts
- GIFT Nifty as overlay line
- RITAM prediction zone: shaded region ± predicted_move_pct ahead of last candle
- Color: green zone = UP prediction, red = DOWN, grey = neutral
- Confidence shown as band width (narrow = high confidence)

### Panel 2 — Agent Signal Board (Live)
- 5 rows, one per agent
- Each row: agent name + horizontal progress bar (strength) + direction label + confidence %
- Master signal row at bottom, highlighted
- Updates every 60 seconds via WebSocket

### Panel 3 — Prediction vs Reality Tracker
- Table: timestamp | predicted | actual | error | ✓/✗
- Last 20 predictions shown
- Running accuracy % shown as large number top-right
- Sharpe ratio + max drawdown shown
- Red flash animation when prediction is wrong
- Green pulse when correct

### Panel 4 — Historical Analog Viewer
- Shows top 3 analogs from AnalogAgent
- Each card: scenario name, date, similarity %, expected outcome
- Refreshes every 5 minutes (Gemma query is slow)

## Outputs
- src/api/server.py
- src/api/websocket_manager.py
- dashboard/ (Flutter project)
- tests/api/test_server.py

## Definition of Done
- [ ] FastAPI server starts and WebSocket sends data
- [ ] Flutter app connects via WebSocket and updates all 4 panels live
- [ ] Dashboard works at localhost in browser (Flutter Web)
- [ ] All 4 panels visible and updating
- [ ] STATUS.md updated

