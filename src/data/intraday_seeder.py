from loguru import logger
from src.config import settings
from src.data.db import upsert_intraday_candles, get_latest_intraday_timestamp

def seed_intraday_history(
    symbol: str = None,
    days_back: int = None
) -> int:
    """
    Seeds intraday_candles table with 15-min OHLCV from Kite.
    Returns total candles inserted.
    Kite historical_data() allows max 60 days per call for 15min interval.
    """
    from datetime import datetime, timedelta, date
    import pytz

    symbol = symbol or settings.INTRADAY_SYMBOL
    days_back = days_back or settings.INTRADAY_LOOKBACK_DAYS
    ist = pytz.timezone("Asia/Kolkata")
    # Note: `get_kite` does not exist in `src.data.kite_client.py`, it's called `get_client`
    from src.data.kite_client import get_client
    kite = get_client()

    # Resolve instrument token for symbol
    if "NIFTY 50" in symbol:
        token = 256265
    else:
        instruments = kite.instruments("NSE") if hasattr(kite, "instruments") else []
        token = next(
            (i["instrument_token"] for i in instruments
             if i.get("tradingsymbol") == symbol.replace("NSE:", "")),
            None
        )
        if not token:
            logger.error(f"Could not resolve token for {symbol}")
            return 0

    end_date = date.today()
    start_date = end_date - timedelta(days=days_back)

    logger.info(f"Seeding 15-min candles for {symbol} "
                f"from {start_date} to {end_date}")

    raw_all = []
    current_start = start_date

    while current_start < end_date:
        current_end = min(current_start + timedelta(days=45), end_date)
        raw_chunk = kite.historical_data(
            instrument_token=token,
            from_date=current_start,
            to_date=current_end,
            interval="15minute",
            continuous=False,
            oi=False,
        )
        logger.info(f"Kite returned {len(raw_chunk)} raw candles for chunk {current_start} → {current_end}")
        raw_all.extend(raw_chunk)
        current_start = current_end + timedelta(days=1)

    if not raw_all:
        logger.warning(f"No candles returned for {symbol} in requested date range.")
        return 0

    candles = []
    seen = set()
    for r in raw_all:
        dt = r["date"]
        if hasattr(dt, "isoformat"):
            ts = dt.astimezone(ist).isoformat()
        else:
            ts = str(dt)

        if ts in seen:
            continue
        seen.add(ts)

        candles.append({
            "timestamp_ist": ts,
            "open": float(r["open"]),
            "high": float(r["high"]),
            "low": float(r["low"]),
            "close": float(r["close"]),
            "volume": int(r["volume"]),
        })

    inserted = upsert_intraday_candles(symbol, candles)
    logger.info(f"Seeded {inserted} new 15-min candles for {symbol}")
    return inserted


def sync_intraday_today(symbol: str = None) -> int:
    """
    Incremental sync — fetches only today's candles so far.
    Called by scheduler at market open each day.
    Returns count inserted.
    """
    from datetime import date, datetime, timedelta
    import pytz
    from src.data.kite_client import get_client

    symbol = symbol or settings.INTRADAY_SYMBOL
    ist = pytz.timezone("Asia/Kolkata")
    kite = get_client()

    if "NIFTY 50" in symbol:
        token = 256265
    else:
        instruments = kite.instruments("NSE") if hasattr(kite, "instruments") else []
        token = next(
            (i["instrument_token"] for i in instruments
             if i.get("tradingsymbol") == symbol.replace("NSE:", "")),
            None
        )
        if not token:
            logger.error(f"Token not found for {symbol}")
            return 0

    today = date.today()
    yesterday = today - timedelta(days=1)

    raw = kite.historical_data(
        instrument_token=token,
        from_date=yesterday,
        to_date=today,
        interval="15minute",
        continuous=False,
        oi=False,
    )
    print(len(raw))

    candles = []
    for r in raw:
        dt = r["date"]
        ts = dt.astimezone(ist).isoformat() if hasattr(dt, "astimezone") else str(dt)
        candles.append({
            "timestamp_ist": ts,
            "open": float(r["open"]),
            "high": float(r["high"]),
            "low": float(r["low"]),
            "close": float(r["close"]),
            "volume": int(r["volume"]),
        })

    inserted = upsert_intraday_candles(symbol, candles)
    logger.info(f"Incremental sync: {inserted} new candles for {symbol}")
    return inserted
