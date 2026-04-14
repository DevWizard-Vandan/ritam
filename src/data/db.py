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
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT, predicted_direction TEXT,
                predicted_move_pct REAL, confidence REAL,
                timeframe_minutes INTEGER, regime TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS prediction_errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prediction_id INTEGER REFERENCES predictions(id),
                actual_direction TEXT, actual_move_pct REAL,
                direction_correct INTEGER, magnitude_error REAL, scored_at TEXT
            )
        """)
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
