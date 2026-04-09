"""
Kite-compatible market data client backed by yfinance.

This module preserves the existing `get_client()` entrypoint and the subset of
the Kite client interface currently used by the codebase so we can swap in the
real Zerodha client later without touching downstream callers.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pandas as pd
import pytz
import yfinance as yf
from loguru import logger

from src.config import settings

IST = pytz.timezone(settings.TIMEZONE)

# Zerodha index tokens used by the current codebase. They resolve to yfinance
# symbols until a real Kite Connect integration is available.
INSTRUMENT_TOKEN_TO_TICKER = {
    256265: "^NSEI",
    260105: "^NSEBANK",
}

INTERVAL_TO_YFINANCE = {
    "minute": ("1m", timedelta(minutes=1)),
    "3minute": ("5m", timedelta(minutes=5)),
    "5minute": ("5m", timedelta(minutes=5)),
    "10minute": ("15m", timedelta(minutes=15)),
    "15minute": ("15m", timedelta(minutes=15)),
    "30minute": ("30m", timedelta(minutes=30)),
    "60minute": ("60m", timedelta(hours=1)),
    "day": ("1d", timedelta(days=1)),
}


def _coerce_datetime(value: datetime | str) -> datetime:
    """Normalize strings and naive datetimes into IST-aware datetimes."""
    normalized = pd.Timestamp(value).to_pydatetime()
    if normalized.tzinfo is None:
        return IST.localize(normalized)
    return normalized.astimezone(IST)


def _resolve_ticker(instrument_token: int) -> str:
    ticker = INSTRUMENT_TOKEN_TO_TICKER.get(instrument_token)
    if ticker is None:
        raise ValueError(f"Unsupported instrument token: {instrument_token}")
    return ticker


class YFinanceKiteClient:
    """Small adapter that mimics the Kite methods used by the repo today."""

    def __init__(self, api_key: str = "", access_token: str = "") -> None:
        self.api_key = api_key
        self.access_token = access_token

    def set_access_token(self, access_token: str) -> None:
        self.access_token = access_token
        logger.debug("Updated compatibility client access token")

    def historical_data(
        self,
        instrument_token: int,
        from_date: datetime | str,
        to_date: datetime | str,
        interval: str,
        continuous: bool = False,
        oi: bool = False,
    ) -> list[dict[str, Any]]:
        """Return Kite-shaped OHLCV candles for the requested instrument."""
        del continuous, oi

        try:
            ticker = _resolve_ticker(instrument_token)
            start_dt = _coerce_datetime(from_date)
            end_dt = _coerce_datetime(to_date)
            yf_interval, end_padding = INTERVAL_TO_YFINANCE[interval]
        except KeyError:
            logger.exception("Unsupported interval requested: {}", interval)
            return []
        except Exception:
            logger.exception("Failed to prepare historical data request")
            return []

        try:
            frame = yf.download(
                tickers=ticker,
                start=start_dt,
                end=end_dt + end_padding,
                interval=yf_interval,
                auto_adjust=False,
                progress=False,
                threads=False,
            )
        except Exception:
            logger.exception("yfinance download failed for {}", ticker)
            return []

        if frame.empty:
            logger.warning(
                "No market data returned for {} between {} and {}",
                ticker,
                start_dt.isoformat(),
                end_dt.isoformat(),
            )
            return []

        candles: list[dict[str, Any]] = []
        for timestamp, row in frame.iterrows():
            candle_time = _coerce_datetime(timestamp)
            candles.append(
                {
                    "date": candle_time,
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": 0 if pd.isna(row["Volume"]) else int(row["Volume"]),
                }
            )

        logger.info(
            "Fetched {} {} candles for {} via yfinance",
            len(candles),
            interval,
            ticker,
        )
        return candles


def get_client() -> YFinanceKiteClient:
    """Return a Kite-compatible client backed by yfinance."""
    client = YFinanceKiteClient(
        api_key=settings.KITE_API_KEY,
        access_token=settings.KITE_ACCESS_TOKEN,
    )
    logger.info("Using yfinance-backed Kite compatibility client")
    return client
