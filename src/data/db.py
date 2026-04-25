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

    @property
    def description(self):
        return self.cursor.description

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
    DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("TIMESCALE_URL")
    POSTGRES_CONNECT_TIMEOUT = int(os.getenv("POSTGRES_CONNECT_TIMEOUT", "5"))

    def _connect_postgres():
        if not DATABASE_URL:
            raise RuntimeError(
                "DB_MODE=postgres requires DATABASE_URL or TIMESCALE_URL to be set"
            )
        return psycopg2.connect(DATABASE_URL, connect_timeout=POSTGRES_CONNECT_TIMEOUT)

    def get_connection():
        return ConnectionWrapper(_connect_postgres())
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
        raw_conn = _connect_postgres()
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
        # SQLite path — makedirs BEFORE connect, guard against empty dirname
        import sqlite3
        db_dir = os.path.dirname(settings.DB_PATH)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        conn = sqlite3.connect(settings.DB_PATH)
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


def write_news_raw(records: list[dict]) -> int:
    """
    Insert news records into news_raw, ignoring duplicates.
    Each record dict: {source, headline, url, published_at, fetched_at}
    Returns count of newly inserted rows.
    """
    inserted = 0
    with get_connection() as conn:
        for rec in records:
            cursor = insert_or_ignore(
                conn,
                f"""
                INSERT OR IGNORE INTO news_raw
                (source, headline, url, published_at, fetched_at)
                VALUES ({PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER})
                """,
                (
                    rec.get("source") or "",
                    rec.get("headline") or "",
                    rec.get("url"),
                    rec.get("published_at") or "",
                    rec.get("fetched_at") or "",
                ),
            )
            if cursor.rowcount > 0:
                inserted += cursor.rowcount
        conn.commit()
    return inserted


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


def insert_sandbox_run(
    condition: str | None,
    date: str | None,
    data_source: str,
    regime: str,
    narrative: str,
    confidence: float,
    result_json: str,
) -> None:
    """Persist a sandbox scenario run."""
    with get_connection() as conn:
        conn.execute(
            f"""
            INSERT INTO sandbox_runs
                (condition, date, data_source, regime, narrative, confidence, result_json)
            VALUES ({PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER},
                    {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER})
            """,
            (condition, date, data_source, regime, narrative, confidence, result_json),
        )


def read_sandbox_runs(limit: int = 10) -> list[dict]:
    """Return recent sandbox scenario runs, newest first."""
    safe_limit = max(1, int(limit))
    with get_connection() as conn:
        cursor = conn.execute(
            f"""
            SELECT id, condition, date, data_source, regime, narrative,
                   confidence, result_json, created_at
            FROM sandbox_runs
            ORDER BY id DESC
            LIMIT {PLACEHOLDER}
            """,
            (safe_limit,),
        )
        rows = cursor.fetchall()
    return [
        {
            "id": row[0],
            "condition": row[1],
            "date": row[2],
            "data_source": row[3],
            "regime": row[4],
            "narrative": row[5],
            "confidence": row[6],
            "result_json": row[7],
            "created_at": row[8],
        }
        for row in rows
    ]


def read_paper_trades(limit: int = 50) -> list[dict]:
    """Return recent paper trades, newest first."""
    safe_limit = max(1, int(limit))
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT id, signal, entry_price, entry_time, exit_price, exit_time,
                   pnl, outcome, sharpe_contribution, created_at
            FROM paper_trades
            ORDER BY id DESC
            LIMIT {PLACEHOLDER}
            """,
            (safe_limit,),
        ).fetchall()
    return [
        {
            "id": row[0],
            "signal": row[1],
            "entry_price": row[2],
            "entry_time": row[3],
            "exit_price": row[4],
            "exit_time": row[5],
            "pnl": row[6],
            "outcome": row[7],
            "sharpe_contribution": row[8],
            "created_at": row[9],
        }
        for row in rows
    ]


def get_agent_accuracy_stats() -> list[dict]:
    """Return agent weights and rolling accuracy, sorted by weight."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT agent_name, weight, accuracy_7d, accuracy_30d,
                   total_predictions, correct_predictions, last_updated
            FROM agent_weights
            ORDER BY weight DESC, agent_name ASC
            """
        ).fetchall()
    return [
        {
            "agent_name": row[0],
            "weight": row[1],
            "accuracy_7d": row[2],
            "accuracy_30d": row[3],
            "total_predictions": row[4],
            "correct_predictions": row[5],
            "last_updated": row[6],
        }
        for row in rows
    ]


def get_agent_weights() -> dict[str, float]:
    """Return persisted agent weights keyed by agent name."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT agent_name, weight FROM agent_weights"
        ).fetchall()
    return {row[0]: float(row[1]) for row in rows}


def upsert_agent_weight(
    agent_name: str,
    weight: float,
    accuracy_7d: float | None = None,
    accuracy_30d: float | None = None,
    total: int = 0,
    correct: int = 0,
) -> None:
    """Insert or update one agent's current weight and accuracy stats."""
    if DB_MODE == "postgres":
        sql = """
            INSERT INTO agent_weights (
                agent_name, weight, accuracy_7d, accuracy_30d,
                total_predictions, correct_predictions, last_updated
            )
            VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (agent_name) DO UPDATE SET
                weight = EXCLUDED.weight,
                accuracy_7d = EXCLUDED.accuracy_7d,
                accuracy_30d = EXCLUDED.accuracy_30d,
                total_predictions = EXCLUDED.total_predictions,
                correct_predictions = EXCLUDED.correct_predictions,
                last_updated = CURRENT_TIMESTAMP
        """
    else:
        sql = """
            INSERT INTO agent_weights (
                agent_name, weight, accuracy_7d, accuracy_30d,
                total_predictions, correct_predictions, last_updated
            )
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(agent_name) DO UPDATE SET
                weight = excluded.weight,
                accuracy_7d = excluded.accuracy_7d,
                accuracy_30d = excluded.accuracy_30d,
                total_predictions = excluded.total_predictions,
                correct_predictions = excluded.correct_predictions,
                last_updated = datetime('now')
        """
    with get_connection() as conn:
        conn.execute(
            sql,
            (agent_name, weight, accuracy_7d, accuracy_30d, total, correct),
        )


def insert_weight_history(
    agent_name: str,
    weight: float,
    accuracy_7d: float | None,
) -> None:
    """Append a weight-history point."""
    timestamp_sql = "CURRENT_TIMESTAMP" if DB_MODE == "postgres" else "datetime('now')"
    with get_connection() as conn:
        conn.execute(
            f"""
            INSERT INTO weight_history (agent_name, weight, accuracy_7d, recorded_at)
            VALUES ({PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}, {timestamp_sql})
            """,
            (agent_name, weight, accuracy_7d),
        )


def log_agent_signals(cycle_id: str, signals: list) -> None:
    """Persist raw agent signals for later attribution analysis."""
    with get_connection() as conn:
        for signal in signals:
            conn.execute(
                f"""
                INSERT INTO agent_signal_log
                    (cycle_id, agent_name, signal, confidence, reasoning)
                VALUES ({PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER},
                        {PLACEHOLDER}, {PLACEHOLDER})
                """,
                (
                    cycle_id,
                    getattr(signal, "agent_name", "unknown"),
                    int(getattr(signal, "signal", 0)),
                    float(getattr(signal, "confidence", 0.0)),
                    getattr(signal, "reasoning", ""),
                ),
            )


def insert_paper_trade(
    signal: str,
    entry_price: float,
    entry_time: str,
    exit_price: float,
    exit_time: str,
    pnl: float,
    outcome: str,
    sharpe_contribution: float | None = None,
) -> None:
    """Persist a completed paper trade."""
    with get_connection() as conn:
        conn.execute(
            f"""
            INSERT INTO paper_trades (
                signal, entry_price, entry_time, exit_price, exit_time,
                pnl, outcome, sharpe_contribution
            )
            VALUES ({PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER},
                    {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER})
            """,
            (
                signal,
                entry_price,
                entry_time,
                exit_price,
                exit_time,
                pnl,
                outcome,
                sharpe_contribution,
            ),
        )


def get_paper_trade_stats() -> dict:
    """Return aggregate paper-trading stats."""
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*),
                   COALESCE(SUM(pnl), 0),
                   COALESCE(SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END), 0)
            FROM paper_trades
            """
        ).fetchone()
    trade_count = int(row[0] or 0)
    total_pnl = float(row[1] or 0.0)
    wins = int(row[2] or 0)
    return {
        "trade_count": trade_count,
        "total_pnl": total_pnl,
        "win_rate": round(wins / trade_count, 4) if trade_count else 0.0,
    }


def get_latest_daily_metrics() -> dict | None:
    """Return the most recent daily metrics row."""
    from src.data.db_eval_helpers import read_daily_metrics

    rows = read_daily_metrics(limit=1)
    return rows[0] if rows else None


def __getattr__(name: str):
    """Lazy compatibility exports for evaluation helper functions."""
    if name in {
        "read_daily_metrics",
        "read_evaluation_state",
        "upsert_daily_metrics",
        "upsert_evaluation_state",
    }:
        from src.data import db_eval_helpers

        return getattr(db_eval_helpers, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
