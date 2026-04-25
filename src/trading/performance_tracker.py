"""SQLite-backed performance tracker for expectancy and drawdown."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from src.config.settings import settings
from src.data.db import read_evaluation_state, upsert_evaluation_state

IST = timezone(timedelta(hours=5, minutes=30))


def _now_ist() -> datetime:
    return datetime.now(IST)


def _ensure_dir(db_path: str) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)


@dataclass
class TradeEntry:
    trade_id: str
    timestamp: str
    trade_date: str
    signal: str | None
    confidence: float | None
    regime: str | None
    decision: str
    reason: str | None
    reason_code: str | None
    pcr_value: float | None
    profit_loss: float | None
    equity_after: float | None


class PerformanceTracker:
    """Track trade expectancy, win rate, and drawdown locally in SQLite."""

    def __init__(self, db_path: str | None = None, starting_equity: float | None = None):
        self.db_path = db_path or settings.DB_PATH
        persisted_state = read_evaluation_state(self.db_path)
        if starting_equity is not None:
            self.starting_equity = float(starting_equity)
        elif persisted_state is not None:
            self.starting_equity = float(persisted_state["starting_equity"])
        else:
            self.starting_equity = float(settings.PAPER_CAPITAL)
        if persisted_state is None:
            from datetime import datetime, timezone, timedelta

            ist = timezone(timedelta(hours=5, minutes=30))
            upsert_evaluation_state(
                datetime.now(ist).date().isoformat(),
                self.starting_equity,
                db_path=self.db_path,
            )
        self._equity = self.starting_equity
        self._peak_equity = self.starting_equity
        self._trades: list[TradeEntry] = []
        self._decisions: list[TradeEntry] = []
        self._decision_counts: dict[tuple[str, str], int] = {}
        _ensure_dir(self.db_path)
        self._init_db()
        self._load_history()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS trade_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id TEXT UNIQUE,
                    timestamp TEXT NOT NULL,
                    trade_date TEXT NOT NULL,
                    signal TEXT,
                    confidence REAL,
                    regime TEXT,
                    decision TEXT NOT NULL,
                    reason TEXT,
                    reason_code TEXT,
                    pcr_value REAL,
                    profit_loss REAL,
                    equity_after REAL,
                    cumulative_equity_after_trade REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            try:
                conn.execute(
                    "ALTER TABLE trade_performance ADD COLUMN cumulative_equity_after_trade REAL"
                )
            except sqlite3.OperationalError:
                pass
            for ddl in (
                "ALTER TABLE trade_performance ADD COLUMN reason_code TEXT",
                "ALTER TABLE trade_performance ADD COLUMN pcr_value REAL",
            ):
                try:
                    conn.execute(ddl)
                except sqlite3.OperationalError:
                    pass
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_trade_performance_trade_date
                ON trade_performance(trade_date)
                """
            )
            conn.commit()

    def _load_history(self) -> None:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT trade_id, timestamp, trade_date, signal, confidence, regime, decision,
                       reason, reason_code, pcr_value, profit_loss, equity_after
                FROM trade_performance
                ORDER BY id ASC
                """
            ).fetchall()

        self._trades.clear()
        self._decisions.clear()
        self._decision_counts.clear()
        self._equity = self.starting_equity
        self._peak_equity = self.starting_equity
        for row in rows:
            entry = TradeEntry(*row)
            if entry.decision == "TRADE" and entry.profit_loss is not None:
                self._trades.append(entry)
                self._equity = float(
                    entry.equity_after if entry.equity_after is not None else self._equity + float(entry.profit_loss)
                )
                self._peak_equity = max(self._peak_equity, self._equity)
            else:
                self._decisions.append(entry)

    @staticmethod
    def _normalize_trade_signal(signal: str | None) -> str | None:
        if signal is None:
            return None
        normalized = signal.strip().upper()
        if normalized in {"CALL", "BUY_CALL", "BUY_CALL_OPTION", "BUY"}:
            return "CALL"
        if normalized in {"PUT", "BUY_PUT", "BUY_PUT_OPTION", "SELL"}:
            return "PUT"
        return normalized

    def _persist_entry(self, entry: TradeEntry) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO trade_performance (
                    trade_id, timestamp, trade_date, signal, confidence, regime,
                    decision, reason, reason_code, pcr_value, profit_loss, equity_after, cumulative_equity_after_trade
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.trade_id,
                    entry.timestamp,
                    entry.trade_date,
                    entry.signal,
                    entry.confidence,
                    entry.regime,
                    entry.decision,
                    entry.reason,
                    entry.reason_code,
                    entry.pcr_value,
                    entry.profit_loss,
                    entry.equity_after,
                    entry.equity_after,
                ),
            )
            conn.commit()

    def record_trade(
        self,
        profit_loss: float,
        *,
        trade_id: str | None = None,
        signal: str | None = None,
        confidence: float | None = None,
        regime: str | None = None,
        timestamp: str | None = None,
        pcr_value: float | None = None,
        reason_code: str | None = None,
    ) -> dict[str, Any]:
        """Record a completed trade and update running equity state."""
        ts = _parse_timestamp(timestamp)
        trade_id = trade_id or uuid4().hex
        normalized_signal = self._normalize_trade_signal(signal)
        self._equity += float(profit_loss)
        self._peak_equity = max(self._peak_equity, self._equity)
        entry = TradeEntry(
            trade_id=trade_id,
            timestamp=ts.isoformat(),
            trade_date=ts.date().isoformat(),
            signal=normalized_signal,
            confidence=None if confidence is None else float(confidence),
            regime=regime,
            decision="TRADE",
            reason=None,
            reason_code=reason_code,
            pcr_value=pcr_value,
            profit_loss=float(profit_loss),
            equity_after=round(self._equity, 2),
        )
        self._trades.append(entry)
        self._persist_entry(entry)
        return {
            "trade_id": trade_id,
            "signal": normalized_signal,
            "pcr_value": pcr_value,
            "reason_code": reason_code,
            "equity_after": entry.equity_after,
            "cumulative_equity_after_trade": entry.equity_after,
            "profit_loss": entry.profit_loss,
        }

    def record_decision(
        self,
        decision: str,
        reason: str,
        *,
        trade_id: str | None = None,
        signal: str | None = None,
        confidence: float | None = None,
        regime: str | None = None,
        timestamp: str | None = None,
        sample_every: int = 5,
        pcr_value: float | None = None,
    ) -> dict[str, Any]:
        """Record a non-trade decision for gate diagnostics."""
        ts = _parse_timestamp(timestamp)
        entry = TradeEntry(
            trade_id=trade_id or uuid4().hex,
            timestamp=ts.isoformat(),
            trade_date=ts.date().isoformat(),
            signal=signal,
            confidence=None if confidence is None else float(confidence),
            regime=regime,
            decision=decision,
            reason=reason,
            reason_code=reason,
            pcr_value=pcr_value,
            profit_loss=None,
            equity_after=None,
        )
        self._decisions.append(entry)
        self._persist_entry(entry)
        key = (ts.date().isoformat(), reason)
        self._decision_counts[key] = self._decision_counts.get(key, 0) + 1
        occurrence = self._decision_counts[key]
        return {
            "trade_id": entry.trade_id,
            "decision": decision,
            "reason": reason,
            "pcr_value": pcr_value,
            "occurrence": occurrence,
            "sample_every": sample_every,
            "should_log": occurrence == 1 or (sample_every > 0 and occurrence % sample_every == 0),
        }

    def export_trade_log(self) -> list[dict[str, Any]]:
        """Return the full journal of trades and gate decisions in chronological order."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT trade_id, timestamp, trade_date, signal, confidence, regime, decision,
                       reason, reason_code, pcr_value, profit_loss, equity_after,
                       cumulative_equity_after_trade
                FROM trade_performance
                ORDER BY id ASC
                """
            ).fetchall()
        return [
            {
                "trade_id": row[0],
                "timestamp": row[1],
                "trade_date": row[2],
                "signal": row[3],
                "confidence": row[4],
                "regime": row[5],
                "decision": row[6],
                "reason": row[7],
                "reason_code": row[8] or row[7],
                "pcr_value": row[9],
                "profit_loss": row[10],
                "equity_after": row[11] if row[11] is not None else row[12],
                "cumulative_equity_after_trade": row[12],
            }
            for row in rows
        ]

    @staticmethod
    def _compute_drawdown(equity_curve: list[float]) -> float:
        peak = equity_curve[0] if equity_curve else 0.0
        max_drawdown = 0.0
        for equity in equity_curve:
            peak = max(peak, equity)
            if peak <= 0:
                continue
            drawdown = (peak - equity) / peak
            max_drawdown = max(max_drawdown, drawdown)
        return max_drawdown

    @staticmethod
    def _trade_metrics(pnls: list[float]) -> dict[str, float]:
        total = len(pnls)
        wins = [p for p in pnls if p > 0]
        losses = [abs(p) for p in pnls if p < 0]
        win_count = len(wins)
        loss_count = len(losses)
        win_rate = win_count / total if total else 0.0
        loss_rate = loss_count / total if total else 0.0
        avg_win = sum(wins) / win_count if win_count else 0.0
        avg_loss = sum(losses) / loss_count if loss_count else 0.0
        expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)
        return {
            "total_trades": total,
            "wins": win_count,
            "losses": loss_count,
            "win_rate": round(win_rate, 4),
            "avg_win": round(avg_win, 4),
            "avg_loss": round(avg_loss, 4),
            "expectancy": round(expectancy, 4),
        }

    def calculate_metrics(self) -> dict[str, Any]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT timestamp, trade_date, signal, confidence, regime, decision,
                       reason, profit_loss, equity_after, cumulative_equity_after_trade
                FROM trade_performance
                ORDER BY id ASC
                """
            ).fetchall()

        trade_rows = [row for row in rows if row[5] == "TRADE" and row[7] is not None]
        pnls = [float(row[7]) for row in trade_rows]
        equity_curve = [self.starting_equity]
        for pnl in pnls:
            equity_curve.append(equity_curve[-1] + pnl)

        trade_metrics = self._trade_metrics(pnls)
        max_drawdown = self._compute_drawdown(equity_curve)

        daily: dict[str, dict[str, Any]] = {}
        no_trade_count = 0
        for row in rows:
            trade_date = row[1]
            daily.setdefault(
                trade_date,
                {
                    "trades": 0,
                    "wins": 0,
                    "losses": 0,
                    "pnl": 0.0,
                    "_pnls": [],
                    "no_trade": 0,
                },
            )
            if row[5] == "TRADE" and row[7] is not None:
                pnl = float(row[7])
                bucket = daily[trade_date]
                bucket["trades"] += 1
                bucket["pnl"] += pnl
                bucket["_pnls"].append(pnl)
                if pnl > 0:
                    bucket["wins"] += 1
                elif pnl < 0:
                    bucket["losses"] += 1
            else:
                daily[trade_date]["no_trade"] += 1
                no_trade_count += 1

        for bucket in daily.values():
            trades = bucket["trades"]
            wins = bucket["wins"]
            losses = bucket["losses"]
            pnls_day = bucket.pop("_pnls")
            day_wins = [p for p in pnls_day if p > 0]
            day_losses = [abs(p) for p in pnls_day if p < 0]
            win_rate = wins / trades if trades else 0.0
            avg_win = sum(day_wins) / len(day_wins) if day_wins else 0.0
            avg_loss = sum(day_losses) / len(day_losses) if day_losses else 0.0
            bucket["win_rate"] = round(win_rate, 4)
            bucket["avg_win"] = round(avg_win, 4)
            bucket["avg_loss"] = round(avg_loss, 4)
            bucket["expectancy"] = round((win_rate * avg_win) - ((1 - win_rate) * avg_loss), 4)
            bucket["pnl"] = round(bucket["pnl"], 2)

        return {
            **trade_metrics,
            "max_drawdown": round(max_drawdown, 4),
            "max_drawdown_pct": round(max_drawdown * 100.0, 2),
            "equity_curve": [round(value, 2) for value in equity_curve],
            "ending_equity": round(equity_curve[-1] if equity_curve else self.starting_equity, 2),
            "daily": daily,
            "no_trade_events": no_trade_count,
            "total_events": len(rows),
        }


def _parse_timestamp(timestamp: str | None) -> datetime:
    if timestamp is None:
        return _now_ist().replace(microsecond=0)
    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        return dt.replace(tzinfo=IST)
    return dt.astimezone(IST)
