"""NSE PCR fetcher with cookie warmup, retries, and short-lived caching."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any, Callable
import time

import requests
try:
    from loguru import logger
except ModuleNotFoundError:  # pragma: no cover - environment fallback
    import logging

    logger = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))
PCR_CACHE_TTL_SECONDS = 30
PCR_RETRY_ATTEMPTS = 3

_CACHE_LOCK = Lock()
_CACHE: dict[str, Any] | None = None


def _now_ist() -> datetime:
    return datetime.now(IST)


def _default_headers() -> dict[str, str]:
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.nseindia.com/option-chain",
        "X-Requested-With": "XMLHttpRequest",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }


def clear_pcr_cache() -> None:
    """Clear the in-memory PCR cache."""
    global _CACHE
    with _CACHE_LOCK:
        _CACHE = None


def _cache_hit(now: datetime, ttl_seconds: int) -> dict[str, Any] | None:
    with _CACHE_LOCK:
        if not _CACHE:
            return None
        cached_at = _CACHE["cached_at"]
        age_seconds = max(0.0, (now - cached_at).total_seconds())
        if age_seconds > ttl_seconds:
            return None
        snapshot = dict(_CACHE["snapshot"])
        snapshot["cached_at"] = cached_at.isoformat()
        snapshot["cache_age_seconds"] = round(age_seconds, 3)
        snapshot["is_stale"] = False
        return snapshot


def _store_cache(snapshot: dict[str, Any], cached_at: datetime) -> None:
    global _CACHE
    with _CACHE_LOCK:
        _CACHE = {"snapshot": dict(snapshot), "cached_at": cached_at}


def _build_fallback(
    reason: str,
    cached_at: datetime | None = None,
    *,
    is_stale: bool = False,
    cache_age_seconds: float | None = None,
) -> dict[str, Any]:
    now = cached_at or _now_ist()
    return {
        "available": False,
        "status": "unavailable",
        "reason": reason,
        "ce_oi": 0,
        "pe_oi": 0,
        "pcr": 1.0,
        "fetched_at": now.isoformat(),
        "cached_at": now.isoformat(),
        "cache_age_seconds": cache_age_seconds,
        "is_stale": is_stale,
    }


def _extract_oi(records: list[dict[str, Any]]) -> tuple[int, int]:
    ce_oi = 0
    pe_oi = 0
    for row in records:
        ce = row.get("CE") or {}
        pe = row.get("PE") or {}
        ce_oi += int(ce.get("openInterest") or 0)
        pe_oi += int(pe.get("openInterest") or 0)
    return ce_oi, pe_oi


def fetch_nifty_pcr(
    *,
    session_factory: Callable[[], requests.Session] = requests.Session,
    ttl_seconds: int = PCR_CACHE_TTL_SECONDS,
    max_retries: int = PCR_RETRY_ATTEMPTS,
    timeout_seconds: int = 15,
    sleep_fn: Callable[[float], None] = time.sleep,
    now_fn: Callable[[], datetime] = _now_ist,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """
    Fetch NIFTY option-chain PCR from NSE.

    Returns a structured snapshot with CE OI, PE OI, PCR, and availability.
    On failure, returns a neutral fallback snapshot and does not raise.
    """
    now = now_fn()
    if not force_refresh:
        cached = _cache_hit(now, ttl_seconds)
        if cached is not None:
            return cached

    headers = _default_headers()
    last_error: Exception | None = None
    stale_snapshot: dict[str, Any] | None = None
    stale_age_seconds: float | None = None

    with _CACHE_LOCK:
        if _CACHE:
            cached_at = _CACHE["cached_at"]
            age_seconds = max(0.0, (now - cached_at).total_seconds())
            if age_seconds > ttl_seconds:
                stale_snapshot = dict(_CACHE["snapshot"])
                stale_snapshot["cached_at"] = cached_at.isoformat()
                stale_age_seconds = round(age_seconds, 3)

    for attempt in range(1, max_retries + 1):
        session = session_factory()
        try:
            session.get("https://www.nseindia.com", timeout=timeout_seconds, headers=headers)
            session.get("https://www.nseindia.com/option-chain", timeout=timeout_seconds, headers=headers)
            response = session.get(
                "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY",
                timeout=timeout_seconds,
                headers=headers,
            )
            response.raise_for_status()
            payload = response.json()

            records = payload.get("records", {}).get("data", [])
            if not isinstance(records, list) or not records:
                fallback = _build_fallback("empty_records", now)
                _store_cache(fallback, now)
                return fallback

            ce_oi, pe_oi = _extract_oi(records)
            pcr = float(pe_oi) / float(ce_oi) if ce_oi > 0 else 1.0
            snapshot = {
                "available": True,
                "status": "ok",
                "reason": "ok",
                "ce_oi": ce_oi,
                "pe_oi": pe_oi,
                "pcr": round(pcr, 4),
                "fetched_at": now.isoformat(),
                "cached_at": now.isoformat(),
                "cache_age_seconds": 0.0,
                "is_stale": False,
            }
            _store_cache(snapshot, now)
            return snapshot
        except Exception as exc:  # pragma: no cover - retry path exercised with mocks
            last_error = exc
            logger.warning(f"NSE PCR fetch attempt {attempt}/{max_retries} failed: {exc}")
            if attempt < max_retries:
                sleep_fn(min(0.25 * attempt, 1.0))
        finally:
            close = getattr(session, "close", None)
            if callable(close):
                close()

    if stale_snapshot is not None:
        stale_snapshot.update(
            {
                "status": "stale",
                "reason": f"stale_cache_fallback: {last_error}",
                "is_stale": True,
                "cache_age_seconds": stale_age_seconds,
            }
        )
        return stale_snapshot

    fallback = _build_fallback(f"fetch_failed: {last_error}", now)
    _store_cache(fallback, now)
    return fallback
