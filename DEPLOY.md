# Deploying and Running RITAM v2

RITAM v2 currently runs as a backend-first paper-trading evaluation system with optional React dashboard.

Runtime flow:

```text
Data -> Agents -> TradeGate -> Paper Execution or Skip -> Evaluation Metrics
```

There is no live broker order placement in evaluation mode.

---

## Local Evaluation Run

### 1. Activate environment

```powershell
venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

### 3. Verify `.env`

Required for best live-paper behavior:

```env
KITE_API_KEY=
KITE_API_SECRET=
KITE_ACCESS_TOKEN=
NEWS_API_KEY=
GEMINI_API_KEY_1=
GEMINI_API_KEY_2=
GEMINI_API_KEY_3=
GEMINI_API_KEY_4=
GEMINI_API_KEY_5=
GEMINI_API_KEY_6=
GEMINI_API_KEY_7=
DB_PATH=ritam.db
PAPER_CAPITAL=100000
PAPER_LOT_SIZE=50
```

Do not commit `.env`.

### 4. Initialize database

```powershell
python -c "from src.data.db import init_db; init_db()"
```

### 5. Start API

```powershell
uvicorn src.api.server:app --host 0.0.0.0 --port 8000 --reload
```

### 6. Confirm readiness

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/api/scheduler/status
Invoke-RestMethod http://localhost:8000/api/data/health
Invoke-RestMethod http://localhost:8000/api/evaluation/metrics
```

Expected state:

```text
API: running
Scheduler: running or explicitly disabled by config
Data health: OK during market hours
Evaluation mode: ON
Config frozen: true
Database: writable
```

---

## Optional Frontend

```powershell
cd frontend
npm install
npm run dev
```

Frontend: `http://localhost:5173`

Set frontend API base URL in `frontend/.env` or deployment environment:

```env
VITE_API_BASE_URL=http://localhost:8000
```

---

## Docker Local

```powershell
docker-compose up --build
```

API: `http://localhost:8000`

Health: `http://localhost:8000/health`

---

## Production API Deployment Notes

Preferred deployment path:

- API: Fly.io or equivalent Python/FastAPI host
- Frontend: Vercel
- Database: PostgreSQL-compatible service
- Secrets: deployment secret store only

Fly.io sketch:

```powershell
flyctl auth login
flyctl launch --no-deploy
flyctl secrets set GEMINI_API_KEY_1=...
flyctl secrets set GEMINI_API_KEY_2=...
flyctl secrets set GEMINI_API_KEY_3=...
flyctl secrets set GEMINI_API_KEY_4=...
flyctl secrets set GEMINI_API_KEY_5=...
flyctl secrets set GEMINI_API_KEY_6=...
flyctl secrets set GEMINI_API_KEY_7=...
flyctl secrets set KITE_API_KEY=...
flyctl secrets set KITE_API_SECRET=...
flyctl secrets set KITE_ACCESS_TOKEN=...
flyctl secrets set NEWS_API_KEY=...
flyctl secrets set DB_MODE=postgres
flyctl secrets set DATABASE_URL=postgres://...
flyctl secrets set ENVIRONMENT=production
flyctl deploy
```

Frontend deployment:

```powershell
cd frontend
vercel --prod
```

Set:

```env
VITE_API_BASE_URL=https://your-api-host
```

---

## Evaluation Monitoring Endpoints

| Endpoint | Use |
|---|---|
| `/health` | API process health |
| `/api/scheduler/status` | Scheduler running state |
| `/api/data/health` | Candle freshness and source diagnostics |
| `/api/evaluation/metrics` | Live evaluation metrics |
| `/api/evaluation/daily/latest` | Latest daily summary |
| `/api/evaluation/trades` | Trade journal export |
| `/api/paper/trades` | Paper trade history |
| `/api/paper/stats` | Paper P&L/open position state |

---

## End-of-Day Procedure

After market close:

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/api/evaluation/daily-summary/run
Invoke-RestMethod http://localhost:8000/api/evaluation/daily/latest
Invoke-RestMethod http://localhost:8000/api/evaluation/trades
```

Review:

- trades
- win rate
- expectancy
- max drawdown
- top NO_TRADE reason
- abnormal system errors

Do not tune thresholds based on one day.

---

## Stop Conditions

Stop or pause the run for infrastructure faults only:

- `/api/data/health` remains `STALE` for an extended period
- PCR unavailable beyond configured safety window
- repeated `SYSTEM_ERROR` reason codes
- database write failures
- scheduler loop errors
- system opens more trades than expected safety limit without warning

Do not stop because of one losing trade.

---

## Notes

- Kite is the preferred live market data source.
- yfinance fallback is useful for resilience but may be delayed.
- NSE PCR can fail intermittently; stale/unavailable state must be visible in logs/metrics.
- Evaluation mode is a measurement run, not an optimization loop.
