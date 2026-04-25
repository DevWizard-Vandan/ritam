"""Data freshness checks for live market ingestion."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from src.config.settings import settings
from src.data.db import read_candles, read_intraday_candles
from src.data.kite_client import fetch_current_price, get_client

IST = timezone(timedelta(hours=5, minutes=30))


def _now_ist() -> datetime:
    return datetime.now(IST)


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        return dt.replace(tzinfo=IST)
    return dt.astimezone(IST)


def _latest_candle(symbol: str) -> tuple[dict[str, Any] | None, str | None]:
    intraday = read_intraday_candles(symbol, limit=1)
    if intraday:
        return intraday[-1], "intraday_candles"

    daily = read_candles(symbol, "2000-01-01", _now_ist().isoformat(), limit=1)
    if daily:
        return daily[-1], "candles"

    return None, None


def check_data_freshness(
    symbol: str = settings.INTRADAY_SYMBOL,
    *,
    stale_after_seconds: int = 120,
    now_fn: Any = _now_ist,
) -> dict[str, Any]:
    """
    Inspect the latest stored market candle and report freshness.

    Status is OK when the latest candle is newer than `stale_after_seconds`.
    """
    now = now_fn()
    candle, table_name = _latest_candle(symbol)
    client = get_client()
    data_source = "kite" if client.__class__.__module__.startswith("kiteconnect") else "yfinance"

    if candle is None:
        quote = fetch_current_price(symbol)
        return {
            "status": "STALE",
            "data_source": data_source,
            "price_source": quote.get("source"),
            "last_candle_timestamp": None,
            "delay_seconds": None,
            "current_price": quote.get("price"),
            "current_price_fetched_at": quote.get("fetched_at"),
            "freshness_threshold_seconds": stale_after_seconds,
            "table": table_name,
            "reason": "no_candles_available",
        }

    last_timestamp = _parse_timestamp(candle.get("timestamp_ist"))
    delay_seconds = None
    if last_timestamp is not None:
        delay_seconds = max(0.0, (now - last_timestamp).total_seconds())

    quote = fetch_current_price(symbol)
    status = "OK" if delay_seconds is not None and delay_seconds <= stale_after_seconds else "STALE"

    return {
        "status": status,
        "data_source": data_source,
        "price_source": quote.get("source"),
        "last_candle_timestamp": last_timestamp.isoformat() if last_timestamp else None,
        "delay_seconds": round(delay_seconds, 2) if delay_seconds is not None else None,
        "current_price": quote.get("price"),
        "current_price_fetched_at": quote.get("fetched_at"),
        "freshness_threshold_seconds": stale_after_seconds,
        "table": table_name,
    }
