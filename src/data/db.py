"""
SQLite database helpers — write and read OHLCV candles and news headlines.
Uses SQLAlchemy for all DB operations.
"""
import sqlite3
import os
from src.config import settings
try:
    from loguru import logger
except ModuleNotFoundError:  # pragma: no cover - environment fallback
    import logging
    logger = logging.getLogger(__name__)


def get_connection():
    os.makedirs(os.path.dirname(settings.DB_PATH), exist_ok=True)
    return sqlite3.connect(settings.DB_PATH)


def init_db():
    """Create tables if they do not exist."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS candles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timestamp_ist TEXT NOT NULL,
                open REAL, high REAL, low REAL, close REAL, volume INTEGER,
                UNIQUE(symbol, timestamp_ist)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS headlines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT,
                headline TEXT NOT NULL,
                url TEXT UNIQUE,
                published_at TEXT,
                fetched_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS news_raw (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT,
                headline TEXT NOT NULL,
                url TEXT UNIQUE,
                published_at TEXT,
                fetched_at TEXT
            )
        """)
        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_news_dedup
            ON news_raw(source, headline, COALESCE(url, ''))
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS intraday_candles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timestamp_ist TEXT NOT NULL,     -- ISO8601 "2026-04-14T09:15:00+05:30"
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume INTEGER NOT NULL,
                UNIQUE(symbol, timestamp_ist)    -- no duplicates on re-seed
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_intraday_symbol_ts
            ON intraday_candles(symbol, timestamp_ist)
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT, predicted_direction TEXT,
                predicted_move_pct REAL, confidence REAL,
                timeframe_minutes INTEGER, regime TEXT,
                source TEXT DEFAULT 'daily'
            )
        """)

        # In case the table already exists, try adding the column
        try:
            conn.execute("ALTER TABLE predictions ADD COLUMN source TEXT DEFAULT 'daily'")
        except sqlite3.OperationalError:
            pass # Column likely already exists

        conn.execute("""
            CREATE TABLE IF NOT EXISTS prediction_errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prediction_id INTEGER REFERENCES predictions(id),
                actual_direction TEXT, actual_move_pct REAL,
                direction_correct INTEGER, magnitude_error REAL, scored_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_weights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                weight REAL NOT NULL DEFAULT 0.10,
                accuracy_7d REAL,           -- rolling 7-day accuracy (0.0–1.0)
                accuracy_30d REAL,          -- rolling 30-day accuracy
                total_predictions INT DEFAULT 0,
                correct_predictions INT DEFAULT 0,
                last_updated TEXT,          -- ISO8601 timestamp
                UNIQUE(agent_name)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS weight_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                weight REAL NOT NULL,
                accuracy_7d REAL,
                recorded_at TEXT NOT NULL   -- ISO8601 timestamp
            )
        """)
        try:
            conn.execute("ALTER TABLE predictions ADD COLUMN agent_signals TEXT DEFAULT NULL")
        except sqlite3.OperationalError:
            pass

        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_signal_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_id TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                signal INTEGER NOT NULL,
                confidence REAL NOT NULL,
                reasoning TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)

        conn.execute('''
            CREATE TABLE IF NOT EXISTS paper_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal TEXT,
                entry_price REAL,
                entry_time TEXT,
                exit_price REAL,
                exit_time TEXT,
                pnl REAL,
                outcome TEXT,
                sharpe_contribution REAL,
                created_at TEXT DEFAULT (datetime('now'))
            )
        ''')
        conn.commit()
    logger.info("Database initialized")


def write_candles(symbol: str, candles: list[dict]):
    """Insert OHLCV candles, ignoring duplicates."""
    with get_connection() as conn:
        conn.executemany("""
            INSERT OR IGNORE INTO candles (symbol, timestamp_ist, open, high, low, close, volume)
            VALUES (:symbol, :timestamp_ist, :open, :high, :low, :close, :volume)
        """, [{"symbol": symbol, **c} for c in candles])
        conn.commit()


def upsert_intraday_candles(symbol: str, candles: list[dict]) -> int:
    """
    Insert or ignore candles. Returns count of new rows inserted.
    Each candle dict: {timestamp_ist, open, high, low, close, volume}
    """
    with get_connection() as conn:
        cursor = conn.executemany("""
            INSERT OR IGNORE INTO intraday_candles (symbol, timestamp_ist, open, high, low, close, volume)
            VALUES (:symbol, :timestamp_ist, :open, :high, :low, :close, :volume)
        """, [{"symbol": symbol, **c} for c in candles])
        conn.commit()
        return cursor.rowcount

def read_intraday_candles(
    symbol: str,
    from_dt: str | None = None,
    to_dt: str | None = None,
    limit: int | None = None
) -> list[dict]:
    """
    Returns candles ordered ASC by timestamp_ist.
    If limit provided: returns last `limit` rows ordered ASC.
    Validates limit > 0 (raises ValueError otherwise).
    """
    if limit is not None:
        if not isinstance(limit, int) or limit <= 0:
            raise ValueError(f"limit must be a positive integer, got {limit!r}")

    with get_connection() as conn:
        query = """
            SELECT timestamp_ist, open, high, low, close, volume
            FROM intraday_candles WHERE symbol=?
        """
        params = [symbol]

        if from_dt:
            query += " AND timestamp_ist >= ?"
            params.append(from_dt)
        if to_dt:
            query += " AND timestamp_ist <= ?"
            params.append(to_dt)

        if limit is not None:
            query = f"""
                SELECT * FROM (
                    {query}
                    ORDER BY timestamp_ist DESC
                    LIMIT ?
                ) ORDER BY timestamp_ist ASC
            """
            params.append(limit)
        else:
            query += " ORDER BY timestamp_ist ASC"

        rows = conn.execute(query, tuple(params)).fetchall()

    return [{"timestamp_ist": r[0], "open": r[1], "high": r[2],
             "low": r[3], "close": r[4], "volume": r[5]} for r in rows]

def get_latest_intraday_timestamp(symbol: str) -> str | None:
    """Returns the most recent timestamp_ist for a symbol, or None."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT MAX(timestamp_ist) FROM intraday_candles WHERE symbol=?",
            (symbol,)
        ).fetchone()
    return row[0] if row and row[0] else None


def read_candles(symbol: str, from_date: str, to_date: str, limit: int = None) -> list[dict]:
    """Read OHLCV candles for a symbol between two ISO date strings.

    Args:
        symbol: Instrument identifier (e.g. ``"NSE:NIFTY 50"``).
        from_date: ISO-8601 datetime string for the start of the range (inclusive).
        to_date:   ISO-8601 datetime string for the end of the range (inclusive).
        limit:     When provided, return only the most-recent *limit* candles
                   within the date range, ordered ascending by timestamp.
                   Must be a positive integer; raises ``ValueError`` otherwise.

    Returns:
        List of candle dicts with keys:
        ``timestamp_ist``, ``open``, ``high``, ``low``, ``close``, ``volume``.
    """
    if limit is not None:
        if not isinstance(limit, int) or limit <= 0:
            raise ValueError(f"limit must be a positive integer, got {limit!r}")

    with get_connection() as conn:
        query = """
            SELECT timestamp_ist, open, high, low, close, volume
            FROM candles WHERE symbol=? AND timestamp_ist BETWEEN ? AND ?
            ORDER BY timestamp_ist ASC
        """
        params = [symbol, from_date, to_date]

        if limit is not None:
            query = """
                SELECT * FROM (
                    SELECT timestamp_ist, open, high, low, close, volume
                    FROM candles WHERE symbol=? AND timestamp_ist BETWEEN ? AND ?
                    ORDER BY timestamp_ist DESC
                    LIMIT ?
                ) ORDER BY timestamp_ist ASC
            """
            params.append(limit)

        rows = conn.execute(query, tuple(params)).fetchall()
    return [{"timestamp_ist": r[0], "open": r[1], "high": r[2],
             "low": r[3], "close": r[4], "volume": r[5]} for r in rows]


def write_news_raw(records: list[dict]):
    """Insert raw news headline records, ignoring duplicate URLs."""
    with get_connection() as conn:
        conn.executemany("""
            INSERT OR IGNORE INTO news_raw (source, headline, url, published_at, fetched_at)
            VALUES (:source, :headline, :url, :published_at, :fetched_at)
        """, records)
        conn.commit()

def log_agent_signals(cycle_id: str, signals: list) -> None:
    """Log a batch of agent signals to the database."""
    with get_connection() as conn:
        conn.executemany("""
            INSERT INTO agent_signal_log (cycle_id, agent_name, signal, confidence, reasoning)
            VALUES (:cycle_id, :agent_name, :signal, :confidence, :reasoning)
        """, [{"cycle_id": cycle_id, "agent_name": s.agent_name, "signal": s.signal,
               "confidence": s.confidence, "reasoning": s.reasoning} for s in signals])
        conn.commit()


def upsert_agent_weight(
    agent_name: str,
    weight: float,
    accuracy_7d: float,
    accuracy_30d: float,
    total: int,
    correct: int
) -> None:
    """Insert or update agent weight row."""
    import pytz
    from datetime import datetime
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist).isoformat()
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO agent_weights (agent_name, weight, accuracy_7d, accuracy_30d, total_predictions, correct_predictions, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(agent_name) DO UPDATE SET
                weight = excluded.weight,
                accuracy_7d = excluded.accuracy_7d,
                accuracy_30d = excluded.accuracy_30d,
                total_predictions = excluded.total_predictions,
                correct_predictions = excluded.correct_predictions,
                last_updated = excluded.last_updated
        """, (agent_name, weight, accuracy_7d, accuracy_30d, total, correct, now))
        conn.commit()

def get_agent_weights() -> dict[str, float]:
    """
    Returns {agent_name: weight} for all agents.
    If no row exists for an agent, caller uses hardcoded default.
    """
    with get_connection() as conn:
        rows = conn.execute("SELECT agent_name, weight FROM agent_weights").fetchall()
    return {row[0]: row[1] for row in rows}

def get_agent_accuracy_stats() -> list[dict]:
    """
    Returns full stats rows for all agents.
    Used in /api/agents/stats endpoint.
    """
    with get_connection() as conn:
        rows = conn.execute("SELECT agent_name, weight, accuracy_7d, accuracy_30d, total_predictions, correct_predictions, last_updated FROM agent_weights").fetchall()
    return [
        {
            "agent_name": row[0],
            "weight": row[1],
            "accuracy_7d": row[2],
            "accuracy_30d": row[3],
            "total_predictions": row[4],
            "correct_predictions": row[5],
            "last_updated": row[6]
        }
        for row in rows
    ]

def insert_weight_history(
    agent_name: str, weight: float, accuracy_7d: float
) -> None:
    """Appends a row to weight_history for trend tracking."""
    import pytz
    from datetime import datetime
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist).isoformat()
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO weight_history (agent_name, weight, accuracy_7d, recorded_at)
            VALUES (?, ?, ?, ?)
        """, (agent_name, weight, accuracy_7d, now))
        conn.commit()


def insert_paper_trade(
    signal: str, entry_price: float, entry_time: str,
    exit_price: float, exit_time: str, pnl: float, outcome: str
) -> None:
    """Insert a completed paper trade."""
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO paper_trades (signal, entry_price, entry_time, exit_price, exit_time, pnl, outcome)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (signal, entry_price, entry_time, exit_price, exit_time, pnl, outcome))
        conn.commit()


def read_paper_trades(limit: int = 100) -> list[dict]:
    """Read the most recent paper trades."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT id, signal, entry_price, entry_time, exit_price, exit_time, pnl, outcome, sharpe_contribution, created_at
            FROM paper_trades ORDER BY exit_time DESC LIMIT ?
        """, (limit,)).fetchall()
    return [
        {
            "id": r[0], "signal": r[1], "entry_price": r[2], "entry_time": r[3],
            "exit_price": r[4], "exit_time": r[5], "pnl": r[6], "outcome": r[7],
            "sharpe_contribution": r[8], "created_at": r[9]
        }
        for r in rows
    ]


def get_paper_trade_stats() -> dict:
    """Get paper trading statistics."""
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM paper_trades").fetchone()[0]
        wins = conn.execute("SELECT COUNT(*) FROM paper_trades WHERE outcome='WIN'").fetchone()[0]
        pnl_row = conn.execute("SELECT SUM(pnl) FROM paper_trades").fetchone()[0]

    total_pnl = float(pnl_row) if pnl_row is not None else 0.0
    win_rate = float(wins) / total if total > 0 else 0.0

    return {
        "win_rate": round(win_rate, 4),
        "total_pnl": round(total_pnl, 2),
        "trade_count": total
    }
