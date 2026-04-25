"""CRUD helpers for daily_metrics and evaluation_state tables.

Kept in a separate module to avoid making db.py even larger.
Imported by both src.data.db (re-exported) and directly by tests.
"""
from __future__ import annotations

import json
from typing import Any

from src.data.db import get_connection, DB_MODE

try:
    from loguru import logger
except ModuleNotFoundError:  # pragma: no cover
    import logging
    logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# daily_metrics
# ---------------------------------------------------------------------------

def upsert_daily_metrics(
    metric_date: str,
    trades: int,
    win_rate: float,
    expectancy: float,
    max_drawdown: float,
    top_no_trade_reason: str | None,
    current_equity: float,
    no_trade_counts_json: str | None = None,
    *,
    db_path: str | None = None,
) -> None:
    """Insert or replace a daily-metrics row."""
    if DB_MODE == "postgres":
        sql = """
            INSERT INTO daily_metrics
                (metric_date, trades, win_rate, expectancy, max_drawdown,
                 top_no_trade_reason, current_equity, no_trade_counts_json,
                 updated_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,CURRENT_TIMESTAMP)
            ON CONFLICT (metric_date) DO UPDATE SET
                trades               = EXCLUDED.trades,
                win_rate             = EXCLUDED.win_rate,
                expectancy           = EXCLUDED.expectancy,
                max_drawdown         = EXCLUDED.max_drawdown,
                top_no_trade_reason  = EXCLUDED.top_no_trade_reason,
                current_equity       = EXCLUDED.current_equity,
                no_trade_counts_json = EXCLUDED.no_trade_counts_json,
                updated_at           = CURRENT_TIMESTAMP
        """
        params: tuple = (
            metric_date, trades, win_rate, expectancy, max_drawdown,
            top_no_trade_reason, current_equity, no_trade_counts_json,
        )
    else:
        sql = """
            INSERT INTO daily_metrics
                (metric_date, trades, win_rate, expectancy, max_drawdown,
                 top_no_trade_reason, current_equity, no_trade_counts_json,
                 updated_at)
            VALUES (?,?,?,?,?,?,?,?,datetime('now'))
            ON CONFLICT(metric_date) DO UPDATE SET
                trades               = excluded.trades,
                win_rate             = excluded.win_rate,
                expectancy           = excluded.expectancy,
                max_drawdown         = excluded.max_drawdown,
                top_no_trade_reason  = excluded.top_no_trade_reason,
                current_equity       = excluded.current_equity,
                no_trade_counts_json = excluded.no_trade_counts_json,
                updated_at           = datetime('now')
        """
        params = (
            metric_date, trades, win_rate, expectancy, max_drawdown,
            top_no_trade_reason, current_equity, no_trade_counts_json,
        )

    import sqlite3 as _sqlite3
    import os as _os

    if DB_MODE != "postgres" and db_path:
        from src.config import settings as _settings
        _db_path = db_path
        _db_dir = _os.path.dirname(_db_path)
        if _db_dir:
            _os.makedirs(_db_dir, exist_ok=True)
        conn = _sqlite3.connect(_db_path)
        try:
            conn.execute(sql, params)
            conn.commit()
        finally:
            conn.close()
        return

    with get_connection() as conn:
        conn.execute(sql, params)


def read_daily_metrics(
    limit: int = 30,
    *,
    db_path: str | None = None,
) -> list[dict[str, Any]]:
    """Return the most-recent *limit* daily-metrics rows, newest first."""
    if DB_MODE == "postgres":
        sql = """
            SELECT metric_date, trades, win_rate, expectancy, max_drawdown,
                   top_no_trade_reason, current_equity, no_trade_counts_json,
                   created_at, updated_at
            FROM daily_metrics
            ORDER BY metric_date DESC
            LIMIT %s
        """
    else:
        sql = """
            SELECT metric_date, trades, win_rate, expectancy, max_drawdown,
                   top_no_trade_reason, current_equity, no_trade_counts_json,
                   created_at, updated_at
            FROM daily_metrics
            ORDER BY metric_date DESC
            LIMIT ?
        """

    import sqlite3 as _sqlite3
    import os as _os

    if DB_MODE != "postgres" and db_path:
        _db_dir = _os.path.dirname(db_path)
        if _db_dir:
            _os.makedirs(_db_dir, exist_ok=True)
        conn = _sqlite3.connect(db_path)
        try:
            cur = conn.execute(sql, (limit,))
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        finally:
            conn.close()
        return _deserialize_metrics(rows)

    with get_connection() as conn:
        cur = conn.execute(sql, (limit,))
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    return _deserialize_metrics(rows)


def _deserialize_metrics(rows: list[dict]) -> list[dict[str, Any]]:
    for row in rows:
        raw = row.get("no_trade_counts_json")
        if raw:
            try:
                row["no_trade_counts"] = json.loads(raw)
            except (TypeError, ValueError):
                row["no_trade_counts"] = {}
        else:
            row["no_trade_counts"] = {}
    return rows


# ---------------------------------------------------------------------------
# evaluation_state
# ---------------------------------------------------------------------------

def upsert_evaluation_state(
    evaluation_start_date: str,
    starting_equity: float,
    *,
    db_path: str | None = None,
) -> None:
    """Insert the evaluation-run marker (idempotent — ignores duplicates)."""
    if DB_MODE == "postgres":
        sql = """
            INSERT INTO evaluation_state (evaluation_start_date, starting_equity)
            VALUES (%s, %s)
            ON CONFLICT (evaluation_start_date) DO NOTHING
        """
    else:
        sql = """
            INSERT OR IGNORE INTO evaluation_state
                (evaluation_start_date, starting_equity)
            VALUES (?, ?)
        """

    import sqlite3 as _sqlite3
    import os as _os

    if DB_MODE != "postgres" and db_path:
        _db_dir = _os.path.dirname(db_path)
        if _db_dir:
            _os.makedirs(_db_dir, exist_ok=True)
        conn = _sqlite3.connect(db_path)
        try:
            conn.execute(sql, (evaluation_start_date, starting_equity))
            conn.commit()
        finally:
            conn.close()
        return

    with get_connection() as conn:
        conn.execute(sql, (evaluation_start_date, starting_equity))


def read_evaluation_state(
    db_path: str | None = None,
) -> dict[str, Any] | None:
    """Return the single evaluation-state row, or None if not yet created."""
    if DB_MODE == "postgres":
        sql = """
            SELECT evaluation_start_date, starting_equity, created_at, updated_at
            FROM evaluation_state
            ORDER BY id DESC
            LIMIT 1
        """
    else:
        sql = """
            SELECT evaluation_start_date, starting_equity, created_at, updated_at
            FROM evaluation_state
            ORDER BY id DESC
            LIMIT 1
        """

    import sqlite3 as _sqlite3
    import os as _os

    if DB_MODE != "postgres" and db_path:
        _db_dir = _os.path.dirname(db_path)
        if _db_dir:
            _os.makedirs(_db_dir, exist_ok=True)
        conn = _sqlite3.connect(db_path)
        try:
            cur = conn.execute(sql)
            cols = [d[0] for d in cur.description]
            row = cur.fetchone()
        finally:
            conn.close()
        return dict(zip(cols, row)) if row else None

    with get_connection() as conn:
        cur = conn.execute(sql)
        cols = [d[0] for d in cur.description]
        row = cur.fetchone()
    return dict(zip(cols, row)) if row else None
