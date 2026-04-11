"""OHLCV data fetcher for historical + live candle ingestion via yfinance-backed Kite client."""
from __future__ import annotations

from datetime import datetime, time, timedelta

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from loguru import logger

from src.config import settings
from src.data.db import write_candles
from src.data.kite_client import get_client

IST = pytz.timezone(settings.TIMEZONE)
FETCH_TICKER = "^NSEI"
NIFTY_TOKEN = 256265
BANKNIFTY_TOKEN = 260105
DB_SYMBOL = settings.NIFTY_SYMBOL
MARKET_OPEN = time(9, 15)
MARKET_CLOSE = time(15, 30)


def _date_chunks(start: datetime, end: datetime, chunk_days: int = 1800):
    """Yield contiguous (chunk_start, chunk_end) pairs to stay below the 2000-day API limit."""
    if chunk_days <= 0:
        raise ValueError("chunk_days must be a positive integer")
    cursor = start
    while cursor < end:
        chunk_end = min(cursor + timedelta(days=chunk_days), end)
        yield cursor, chunk_end
        cursor = chunk_end


def _get_token_for_symbol(symbol: str) -> int:
    _TOKEN_MAP = {
        "NSE:NIFTY 50": NIFTY_TOKEN,
        "NSE:NIFTY BANK": BANKNIFTY_TOKEN,
    }
    if symbol not in _TOKEN_MAP:
        raise ValueError(f"Unsupported symbol: '{symbol}'. Supported: {list(_TOKEN_MAP.keys())}")
    return _TOKEN_MAP[symbol]


def _candle_to_record(candle: dict, symbol: str) -> dict:
    """Normalize a Kite-shaped candle into DB payload format."""
    return {
        "symbol": symbol,
        "timestamp_ist": candle["date"].astimezone(IST).isoformat(),
        "open": candle["open"],
        "high": candle["high"],
        "low": candle["low"],
        "close": candle["close"],
        "volume": candle["volume"],
    }


def fetch_historical_candles(
    symbol: str = DB_SYMBOL,
    from_date: str | None = None,
    to_date: str | None = None,
    interval: str = "day",
) -> int:
    """Fetch OHLCV candles and store them in SQLite."""
    from src.data.db import init_db
    init_db()

    kite = get_client()

    if from_date:
        start = IST.localize(datetime.strptime(from_date, "%Y-%m-%d"))
    else:
        start = IST.localize(datetime(2000, 1, 1, 0, 0, 0))

    if to_date:
        end = IST.localize(datetime.strptime(to_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59))
    else:
        end = datetime.now(IST)

    token = _get_token_for_symbol(symbol)

    logger.info(
        "Fetching historical {} candles for DB symbol {} (token {})",
        interval,
        symbol,
        token
    )

    candles_raw: list = []
    _yf_fallback: "YFinanceKiteClient | None" = None

    try:
        from kiteconnect.exceptions import KiteException as _KiteException
    except Exception:  # kiteconnect not installed or different layout
        _KiteException = Exception  # type: ignore[assignment,misc]

    for chunk_start, chunk_end in _date_chunks(start, end):
        logger.info("Fetching chunk {} → {}", chunk_start.date(), chunk_end.date())
        try:
            chunk = kite.historical_data(
                instrument_token=token,
                from_date=chunk_start,
                to_date=chunk_end,
                interval=interval,
            )
        except _KiteException as exc:
            logger.warning(
                "Kite historical_data failed for chunk {} → {}: {}. Falling back to yfinance.",
                chunk_start.date(),
                chunk_end.date(),
                exc,
            )
            from src.data.kite_client import YFinanceKiteClient
            if _yf_fallback is None:
                _yf_fallback = YFinanceKiteClient()
            chunk = _yf_fallback.historical_data(
                instrument_token=token,
                from_date=chunk_start,
                to_date=chunk_end,
                interval=interval,
            )
        if not chunk:
            logger.warning(
                "Empty response for chunk {} → {}; some candles may be missing",
                chunk_start.date(),
                chunk_end.date(),
            )
        candles_raw.extend(chunk)
    records = [_candle_to_record(candle, symbol) for candle in candles_raw]

    if not records:
        logger.warning("No historical candles returned for {}", symbol)
        return 0

    write_candles(symbol, records)
    logger.info(
        "Stored {} historical daily candles for {} ({} -> {})",
        len(records),
        symbol,
        start.date(),
        end.date(),
    )
    return len(records)


def fetch_intraday_candles(symbol: str = DB_SYMBOL) -> int:
    """Fetch today's 1-minute candles between 09:15 and 15:30 IST and store them."""
    now = datetime.now(IST)
    if now.time() < MARKET_OPEN:
        logger.info("Market has not opened yet in IST; skipping intraday fetch")
        return 0
    if now.time() > MARKET_CLOSE:
        logger.info("Market is closed in IST; skipping intraday fetch")
        return 0

    today_open = IST.localize(datetime.combine(now.date(), MARKET_OPEN))
    to_time = now
    kite = get_client()
    candles_raw = kite.historical_data(
        instrument_token=NIFTY_TOKEN,
        from_date=today_open,
        to_date=to_time,
        interval="minute",
    )
    records = [_candle_to_record(candle, symbol) for candle in candles_raw]

    if not records:
        logger.warning("No intraday minute candles returned for {}", symbol)
        return 0

    write_candles(symbol, records)
    logger.info(
        "Stored {} intraday minute candles for {} ({} -> {})",
        len(records),
        symbol,
        today_open.isoformat(),
        to_time.isoformat(),
    )
    return len(records)


def start_live_feed() -> BackgroundScheduler:
    """Start APScheduler job that fetches intraday candles every 60 seconds on weekdays."""
    scheduler = BackgroundScheduler(timezone=IST)
    scheduler.add_job(
        fetch_intraday_candles,
        trigger="cron",
        day_of_week="mon-fri",
        hour="9-15",
        minute="*",
        second="0",
        id="nifty_intraday_feed",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    logger.info("Live feed scheduler started for 60-second intraday candle ingestion")
    return scheduler
