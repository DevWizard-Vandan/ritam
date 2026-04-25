"""
SQLite database helpers — write and read OHLCV candles and news headlines.
Uses SQLAlchemy for all DB operations.
"""
import os
from src.config import settings
try:
    from loguru import logger
except ModuleNotFoundError:  # pragma: no cover - environment fallback
    import logging
    logger = logging.getLogger(__name__)

DB_MODE = os.getenv("DB_MODE", "sqlite")
PLACEHOLDER = "%s" if DB_MODE == "postgres" else "?"

if DB_MODE == "postgres":
    try:
        import psycopg2  # type: ignore
    except ModuleNotFoundError:  # pragma: no cover - local fallback
        logger.warning("psycopg2 unavailable; falling back to sqlite DB mode")
        DB_MODE = "sqlite"
        PLACEHOLDER = "?"

def insert_or_ignore(conn, query, params):
    """
    Executes an INSERT, ignoring duplicate key errors.
    Handles both SQLite (INSERT OR IGNORE) and PostgreSQL
    (INSERT ... ON CONFLICT DO NOTHING).
    """
    if DB_MODE == "postgres":
        query = query.replace(
            "INSERT OR IGNORE INTO",
            "INSERT INTO"
        ) + " ON CONFLICT DO NOTHING"
    return conn.execute(query, params)

class CursorWrapper:
    def __init__(self, cursor):
        self.cursor = cursor
        self.rowcount = -1
        self.lastrowid = None

    def execute(self, query, params=None):
        if DB_MODE == "postgres":
            query = query.replace("?", "%s")
            import re
            query = re.sub(r':(\w+)', r'%(\1)s', query)

        if params is not None:
            self.cursor.execute(query, params)
        else:
            self.cursor.execute(query)
        self.rowcount = self.cursor.rowcount
        try:
            self.lastrowid = self.cursor.lastrowid
        except Exception:
            pass
        return self

    def executemany(self, query, params):
        if DB_MODE == "postgres":
            query = query.replace("?", "%s")
            import re
            query = re.sub(r':(\w+)', r'%(\1)s', query)
        self.cursor.executemany(query, params)
        self.rowcount = self.cursor.rowcount
        return self

    def fetchall(self):
        return self.cursor.fetchall()

    def fetchone(self):
        return self.cursor.fetchone()

class ConnectionWrapper:
    def __init__(self, conn):
        self.conn = conn

    def execute(self, query, params=None):
        cursor = CursorWrapper(self.conn.cursor())
        return cursor.execute(query, params)

    def executemany(self, query, params):
        cursor = CursorWrapper(self.conn.cursor())
        return cursor.executemany(query, params)

    def commit(self):
        self.conn.commit()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.conn.commit()
        self.conn.close()

if DB_MODE == "postgres":
    DATABASE_URL = os.getenv("DATABASE_URL")
    def get_connection():
        return ConnectionWrapper(psycopg2.connect(DATABASE_URL))
else:
    import sqlite3
    def _sqlite_connection(path: str | None = None):
        db_path = path or settings.DB_PATH
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        return sqlite3.connect(db_path)

    def get_connection():
        return _sqlite_connection(settings.DB_PATH)


DAILY_METRICS_DDL = """
CREATE TABLE IF NOT EXISTS daily_metrics (
    metric_date TEXT PRIMARY KEY,
    trades INTEGER NOT NULL DEFAULT 0,
    win_rate REAL NOT NULL DEFAULT 0.0,
    expectancy REAL NOT NULL DEFAULT 0.0,
    max_drawdown REAL NOT NULL DEFAULT 0.0,
    top_no_trade_reason TEXT,
    current_equity REAL NOT NULL DEFAULT 0.0,
    no_trade_counts_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
)
"""

EVALUATION_STATE_DDL = """
CREATE TABLE IF NOT EXISTS evaluation_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evaluation_start_date TEXT NOT NULL,
    starting_equity REAL NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(evaluation_start_date)
)
"""


def _ensure_daily_metrics_table(conn) -> None:
    conn.execute(DAILY_METRICS_DDL)


def _ensure_evaluation_state_table(conn) -> None:
    conn.execute(EVALUATION_STATE_DDL)


def _ensure_daily_metrics_table(conn) -> None:
    conn.execute(DAILY_METRICS_DDL)


def _pg_ddl(query: str) -> str:
    """Transform SQLite DDL to PostgreSQL-compatible DDL."""
    query = query.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
    query = query.replace("(datetime('now'))", "CURRENT_TIMESTAMP")
    query = query.replace("WITHOUT ROWID", "")
    return query


def _run_ddl_safe(raw_conn, query: str):
    """
    Run a single DDL statement safely.
    On PostgreSQL: uses autocommit so a failure doesn't poison
    the transaction block for subsequent statements.
    On SQLite: runs normally.
    """
    if DB_MODE == "postgres":
        query = _pg_ddl(query)
        old_autocommit = raw_conn.autocommit
        raw_conn.autocommit = True
        try:
            cur = raw_conn.cursor()
            cur.execute(query)
            cur.close()
        except Exception as e:
            logger.warning(f"DDL skipped (likely already exists): {e}")
        finally:
            raw_conn.autocommit = old_autocommit
    else:
        raw_conn.execute(query)


def execute_ddl(conn, query):
    """Legacy helper kept for compatibility — wraps _run_ddl_safe."""
    if DB_MODE == "postgres":
        query = _pg_ddl(query)
        raw = conn.conn  # unwrap ConnectionWrapper
        old_autocommit = raw.autocommit
        raw.autocommit = True
        try:
            cur = raw.cursor()
            cur.execute(query)
            cur.close()
        except Exception as e:
            logger.warning(f"DDL skipped (likely already exists): {e}")
        finally:
            raw.autocommit = old_autocommit
    else:
        conn.execute(query)


def init_db():
    """Create tables if they do not exist."""
    if DB_MODE == "postgres":
        raw_conn = psycopg2.connect(DATABASE_URL)
        ddl_statements = [
            """
            CREATE TABLE IF NOT EXISTS candles (
                id SERIAL PRIMARY KEY,
                symbol TEXT NOT NULL,
                timestamp_ist TEXT NOT NULL,
                open REAL, high REAL, low REAL, close REAL, volume INTEGER,
                UNIQUE(symbol, timestamp_ist)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS headlines (
                id SERIAL PRIMARY KEY,
                source TEXT,
                headline TEXT NOT NULL,
                url TEXT UNIQUE,
                published_at TEXT,
                fetched_at TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS news_raw (
                id SERIAL PRIMARY KEY,
                source TEXT,
                headline TEXT NOT NULL,
                url TEXT UNIQUE,
                published_at TEXT,
                fetched_at TEXT
            )
            """,
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_news_dedup
            ON news_raw(source, headline, url)
            WHERE url IS NOT NULL
            """,
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_news_dedup_no_url
            ON news_raw(source, headline)
            WHERE url IS NULL
            """,
            """
            CREATE TABLE IF NOT EXISTS intraday_candles (
                id SERIAL PRIMARY KEY,
                symbol TEXT NOT NULL,
                timestamp_ist TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume INTEGER NOT NULL,
                UNIQUE(symbol, timestamp_ist)
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_intraday_symbol_ts
            ON intraday_candles(symbol, timestamp_ist)
            """,
            """
            CREATE TABLE IF NOT EXISTS predictions (
                id SERIAL PRIMARY KEY,
                timestamp TEXT, predicted_direction TEXT,
                predicted_move_pct REAL, confidence REAL,
                timeframe_minutes INTEGER, regime TEXT,
                source TEXT DEFAULT 'daily',
                resolved INTEGER DEFAULT 0,
                agent_signals TEXT DEFAULT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS prediction_errors (
                id SERIAL PRIMARY KEY,
                prediction_id INTEGER REFERENCES predictions(id),
                actual_direction TEXT, actual_move_pct REAL,
                direction_correct INTEGER, magnitude_error REAL, scored_at TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS agent_weights (
                id SERIAL PRIMARY KEY,
                agent_name TEXT NOT NULL,
                weight REAL NOT NULL DEFAULT 0.10,
                accuracy_7d REAL,
                accuracy_30d REAL,
                total_predictions INT DEFAULT 0,
                correct_predictions INT DEFAULT 0,
                last_updated TEXT,
                UNIQUE(agent_name)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS weight_history (
                id SERIAL PRIMARY KEY,
                agent_name TEXT NOT NULL,
                weight REAL NOT NULL,
                accuracy_7d REAL,
                recorded_at TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS agent_signal_log (
                id SERIAL PRIMARY KEY,
                cycle_id TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                signal INTEGER NOT NULL,
                confidence REAL NOT NULL,
                reasoning TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS paper_trades (
                id SERIAL PRIMARY KEY,
                signal TEXT,
                entry_price REAL,
                entry_time TEXT,
                exit_price REAL,
                exit_time TEXT,
                pnl REAL,
                outcome TEXT,
                sharpe_contribution REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS daily_metrics (
                metric_date TEXT PRIMARY KEY,
                trades INTEGER NOT NULL DEFAULT 0,
                win_rate REAL NOT NULL DEFAULT 0.0,
                expectancy REAL NOT NULL DEFAULT 0.0,
                max_drawdown REAL NOT NULL DEFAULT 0.0,
                top_no_trade_reason TEXT,
                current_equity REAL NOT NULL DEFAULT 0.0,
                no_trade_counts_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS evaluation_state (
                id SERIAL PRIMARY KEY,
                evaluation_start_date TEXT NOT NULL,
                starting_equity REAL NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(evaluation_start_date)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS sandbox_runs (
                id SERIAL PRIMARY KEY,
                condition TEXT,
                date TEXT,
                data_source TEXT,
                regime TEXT,
                narrative TEXT,
                confidence REAL,
                result_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """,
        ]
        for stmt in ddl_statements:
            _run_ddl_safe(raw_conn, stmt)
        raw_conn.close()
    else:
        # SQLite path — single transaction is fine
        import sqlite3
        conn = sqlite3.connect(settings.DB_PATH)
        os.makedirs(os.path.dirname(settings.DB_PATH), exist_ok=True)
        stmts = [
            """
            CREATE TABLE IF NOT EXISTS candles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timestamp_ist TEXT NOT NULL,
                open REAL, high REAL, low REAL, close REAL, volume INTEGER,
                UNIQUE(symbol, timestamp_ist)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS headlines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT,
                headline TEXT NOT NULL,
                url TEXT UNIQUE,
                published_at TEXT,
                fetched_at TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS news_raw (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT,
                headline TEXT NOT NULL,
                url TEXT UNIQUE,
                published_at TEXT,
                fetched_at TEXT
            )
            """,
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_news_dedup
            ON news_raw(source, headline, url)
            WHERE url IS NOT NULL
            """,
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_news_dedup_no_url
            ON news_raw(source, headline)
            WHERE url IS NULL
            """,
            """
            CREATE TABLE IF NOT EXISTS intraday_candles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timestamp_ist TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume INTEGER NOT NULL,
                UNIQUE(symbol, timestamp_ist)
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_intraday_symbol_ts
            ON intraday_candles(symbol, timestamp_ist)
            """,
            """
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT, predicted_direction TEXT,
                predicted_move_pct REAL, confidence REAL,
                timeframe_minutes INTEGER, regime TEXT,
                source TEXT DEFAULT 'daily',
                resolved INTEGER DEFAULT 0,
                agent_signals TEXT DEFAULT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS prediction_errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prediction_id INTEGER REFERENCES predictions(id),
                actual_direction TEXT, actual_move_pct REAL,
                direction_correct INTEGER, magnitude_error REAL, scored_at TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS agent_weights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                weight REAL NOT NULL DEFAULT 0.10,
                accuracy_7d REAL,
                accuracy_30d REAL,
                total_predictions INT DEFAULT 0,
                correct_predictions INT DEFAULT 0,
                last_updated TEXT,
                UNIQUE(agent_name)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS weight_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                weight REAL NOT NULL,
                accuracy_7d REAL,
                recorded_at TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS agent_signal_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_id TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                signal INTEGER NOT NULL,
                confidence REAL NOT NULL,
                reasoning TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """,
            """
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
            """,
            """
            CREATE TABLE IF NOT EXISTS daily_metrics (
                metric_date TEXT PRIMARY KEY,
                trades INTEGER NOT NULL DEFAULT 0,
                win_rate REAL NOT NULL DEFAULT 0.0,
                expectancy REAL NOT NULL DEFAULT 0.0,
                max_drawdown REAL NOT NULL DEFAULT 0.0,
                top_no_trade_reason TEXT,
                current_equity REAL NOT NULL DEFAULT 0.0,
                no_trade_counts_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS evaluation_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evaluation_start_date TEXT NOT NULL,
                starting_equity REAL NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                UNIQUE(evaluation_start_date)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS sandbox_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                condition TEXT,
                date TEXT,
                data_source TEXT,
                regime TEXT,
                narrative TEXT,
                confidence REAL,
                result_json TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
            """,
        ]
        for stmt in stmts:
            try:
                conn.execute(stmt)
            except Exception as e:
                logger.warning(f"DDL skipped: {e}")
        conn.commit()
        conn.close()
    logger.info("Database initialized")


def write_candles(symbol: str, candles: list[dict]):
    """Insert OHLCV candles, ignoring duplicates."""
    with get_connection() as conn:
        records = [{"symbol": symbol, **c} for c in candles]
        for record in records:
            insert_or_ignore(
                conn,
                f"""
                INSERT OR IGNORE INTO candles
                (symbol, timestamp_ist, open, high, low, close, volume)
                VALUES ({PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER})
                """,
                (
                    record["symbol"],
                    record["timestamp_ist"],
                    record["open"],
                    record["high"],
                    record["low"],
                    record["close"],
                    record["volume"],
                ),
            )
        conn.commit()


def upsert_intraday_candles(symbol: str, candles: list[dict]) -> int:
    """
    Insert or ignore candles. Returns count of new rows inserted.
    Each candle dict: {timestamp_ist, open, high, low, close, volume}
    """
    with get_connection() as conn:
        inserted_rows = 0
        records = [{"symbol": symbol, **c} for c in candles]
        for record in records:
            cursor = insert_or_ignore(
                conn,
                f"""
                INSERT OR IGNORE INTO intraday_candles
                (symbol, timestamp_ist, open, high, low, close, volume)
                VALUES ({PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER})
                """,
                (
                    record["symbol"],
                    record["timestamp_ist"],
                    record["open"],
                    record["high"],
                    record["low"],
                    record["close"],
                    record["volume"],
                ),
            )
            if cursor.rowcount > 0:
                inserted_rows += cursor.rowcount
        conn.commit()
        return inserted_rows

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
    """Read OHLCV candles for a symbol between two ISO date strings."""
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
        for record in records:
            insert_or_ignore(
                conn,
                f"""
                INSERT OR IGNORE INTO news_raw
                (source, headline, url, published_at, fetched_at)
                VALUES ({PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER})
                """,
                (
                    record["source"],
                    record["headline"],
                    record["url"],
                    record["published_at"],
                    record["fetched_at"],
                ),
            )
        conn.commit()

def log_agent_signals(cycle_id: str, signals: list) -> None:
    """Log a batch of agent signals to the database."""
    with get_connection() as conn:
        conn.executemany(f"""
            INSERT INTO agent_signal_log (cycle_id, agent_name, signal, confidence, reasoning)
            VALUES ({PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER})
        """, [(cycle_id, s.agent_name, s.signal, s.confidence, s.reasoning) for s in signals])
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
    with get_connection() as conn:
        rows = conn.execute("SELECT agent_name, weight FROM agent_weights").fetchall()
    return {row[0]: row[1] for row in rows}

def get_agent_accuracy_stats() -> list[dict]:
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


def upsert_daily_metrics(
    metric_date: str,
    trades: int,
    win_rate: float,
    expectancy: float,
    max_drawdown: float,
    top_no_trade_reason: str | None,
    current_equity: float,
    no_trade_counts_json: str | None,
    db_path: str | None = None,
) -> None:
    """Insert or update a single daily evaluation summary row."""
    if DB_MODE == "postgres" and db_path is None:
        conn = get_connection()
    else:
        conn = _sqlite_connection(db_path)
    with conn:
        _ensure_daily_metrics_table(conn)
        conn.execute(
            """
            INSERT INTO daily_metrics (
                metric_date, trades, win_rate, expectancy, max_drawdown,
                top_no_trade_reason, current_equity, no_trade_counts_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(metric_date) DO UPDATE SET
                trades = excluded.trades,
                win_rate = excluded.win_rate,
                expectancy = excluded.expectancy,
                max_drawdown = excluded.max_drawdown,
                top_no_trade_reason = excluded.top_no_trade_reason,
                current_equity = excluded.current_equity,
                no_trade_counts_json = excluded.no_trade_counts_json,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                metric_date,
                trades,
                win_rate,
                expectancy,
                max_drawdown,
                top_no_trade_reason,
                current_equity,
                no_trade_counts_json,
            ),
        )
        conn.commit()


def read_daily_metrics(limit: int = 30, db_path: str | None = None) -> list[dict]:
    """Read the most recent daily evaluation summaries."""
    if DB_MODE == "postgres" and db_path is None:
        conn = get_connection()
    else:
        conn = _sqlite_connection(db_path)
    with conn:
        _ensure_daily_metrics_table(conn)
        rows = conn.execute(
            """
            SELECT metric_date, trades, win_rate, expectancy, max_drawdown,
                   top_no_trade_reason, current_equity, no_trade_counts_json,
                   created_at, updated_at
            FROM daily_metrics
            ORDER BY metric_date DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [
        {
            "metric_date": r[0],
            "trades": r[1],
            "win_rate": r[2],
            "expectancy": r[3],
            "max_drawdown": r[4],
            "top_no_trade_reason": r[5],
            "current_equity": r[6],
            "no_trade_counts_json": r[7],
            "created_at": r[8],
            "updated_at": r[9],
        }
        for r in rows
    ]


def get_latest_daily_metrics(db_path: str | None = None) -> dict | None:
    rows = read_daily_metrics(limit=1, db_path=db_path)
    return rows[0] if rows else None


def upsert_evaluation_state(
    evaluation_start_date: str,
    starting_equity: float,
    db_path: str | None = None,
) -> None:
    """Persist the evaluation run marker and baseline equity."""
    if DB_MODE == "postgres" and db_path is None:
        conn = get_connection()
    else:
        conn = _sqlite_connection(db_path)
    with conn:
        _ensure_evaluation_state_table(conn)
        conn.execute(
            """
            INSERT INTO evaluation_state (
                evaluation_start_date, starting_equity, updated_at
            ) VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(evaluation_start_date) DO UPDATE SET
                starting_equity = excluded.starting_equity,
                updated_at = CURRENT_TIMESTAMP
            """,
            (evaluation_start_date, starting_equity),
        )
        conn.commit()


def read_evaluation_state(db_path: str | None = None) -> dict | None:
    """Read the first persisted evaluation marker, if present."""
    if DB_MODE == "postgres" and db_path is None:
        conn = get_connection()
    else:
        conn = _sqlite_connection(db_path)
    with conn:
        _ensure_evaluation_state_table(conn)
        row = conn.execute(
            """
            SELECT evaluation_start_date, starting_equity, created_at, updated_at
            FROM evaluation_state
            ORDER BY id ASC
            LIMIT 1
            """
        ).fetchone()
    if not row:
        return None
    return {
        "evaluation_start_date": row[0],
        "starting_equity": row[1],
        "created_at": row[2],
        "updated_at": row[3],
    }


def insert_sandbox_run(
    condition: str | None,
    date: str | None,
    data_source: str,
    regime: str,
    narrative: str,
    confidence: float,
    result_json: str
) -> int:
    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO sandbox_runs (condition, date, data_source, regime, narrative, confidence, result_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (condition, date, data_source, regime, narrative, confidence, result_json))
        conn.commit()
        return cursor.lastrowid

def read_sandbox_runs(limit: int = 10) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT id, condition, date, data_source, regime, narrative, confidence, result_json, created_at
            FROM sandbox_runs ORDER BY id DESC LIMIT ?
        """, (limit,)).fetchall()
    return [
        {
            "id": r[0], "condition": r[1], "date": r[2], "data_source": r[3],
            "regime": r[4], "narrative": r[5], "confidence": r[6],
            "result_json": r[7], "created_at": r[8]
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
