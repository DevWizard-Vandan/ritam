"""SQLite-backed tracker for prediction outcomes and directional accuracy."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Any, Iterator


class PredictionTracker:
    """Persist predictions and compute accuracy metrics."""

    def __init__(self, db_path: str = "data/market.db"):
        self._use_uri = False
        self._memory_anchor: sqlite3.Connection | None = None

        if db_path == ":memory:":
            self.db_path = "file:feedback_tracker_test?mode=memory&cache=shared"
            self._use_uri = True
            self._memory_anchor = sqlite3.connect(self.db_path, uri=True)
        else:
            self.db_path = db_path
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, uri=self._use_uri)
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS feedback_predictions (
                    id INTEGER,
                    timestamp TEXT PRIMARY KEY,
                    signal TEXT,
                    sentiment_score REAL,
                    regime TEXT,
                    analog_similarity REAL,
                    actual_return_pct REAL,
                    resolved INTEGER DEFAULT 0,
                    source TEXT DEFAULT 'daily'
                )
                """
            )

            try:
                conn.execute("ALTER TABLE feedback_predictions ADD COLUMN source TEXT DEFAULT 'daily'")
            except sqlite3.OperationalError:
                pass
            conn.commit()

    def record_prediction(
        self,
        timestamp: str,
        signal: str,
        sentiment_score: float,
        regime: str,
        analog_similarity: float,
        source: str = "daily",
        agent_signals_json: str | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO feedback_predictions (
                    timestamp, signal, sentiment_score, regime, analog_similarity, source
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(timestamp) DO NOTHING
                """,
                (timestamp, signal, sentiment_score, regime, analog_similarity, source),
            )
            # Also update the main predictions table (schema consistency)
            try:
                conn.execute(
                    """
                    INSERT INTO predictions (
                        timestamp, predicted_direction, predicted_move_pct, confidence, timeframe_minutes, regime, source, agent_signals
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (timestamp, signal, 0.0, 0.5, 1440 if source == "daily" else 15, regime, source, agent_signals_json),
                )
            except sqlite3.OperationalError:
                try:
                    conn.execute("ALTER TABLE predictions ADD COLUMN agent_signals TEXT DEFAULT NULL")
                    conn.execute(
                        """
                        INSERT INTO predictions (
                            timestamp, predicted_direction, predicted_move_pct, confidence, timeframe_minutes, regime, source, agent_signals
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (timestamp, signal, 0.0, 0.5, 1440 if source == "daily" else 15, regime, source, agent_signals_json),
                    )
                except sqlite3.OperationalError:
                    pass

            conn.commit()

    def record_outcome(self, timestamp: str, actual_return_pct: float) -> None:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE feedback_predictions
                SET actual_return_pct = ?, resolved = 1
                WHERE timestamp = ?
                """,
                (actual_return_pct, timestamp),
            )
            if cursor.rowcount == 0:
                raise ValueError(f"No prediction found for timestamp: {timestamp}")
            conn.commit()

    @staticmethod
    def _is_correct(signal: str, actual_return_pct: float) -> bool:
        if signal == "buy":
            return actual_return_pct > 0
        if signal == "sell":
            return actual_return_pct < 0
        if signal == "hold":
            return True
        return False

    @staticmethod
    def _error(signal: str, actual_return_pct: float) -> float:
        if PredictionTracker._is_correct(signal, actual_return_pct):
            return 0.0
        return abs(actual_return_pct)

    def get_accuracy_stats(self, since: str | None = None) -> dict[str, Any]:
        with self._connect() as conn:
            query = """
                SELECT signal, actual_return_pct
                FROM feedback_predictions
                WHERE signal IN ('buy', 'sell', 'hold')
                  AND resolved = 1
                  AND actual_return_pct IS NOT NULL
            """
            params = []
            if since:
                query += " AND timestamp >= ?"
                params.append(since)

            rows = conn.execute(query, params).fetchall()

        total = len(rows)
        if total == 0:
            return {
                "total": 0,
                "correct": 0,
                "accuracy_pct": 0.0,
                "avg_error": 0.0,
                "by_signal": {
                    "buy": {"total": 0, "correct": 0, "accuracy_pct": 0.0},
                    "sell": {"total": 0, "correct": 0, "accuracy_pct": 0.0},
                    "hold": {"total": 0, "correct": 0, "accuracy_pct": 0.0},
                },
            }

        by_signal: dict[str, dict[str, float]] = {
            "buy": {"total": 0, "correct": 0, "accuracy_pct": 0.0},
            "sell": {"total": 0, "correct": 0, "accuracy_pct": 0.0},
            "hold": {"total": 0, "correct": 0, "accuracy_pct": 0.0},
        }

        correct = 0
        total_error = 0.0

        for signal, actual_return_pct in rows:
            by_signal[signal]["total"] += 1
            is_correct = self._is_correct(signal, float(actual_return_pct))
            if is_correct:
                correct += 1
                by_signal[signal]["correct"] += 1
            total_error += self._error(signal, float(actual_return_pct))

        for signal_stats in by_signal.values():
            sig_total = signal_stats["total"]
            signal_stats["accuracy_pct"] = round(signal_stats["correct"] / sig_total, 4) if sig_total else 0.0

        return {
            "total": total,
            "correct": correct,
            "accuracy_pct": round(correct / total, 4),
            "avg_error": round(total_error / total, 6),
            "by_signal": by_signal,
        }
