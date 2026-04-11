import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.data.db import get_connection, init_db

def main():
    init_db()
    symbols = ["NSE:NIFTY 50", "NSE:NIFTY BANK"]
    total_db_rows = 0

    with get_connection() as conn:
        for symbol in symbols:
            # Get basic stats
            row = conn.execute(
                "SELECT COUNT(*), MIN(timestamp_ist), MAX(timestamp_ist) FROM candles WHERE symbol=?",
                (symbol,)
            ).fetchone()

            count, min_date, max_date = row
            if count == 0:
                print(f"{symbol}: 0 rows found.")
                continue

            total_db_rows += count

            # Check for gaps > 5 days
            gap_rows = conn.execute(
                """
                SELECT prev_ts, timestamp_ist,
                       CAST(julianday(timestamp_ist) - julianday(prev_ts) AS INTEGER) AS gap_days
                FROM (
                    SELECT timestamp_ist,
                           LAG(timestamp_ist) OVER (ORDER BY timestamp_ist ASC) AS prev_ts
                    FROM candles
                    WHERE symbol=?
                      AND time(timestamp_ist) = '00:00:00'
                )
                WHERE prev_ts IS NOT NULL
                  AND julianday(timestamp_ist) - julianday(prev_ts) > 5
                ORDER BY timestamp_ist ASC
                """,
                (symbol,)
            ).fetchall()
            gaps = [
                (datetime.fromisoformat(r[0]).strftime('%Y-%m-%d'),
                 datetime.fromisoformat(r[1]).strftime('%Y-%m-%d'),
                 r[2])
                for r in gap_rows
            ]

            print(f"{symbol}: {count} total rows")
            print(f"  Earliest date: {min_date}")
            print(f"  Latest date: {max_date}")

            if gaps:
                print(f"  Found {len(gaps)} gaps > 5 days. Example gaps:")
                for gap in gaps[:3]:
                    print(f"    - {gap[0]} to {gap[1]} ({gap[2]} days)")
            else:
                print("  No gaps > 5 days found.")
            print("-" * 40)

    if total_db_rows < 1000:
        print(f"Error: Expected at least 1000 rows in DB, but found {total_db_rows}.")
        sys.exit(1)

if __name__ == "__main__":
    main()
