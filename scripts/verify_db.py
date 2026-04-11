import sys
from datetime import datetime

from src.data.db import get_connection

def main():
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
            timestamps = conn.execute(
                "SELECT timestamp_ist FROM candles WHERE symbol=? ORDER BY timestamp_ist ASC",
                (symbol,)
            ).fetchall()

            gaps = []
            for i in range(1, len(timestamps)):
                prev_date = datetime.fromisoformat(timestamps[i-1][0])
                curr_date = datetime.fromisoformat(timestamps[i][0])
                delta = curr_date - prev_date
                if delta.days > 5:
                    gaps.append((prev_date.strftime('%Y-%m-%d'), curr_date.strftime('%Y-%m-%d'), delta.days))

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
