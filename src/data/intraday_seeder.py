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
    instruments = kite.instruments("NSE") if hasattr(kite, "instruments") else []
    token = next(
        (i["instrument_token"] for i in instruments
         if i.get("tradingsymbol") == symbol.replace("NSE:", "")),
        None
    )
    if not token:
        # Try index tokens — Nifty 50 index token is 256265
        # Hardcode fallback for NSE:NIFTY 50
        if "NIFTY 50" in symbol:
            token = 256265
        else:
            logger.error(f"Could not resolve token for {symbol}")
            return 0

    to_date = date.today()
    from_date = to_date - timedelta(days=days_back)

    logger.info(f"Seeding 15-min candles for {symbol} "
                f"from {from_date} to {to_date}")

    raw = kite.historical_data(
        instrument_token=token,
        from_date=from_date,
        to_date=to_date,
        interval="15minute",
        continuous=False,
        oi=False,
    )

    candles = []
    for r in raw:
        dt = r["date"]
        if hasattr(dt, "isoformat"):
            ts = dt.astimezone(ist).isoformat()
        else:
            ts = str(dt)
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
