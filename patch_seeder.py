import sys

with open('src/data/intraday_seeder.py', 'r') as f:
    content = f.read()

import re

search_block = """    # Resolve instrument token for symbol
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
    return inserted"""

replace_block = """    # Resolve instrument token for symbol
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
    return inserted"""

if search_block in content:
    content = content.replace(search_block, replace_block)
    with open('src/data/intraday_seeder.py', 'w') as f:
        f.write(content)
    print("Replaced successfully")
else:
    print("Search block not found")
