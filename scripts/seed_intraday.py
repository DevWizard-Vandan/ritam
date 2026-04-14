#!/usr/bin/env python
"""
One-time seed script: populates intraday_candles with 60 days of
15-min OHLCV from Kite Connect.

Usage:
    python scripts/seed_intraday.py
    python scripts/seed_intraday.py --days 30
"""
import argparse
from src.data.db import init_db
from src.data.intraday_seeder import seed_intraday_history

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=60)
    args = parser.parse_args()
    init_db()
    n = seed_intraday_history(days_back=args.days)
    print(f"Seeded {n} candles successfully.")
