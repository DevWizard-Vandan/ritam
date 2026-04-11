import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.data.kite_feed import fetch_historical_candles
from src.data.db import get_connection, init_db

def main():
    init_db()
    parser = argparse.ArgumentParser(description="Seed historical daily candles for DB.")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be fetched without writing.")
    args = parser.parse_args()

    symbols = ["NSE:NIFTY 50", "NSE:NIFTY BANK"]
    start_date = "2000-01-01"
    end_date = "2024-12-31"

    if args.dry_run:
        for symbol in symbols:
            print(f"Would fetch historical daily candles for {symbol} from {start_date} to {end_date}")
        return

    for symbol in symbols:
        count = fetch_historical_candles(
            symbol=symbol,
            from_date=start_date,
            to_date=end_date,
            interval="day",
        )
        print(f"Fetched {count} candles from {start_date} to {end_date} for {symbol}")

    with get_connection() as conn:
        nifty_count = conn.execute("SELECT COUNT(*) FROM candles WHERE symbol=?", ("NSE:NIFTY 50",)).fetchone()[0]
        bank_count = conn.execute("SELECT COUNT(*) FROM candles WHERE symbol=?", ("NSE:NIFTY BANK",)).fetchone()[0]

    print(f"DB seeded. Nifty: {nifty_count} rows, Bank Nifty: {bank_count} rows")

if __name__ == "__main__":
    main()
