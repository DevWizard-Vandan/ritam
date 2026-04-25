"""Evaluation-mode observability and guardrails for the 4-week run."""

from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from src.config.settings import settings
from src.data.db_eval_helpers import (
    read_daily_metrics,
    read_evaluation_state,
    upsert_daily_metrics,
    upsert_evaluation_state,
)
from src.trading.evaluation_config import (
    CONFIDENCE_THRESHOLD,
    MAX_TRADES_PER_DAY,
    NO_TWEAK_MODE,
    PCR_BANDS,
    PCR_UNAVAILABLE_MAX_MINUTES,
)
from src.trading.pcr_fetcher import fetch_nifty_pcr
from src.trading.performance_tracker import PerformanceTracker

logger = logging.getLogger(__name__)
IST = timezone(timedelta(hours=5, minutes=30))

def _parse_ist(timestamp: str | datetime | None) -> datetime:
    if timestamp is None:
        return datetime.now(IST)
    if isinstance(timestamp, datetime):
        dt = timestamp
    else:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        return dt.replace(tzinfo=IST)
    return dt.astimezone(IST)


def _today_iso(now: datetime | None = None) -> str:
    return _parse_ist(now).date().isoformat()


def _query_rows_for_date(metric_date: str, db_path: str | None = None) -> list[dict[str, Any]]:
    tracker = PerformanceTracker(db_path or settings.DB_PATH)
    return [
        row
        for row in tracker.export_trade_log()
        if row["trade_date"] == metric_date
    ]


def _query_all_rows(db_path: str | None = None) -> list[dict[str, Any]]:
    tracker = PerformanceTracker(db_path or settings.DB_PATH)
    return tracker.export_trade_log()


def _compute_trade_metrics(pnls: list[float]) -> dict[str, float]:
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
        "trades": total,
        "win_rate": round(win_rate, 4),
        "avg_win": round(avg_win, 4),
        "avg_loss": round(avg_loss, 4),
        "expectancy": round(expectancy, 4),
    }


def _compute_drawdown(equity_curve: list[float]) -> float:
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    max_drawdown = 0.0
    for equity in equity_curve:
        peak = max(peak, equity)
        if peak <= 0:
            continue
        max_drawdown = max(max_drawdown, (peak - equity) / peak)
    return round(max_drawdown, 4)


def ensure_evaluation_state(db_path: str | None = None) -> dict[str, Any]:
    """Create the first-run evaluation marker if it does not exist."""
    tracker = PerformanceTracker(db_path or settings.DB_PATH)
    state = read_evaluation_state(db_path or settings.DB_PATH)
    if state is None:
        from datetime import datetime

        upsert_evaluation_state(
            datetime.now(IST).date().isoformat(),
            tracker.starting_equity,
            db_path=db_path or settings.DB_PATH,
        )
        state = read_evaluation_state(db_path or settings.DB_PATH)
    return state or {
        "evaluation_start_date": datetime.now(IST).date().isoformat(),
        "starting_equity": tracker.starting_equity,
    }


def validate_system_ready(
    db_path: str | None = None,
    scheduler: Any | None = None,
) -> dict[str, Any]:
    """Check runtime readiness before starting the 4-week evaluation run."""
    resolved_db_path = db_path or settings.DB_PATH
    checks: dict[str, Any] = {}

    try:
        tracker = PerformanceTracker(resolved_db_path)
        metrics = tracker.calculate_metrics()
        read_daily_metrics(limit=1, db_path=resolved_db_path)
        checks["database_connection"] = {
            "ok": True,
            "db_path": resolved_db_path,
            "ending_equity": metrics["ending_equity"],
        }
    except Exception as exc:  # pragma: no cover - defensive
        checks["database_connection"] = {"ok": False, "error": str(exc)}

    required_tables = {
        "trade_performance",
        "daily_metrics",
        "evaluation_state",
    }
    try:
        with tracker._connect() as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        existing_tables = {row[0] for row in rows}
        missing_tables = sorted(required_tables - existing_tables)
        checks["required_tables"] = {
            "ok": not missing_tables,
            "missing": missing_tables,
            "present": sorted(required_tables & existing_tables),
        }
    except Exception as exc:  # pragma: no cover - defensive
        checks["required_tables"] = {"ok": False, "error": str(exc)}

    try:
        pcr_snapshot = fetch_nifty_pcr(force_refresh=True, max_retries=1, timeout_seconds=5)
        checks["pcr_fetcher"] = {
            "ok": bool(pcr_snapshot.get("available", False)),
            "status": pcr_snapshot.get("status"),
            "pcr_value": pcr_snapshot.get("pcr"),
            "is_stale": pcr_snapshot.get("is_stale"),
        }
    except Exception as exc:  # pragma: no cover - defensive
        checks["pcr_fetcher"] = {"ok": False, "error": str(exc)}

    try:
        scheduler_running = bool(scheduler and getattr(scheduler, "running", False))
        job_ids = [getattr(job, "id", None) for job in scheduler.get_jobs()] if scheduler else []
        checks["scheduler"] = {
            "ok": scheduler_running and bool(job_ids),
            "running": scheduler_running,
            "active_jobs": [job_id for job_id in job_ids if job_id],
        }
    except Exception as exc:  # pragma: no cover - defensive
        checks["scheduler"] = {"ok": False, "error": str(exc)}

    checks["config"] = {
        "ok": (
            CONFIDENCE_THRESHOLD == 0.65
            and tuple(PCR_BANDS) == (0.8, 1.3)
            and NO_TWEAK_MODE is True
        ),
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "pcr_bands": tuple(PCR_BANDS),
        "no_tweak_mode": NO_TWEAK_MODE,
        "max_trades_per_day": MAX_TRADES_PER_DAY,
        "pcr_unavailable_max_minutes": PCR_UNAVAILABLE_MAX_MINUTES,
    }

    eval_state = read_evaluation_state(resolved_db_path)
    checks["evaluation_state"] = {
        "ok": eval_state is not None,
        "state": eval_state,
    }

    status = "READY" if all(section.get("ok", False) for section in checks.values()) else "NOT_READY"
    return {"status": status, "checks": checks}


def log_startup_summary(ready_report: dict[str, Any]) -> None:
    """Emit a single startup summary line for the evaluation run."""
    checks = ready_report.get("checks", {})
    logger.info(
        "System Ready:\n"
        f"- TradeGate: active\n"
        f"- PCR: {'working' if checks.get('pcr_fetcher', {}).get('ok') else 'degraded'}\n"
        f"- Scheduler: {'running' if checks.get('scheduler', {}).get('running') else 'stopped'}\n"
        f"- Evaluation mode: ON\n"
        f"- Config: {'frozen' if checks.get('config', {}).get('ok') else 'mismatch'}"
    )


def log_daily_snapshot(summary: dict[str, Any]) -> None:
    """Emit the day-end evaluation snapshot."""
    logger.info(
        "Daily Summary:\n"
        f"- trades: {summary.get('trades', 0)}\n"
        f"- win rate: {float(summary.get('win_rate', 0.0)) * 100:.2f}%\n"
        f"- expectancy: {float(summary.get('expectancy', 0.0)):.2f}\n"
        f"- drawdown: {float(summary.get('max_drawdown', 0.0)) * 100:.2f}%"
    )


def get_system_metrics(db_path: str | None = None) -> dict[str, Any]:
    """Return a lightweight snapshot of evaluation-mode performance."""
    tracker = PerformanceTracker(db_path or settings.DB_PATH)
    overall = tracker.calculate_metrics()
    today = _today_iso()
    rows = _query_rows_for_date(today, db_path=db_path)
    latest_daily_summary = read_daily_metrics(limit=1, db_path=db_path)
    no_trade_counts = Counter(
        (row["reason_code"] or row["reason"] or "UNKNOWN")
        for row in rows
        if row["decision"] == "NO_TRADE"
    )
    trades_today = sum(1 for row in rows if row["decision"] == "TRADE" and row["profit_loss"] is not None)

    return {
        "total_trades": overall["total_trades"],
        "win_rate": overall["win_rate"],
        "avg_win": overall["avg_win"],
        "avg_loss": overall["avg_loss"],
        "expectancy": overall["expectancy"],
        "max_drawdown": overall["max_drawdown"],
        "current_equity": overall["ending_equity"],
        "trades_today": trades_today,
        "no_trade_count_today": sum(no_trade_counts.values()),
        "no_trade_counts_today": dict(no_trade_counts),
        "top_no_trade_reason_today": no_trade_counts.most_common(1)[0][0] if no_trade_counts else None,
        "latest_daily_summary": latest_daily_summary[0] if latest_daily_summary else None,
        "no_tweak_mode": True,
    }


def export_trade_log(db_path: str | None = None) -> list[dict[str, Any]]:
    """Export the full evaluation journal for manual review."""
    return _query_all_rows(db_path=db_path)


def generate_daily_summary(metric_date: str | None = None, db_path: str | None = None) -> dict[str, Any]:
    """Compute and persist the end-of-day evaluation summary."""
    tracker = PerformanceTracker(db_path or settings.DB_PATH)
    metric_date = metric_date or _today_iso()
    rows = _query_rows_for_date(metric_date, db_path=db_path)
    trade_rows = [row for row in rows if row["decision"] == "TRADE" and row["profit_loss"] is not None]
    pnls = [float(row["profit_loss"]) for row in trade_rows]
    metrics = _compute_trade_metrics(pnls)

    equity_curve = [tracker.starting_equity]
    for pnl in pnls:
        equity_curve.append(equity_curve[-1] + pnl)

    no_trade_counts = Counter(
        (row["reason_code"] or row["reason"] or "UNKNOWN")
        for row in rows
        if row["decision"] == "NO_TRADE"
    )
    top_no_trade_reason = no_trade_counts.most_common(1)[0][0] if no_trade_counts else None
    current_equity = round(equity_curve[-1] if equity_curve else tracker.starting_equity, 2)
    max_drawdown = _compute_drawdown(equity_curve)

    summary = {
        "date": metric_date,
        "trades": metrics["trades"],
        "win_rate": metrics["win_rate"],
        "expectancy": metrics["expectancy"],
        "max_drawdown": max_drawdown,
        "top_reason_for_no_trade": top_no_trade_reason,
        "current_equity": current_equity,
        "no_trade_counts": dict(no_trade_counts),
    }

    upsert_daily_metrics(
        metric_date=metric_date,
        trades=summary["trades"],
        win_rate=summary["win_rate"],
        expectancy=summary["expectancy"],
        max_drawdown=summary["max_drawdown"],
        top_no_trade_reason=top_no_trade_reason,
        current_equity=current_equity,
        no_trade_counts_json=json.dumps(summary["no_trade_counts"], sort_keys=True),
        db_path=db_path,
    )
    return summary


class EvaluationSafetyGuard:
    """Runtime-only safety checks for evaluation mode."""

    def __init__(
        self,
        db_path: str | None = None,
        *,
        max_trades_per_day: int = MAX_TRADES_PER_DAY,
        pcr_unavailable_max_minutes: int = PCR_UNAVAILABLE_MAX_MINUTES,
    ):
        self.db_path = db_path or settings.DB_PATH
        self.max_trades_per_day = max_trades_per_day
        self.pcr_unavailable_max_minutes = pcr_unavailable_max_minutes
        self._tracker = PerformanceTracker(self.db_path)
        self._pcr_unavailable_since: datetime | None = None

    def evaluate_safety(
        self,
        trade_gate_result: dict[str, Any],
        timestamp: str | datetime,
    ) -> dict[str, Any]:
        now = _parse_ist(timestamp)
        details = trade_gate_result.get("details", {})
        pcr_available = bool(details.get("pcr_available", True))

        if not pcr_available:
            if self._pcr_unavailable_since is None:
                self._pcr_unavailable_since = now
            unavailable_minutes = (now - self._pcr_unavailable_since).total_seconds() / 60.0
            if unavailable_minutes > self.pcr_unavailable_max_minutes:
                return {
                    "skip": True,
                    "reason_code": "PCR_UNAVAILABLE_TOO_LONG",
                    "reason": (
                        f"PCR has been unavailable for {unavailable_minutes:.1f} minutes, "
                        f"exceeding safety cap {self.pcr_unavailable_max_minutes}."
                    ),
                    "details": {
                        "pcr_available": False,
                        "pcr_unavailable_since": self._pcr_unavailable_since.isoformat(),
                        "unavailable_minutes": round(unavailable_minutes, 2),
                    },
                }
        else:
            self._pcr_unavailable_since = None

        today = now.date().isoformat()
        rows = [
            row
            for row in self._tracker.export_trade_log()
            if row["trade_date"] == today and row["decision"] == "TRADE" and row["profit_loss"] is not None
        ]
        trade_count_today = len(rows)

        warn_trade_limit = trade_count_today >= self.max_trades_per_day
        return {
            "skip": False,
            "warn_trade_limit": warn_trade_limit,
            "trade_count_today": trade_count_today,
            "summary_cycle": False,
        }

    def build_cycle_summary(
        self,
        trade_gate_result: dict[str, Any],
        *,
        pcr_value: float | None,
        regime: str,
        confidence: float,
    ) -> str | None:
        return (
            "Cycle Summary:\n"
            f"- decision: {trade_gate_result.get('decision')}\n"
            f"- reason_code: {trade_gate_result.get('reason_code')}\n"
            f"- confidence: {confidence:.4f}\n"
            f"- pcr_value: {None if pcr_value is None else round(float(pcr_value), 4)}\n"
            f"- regime: {regime}"
        )
