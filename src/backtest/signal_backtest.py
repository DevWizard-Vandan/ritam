"""Signal backtest engine for RL-weighted vs equal-weight evaluation."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
import json
import math
import sqlite3
from typing import Any

from src.config.settings import settings
from src.data.db import get_connection


@dataclass
class BacktestResult:
    from_date: str
    to_date: str
    total_trades: int
    rl_weighted: dict[str, Any]
    equal_weight: dict[str, Any]
    generated_at: str
    weekly_breakdown: list[dict[str, Any]] = field(default_factory=list)


class SignalBacktester:
    """Backtests resolved prediction signals from feedback_predictions."""

    def run(self, from_date: str, to_date: str, walk_forward: bool = False) -> BacktestResult:
        rows = self._load_rows(from_date=from_date, to_date=to_date)
        rl_metrics, eq_metrics, agent_accuracy = self._evaluate_rows(rows, weights=None)

        weekly_breakdown: list[dict[str, Any]] = []
        if walk_forward:
            weekly_breakdown = self._run_walk_forward(from_date=from_date, to_date=to_date)

        rl_metrics["per_agent_accuracy"] = agent_accuracy
        eq_metrics["per_agent_accuracy"] = agent_accuracy

        return BacktestResult(
            from_date=from_date,
            to_date=to_date,
            total_trades=rl_metrics["total_trades"],
            rl_weighted=rl_metrics,
            equal_weight=eq_metrics,
            generated_at=datetime.utcnow().isoformat(),
            weekly_breakdown=weekly_breakdown,
        )

    @staticmethod
    def to_dict(result: BacktestResult) -> dict[str, Any]:
        return asdict(result)

    def _load_rows(self, from_date: str, to_date: str) -> list[dict[str, Any]]:
        try:
            with get_connection() as conn:
                rows = conn.execute(
                    """
                    SELECT f.timestamp, f.signal, f.actual_return_pct, p.agent_signals
                    FROM feedback_predictions f
                    LEFT JOIN predictions p ON p.timestamp = f.timestamp
                    WHERE f.resolved = 1
                      AND f.timestamp >= ?
                      AND f.timestamp <= ?
                    ORDER BY f.timestamp ASC
                    """,
                    (from_date, to_date),
                ).fetchall()
        except sqlite3.OperationalError:
            return []

        return [
            {
                "timestamp": row[0],
                "signal": (row[1] or "").lower(),
                "actual_return_pct": float(row[2]) if row[2] is not None else None,
                "agent_signals": row[3],
            }
            for row in rows
        ]

    def _evaluate_rows(
        self,
        rows: list[dict[str, Any]],
        weights: dict[str, float] | None,
    ) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
        rl_pnls: list[float] = []
        eq_pnls: list[float] = []
        rl_dates: list[str] = []
        eq_dates: list[str] = []

        weighted_agent_scores: dict[str, dict[str, int]] = {}

        for row in rows:
            signal = row["signal"]
            actual = row["actual_return_pct"]
            if actual is None or signal == "hold" or signal not in {"buy", "sell"}:
                continue

            pnl_base = self._trade_pnl(signal=signal, actual_return_pct=actual)

            row_weights = self._weights_for_row(row, weights)
            rl_pnl = pnl_base * row_weights["rl"]
            eq_pnl = pnl_base * row_weights["equal"]

            rl_pnls.append(rl_pnl)
            eq_pnls.append(eq_pnl)
            rl_dates.append(row["timestamp"])
            eq_dates.append(row["timestamp"])

            self._track_agent_accuracy(
                weighted_agent_scores=weighted_agent_scores,
                row=row,
                actual_return_pct=actual,
            )

        rl_metrics = self._calculate_metrics(rl_dates, rl_pnls)
        eq_metrics = self._calculate_metrics(eq_dates, eq_pnls)
        per_agent_accuracy = self._format_agent_accuracy(weighted_agent_scores)

        return rl_metrics, eq_metrics, per_agent_accuracy

    def _run_walk_forward(self, from_date: str, to_date: str) -> list[dict[str, Any]]:
        rows = self._load_rows(from_date=from_date, to_date=to_date)
        if not rows:
            return []

        by_week: dict[tuple[int, int], list[dict[str, Any]]] = {}
        for row in rows:
            ts = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
            key = ts.isocalendar()[:2]  # year, week number
            by_week.setdefault((key[0], key[1]), []).append(row)

        ordered_weeks = sorted(by_week.keys())
        rolling_accuracy: dict[str, float] = {}
        breakdown: list[dict[str, Any]] = []

        for year, week in ordered_weeks:
            week_rows = by_week[(year, week)]
            weights = dict(rolling_accuracy) if rolling_accuracy else None
            rl, eq, per_agent = self._evaluate_rows(week_rows, weights=weights)
            breakdown.append(
                {
                    "year": year,
                    "week": week,
                    "from_date": week_rows[0]["timestamp"],
                    "to_date": week_rows[-1]["timestamp"],
                    "total_trades": rl["total_trades"],
                    "rl_weighted": rl,
                    "equal_weight": eq,
                }
            )

            if per_agent:
                rolling_accuracy = {
                    item["agent_name"]: item["accuracy"]
                    for item in per_agent
                    if item["total"] > 0
                }

        return breakdown

    def _weights_for_row(self, row: dict[str, Any], weights: dict[str, float] | None) -> dict[str, float]:
        parsed = self._parse_agent_signals(row.get("agent_signals"))
        active = [s for s in parsed if s.get("signal") in (-1, 1)]

        if not active:
            return {"rl": 1.0, "equal": 1.0}

        equal = 1.0
        if not weights:
            return {"rl": 1.0, "equal": equal}

        weighted_sum = 0.0
        denom = 0.0
        for signal_item in active:
            name = str(signal_item.get("agent_name", ""))
            sig = float(signal_item.get("signal", 0))
            confidence = float(signal_item.get("confidence", 1.0) or 1.0)
            agent_weight = float(weights.get(name, 0.5))
            weighted_sum += sig * confidence * agent_weight
            denom += abs(sig * confidence)

        if denom == 0:
            return {"rl": 1.0, "equal": equal}

        strength = abs(weighted_sum / denom)
        return {"rl": max(0.0, min(1.0, strength)), "equal": equal}

    @staticmethod
    def _parse_agent_signals(raw: str | None) -> list[dict[str, Any]]:
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, list) else []
        except (json.JSONDecodeError, TypeError):
            return []

    @staticmethod
    def _trade_pnl(signal: str, actual_return_pct: float) -> float:
        lot_size = settings.PAPER_LOT_SIZE
        notional = lot_size * 100.0

        if signal == "buy":
            direction = 1.0
        elif signal == "sell":
            direction = -1.0
        else:
            return 0.0

        return direction * (actual_return_pct / 100.0) * notional

    @staticmethod
    def _track_agent_accuracy(
        weighted_agent_scores: dict[str, dict[str, int]],
        row: dict[str, Any],
        actual_return_pct: float,
    ) -> None:
        parsed = SignalBacktester._parse_agent_signals(row.get("agent_signals"))
        for signal_item in parsed:
            sig = signal_item.get("signal")
            if sig not in (-1, 1):
                continue

            name = str(signal_item.get("agent_name", "unknown"))
            bucket = weighted_agent_scores.setdefault(name, {"correct": 0, "total": 0})
            bucket["total"] += 1
            if (sig > 0 and actual_return_pct > 0) or (sig < 0 and actual_return_pct < 0):
                bucket["correct"] += 1

    @staticmethod
    def _format_agent_accuracy(weighted_agent_scores: dict[str, dict[str, int]]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for name, data in sorted(weighted_agent_scores.items()):
            total = data["total"]
            accuracy = (data["correct"] / total) if total > 0 else 0.0
            out.append(
                {
                    "agent_name": name,
                    "correct": data["correct"],
                    "total": total,
                    "accuracy": round(accuracy, 4),
                }
            )
        return out

    def _calculate_metrics(self, dates: list[str], pnls: list[float]) -> dict[str, Any]:
        if not pnls:
            return {
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "equity_curve": [],
                "total_trades": 0,
            }

        wins = sum(1 for p in pnls if p > 0)
        total_pnl = float(sum(pnls))
        equity_curve = []
        running = 0.0
        peak = 0.0
        max_dd = 0.0

        for date, pnl in zip(dates, pnls):
            running += pnl
            peak = max(peak, running)
            dd = peak - running
            max_dd = max(max_dd, dd)
            equity_curve.append(
                {
                    "date": date,
                    "cumulative_pnl": round(running, 2),
                }
            )

        mean_ret = sum(pnls) / len(pnls)
        variance = sum((x - mean_ret) ** 2 for x in pnls) / len(pnls)
        std_dev = math.sqrt(variance)
        sharpe = (mean_ret / std_dev) * math.sqrt(252) if std_dev > 0 else 0.0

        return {
            "win_rate": round(wins / len(pnls), 4),
            "total_pnl": round(total_pnl, 2),
            "sharpe_ratio": round(float(sharpe), 4),
            "max_drawdown": round(float(max_dd), 2),
            "equity_curve": equity_curve,
            "total_trades": len(pnls),
        }
