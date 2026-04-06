"""
OHLCV data fetcher — historical + live candle ingestion from Zerodha Kite.
"""
from datetime import datetime, timedelta
import pytz
from kiteconnect import KiteConnect
from src.data.kite_client import get_client
from src.data.db import write_candles
from src.config import settings
from loguru import logger

IST = pytz.timezone(settings.TIMEZONE)


def fetch_historical(symbol: str = "NSE:NIFTY 50", years: int = 10):
    """Fetch minute-candle historical data and store in DB."""
    kite = get_client()
    end = datetime.now(IST)
    start = end - timedelta(days=365 * years)
    logger.info(f"Fetching historical data for {symbol} from {start.date()} to {end.date()}")
    candles_raw = kite.historical_data(
        instrument_token=256265,  # Nifty 50 token
        from_date=start,
        to_date=end,
        interval="minute"
    )
    candles = [{
        "timestamp_ist": c["date"].isoformat(),
        "open": c["open"], "high": c["high"],
        "low": c["low"], "close": c["close"], "volume": c["volume"]
    } for c in candles_raw]
    write_candles(symbol, candles)
    logger.info(f"Saved {len(candles)} candles for {symbol}")


def fetch_latest_candle(symbol: str = "NSE:NIFTY 50"):
    """Fetch the most recent minute candle."""
    kite = get_client()
    now = datetime.now(IST)
    candles_raw = kite.historical_data(
        instrument_token=256265,
        from_date=now - timedelta(minutes=5),
        to_date=now,
        interval="minute"
    )
    if candles_raw:
        c = candles_raw[-1]
        candles = [{"timestamp_ist": c["date"].isoformat(),
                    "open": c["open"], "high": c["high"],
                    "low": c["low"], "close": c["close"], "volume": c["volume"]}]
        write_candles(symbol, candles)
