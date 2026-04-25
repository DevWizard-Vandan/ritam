"""Deterministic intraday trade gate between agents and execution."""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from typing import Any, Callable

from src.trading.pcr_fetcher import fetch_nifty_pcr

IST = timezone(timedelta(hours=5, minutes=30))
CONFIDENCE_THRESHOLD = 0.65
VALID_TRENDING_REGIMES = {"trending_up", "trending_down"}
PCR_NEUTRAL_LOW = 0.8
PCR_NEUTRAL_HIGH = 1.3
PCR_MILD_LOW = 0.6
PCR_MILD_HIGH = 1.5
PCR_MILD_PENALTY = 0.1


def _parse_timestamp(timestamp: Any) -> datetime:
    if isinstance(timestamp, datetime):
        dt = timestamp
    elif isinstance(timestamp, str):
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    else:
        raise TypeError("timestamp must be a datetime or ISO-8601 string")

    if dt.tzinfo is None:
        return dt.replace(tzinfo=IST)
    return dt.astimezone(IST)


def _is_restricted_time(ts: datetime) -> bool:
    current = ts.time()
    return (time(9, 15) <= current < time(9, 30)) or (
        time(15, 0) <= current < time(15, 30)
    )


def _is_trending(regime: str) -> bool:
    normalized = (regime or "").strip().lower()
    return normalized in VALID_TRENDING_REGIMES


def _normalize_bias(analog_bias: str) -> str | None:
    normalized = (analog_bias or "").strip().lower()
    if normalized in {"buy_call", "bullish", "up", "long_call", "call", "buy"}:
        return "BUY_CALL"
    if normalized in {"buy_put", "bearish", "down", "long_put", "put", "sell"}:
        return "BUY_PUT"
    return None


def _pcr_adjustment(pcr_snapshot: dict[str, Any]) -> tuple[float, str]:
    if not pcr_snapshot.get("available", False):
        return 0.0, "PCR_UNAVAILABLE_NEUTRAL"

    pcr = float(pcr_snapshot.get("pcr", 1.0))
    if PCR_NEUTRAL_LOW <= pcr <= PCR_NEUTRAL_HIGH:
        return 0.0, "PCR_NEUTRAL"
    if PCR_MILD_LOW <= pcr < PCR_NEUTRAL_LOW or PCR_NEUTRAL_HIGH < pcr <= PCR_MILD_HIGH:
        return -PCR_MILD_PENALTY, "PCR_MILD_PENALTY"
    return 0.0, "PCR_EXTREME"


def _pcr_details(pcr_snapshot: dict[str, Any], now: datetime) -> dict[str, Any]:
    fetched_at_raw = pcr_snapshot.get("fetched_at")
    cache_age_seconds = pcr_snapshot.get("cache_age_seconds")
    is_stale = bool(pcr_snapshot.get("is_stale", False))
    if cache_age_seconds is None and fetched_at_raw:
        try:
            fetched_at = datetime.fromisoformat(str(fetched_at_raw))
            if fetched_at.tzinfo is None:
                fetched_at = fetched_at.replace(tzinfo=IST)
            else:
                fetched_at = fetched_at.astimezone(IST)
            cache_age_seconds = max(0.0, (now - fetched_at).total_seconds())
            is_stale = is_stale or cache_age_seconds > 30
        except ValueError:
            cache_age_seconds = None

    return {
        "pcr_value": float(pcr_snapshot.get("pcr", 1.0)),
        "pcr_available": bool(pcr_snapshot.get("available", False)),
        "pcr_is_stale": is_stale,
        "pcr_cache_age_seconds": cache_age_seconds,
        "pcr_fetched_at": fetched_at_raw,
    }


def evaluate_trade(
    regime: str,
    analog_bias: str,
    confidence: float,
    timestamp: Any,
    *,
    pcr_fetcher: Callable[[], dict[str, Any]] = fetch_nifty_pcr,
) -> dict[str, Any]:
    """Return a deterministic gate decision for intraday execution."""
    ts = _parse_timestamp(timestamp)
    original_confidence = round(float(confidence), 4)
    details: dict[str, Any] = {
        "timestamp": ts.isoformat(),
        "regime": regime,
        "analog_bias": analog_bias,
        "confidence_original": original_confidence,
        "confidence_adjusted": original_confidence,
        "threshold": CONFIDENCE_THRESHOLD,
    }

    if not _is_trending(regime):
        return {
            "decision": "NO_TRADE",
            "reason_code": "REGIME_BLOCK",
            "reason": f"REGIME_BLOCK: regime '{regime}' is not a valid trending regime",
            "signal": None,
            "details": details,
        }

    if _is_restricted_time(ts):
        return {
            "decision": "NO_TRADE",
            "reason_code": "TIME_BLOCK",
            "reason": f"TIME_BLOCK: timestamp {ts.isoformat()} is inside a restricted market window",
            "signal": None,
            "details": details,
        }

    signal = _normalize_bias(analog_bias)
    if signal is None:
        return {
            "decision": "NO_TRADE",
            "reason_code": "UNKNOWN_ANALOG_BIAS",
            "reason": f"UNKNOWN_ANALOG_BIAS: unsupported analog bias '{analog_bias}'",
            "signal": None,
            "details": details,
        }

    pcr_snapshot = pcr_fetcher()
    details.update(_pcr_details(pcr_snapshot, ts))
    pcr_adjustment, pcr_code = _pcr_adjustment(pcr_snapshot)
    effective_confidence = round(max(0.0, original_confidence + pcr_adjustment), 4)

    details.update(
        {
            "signal_candidate": signal,
            "pcr_snapshot": pcr_snapshot,
            "confidence_penalty": round(pcr_adjustment, 4),
            "confidence_adjusted": effective_confidence,
            "pcr_policy": pcr_code,
        }
    )

    if pcr_code == "PCR_EXTREME":
        return {
            "decision": "NO_TRADE",
            "reason_code": pcr_code,
            "reason": f"{pcr_code}: PCR {float(pcr_snapshot.get('pcr', 1.0)):.2f} is outside the allowed band",
            "signal": None,
            "details": details,
        }

    if effective_confidence < CONFIDENCE_THRESHOLD:
        return {
            "decision": "NO_TRADE",
            "reason_code": "LOW_EFFECTIVE_CONFIDENCE",
            "reason": (
                f"LOW_EFFECTIVE_CONFIDENCE: effective confidence {effective_confidence:.2f} "
                f"is below threshold {CONFIDENCE_THRESHOLD:.2f}"
            ),
            "signal": None,
            "details": details,
        }

    return {
        "decision": "TRADE",
        "reason_code": "TRADE_ALLOWED",
        "reason": (
            f"TRADE_ALLOWED: regime '{regime}', analog bias '{analog_bias}', "
            f"effective confidence {effective_confidence:.2f}, PCR policy {pcr_code}"
        ),
        "signal": signal,
        "details": details,
    }
