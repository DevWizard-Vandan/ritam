# Market AI

A self-improving AI system that predicts Nifty 50 / GIFT Nifty market movements
in real time by combining historical event mapping, FinBERT sentiment analysis,
multi-agent signal aggregation, and reinforcement learning.

## Quick Start

```bash
# 1. Clone and enter project
git clone <your-repo-url>
cd market-ai

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment
cp .env.example .env
# Edit .env with your Zerodha Kite API keys

# 5. Initialize database
python -c "from src.data.db import init_db; init_db()"

# 6. Run tests
pytest tests/ -v
```

## For AI Agents

Read `AGENTS.md` first. Check `STATUS.md` for current progress.
All tasks are in `TASKS/`. Follow rules in AGENTS.md before making any changes.

## Architecture

See `AGENTS.md` → System Architecture section for the full 4-layer diagram.

## Cost

~₹3,840/month during development. See full breakdown in project docs.
