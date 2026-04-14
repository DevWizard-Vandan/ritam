import sys

with open('src/data/intraday_seeder.py', 'r') as f:
    content = f.read()

search_block = """    if "NIFTY 50" in symbol:
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
    )"""

replace_block = """    if "NIFTY 50" in symbol:
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
    print(len(raw))"""

if search_block in content:
    content = content.replace(search_block, replace_block)
    with open('src/data/intraday_seeder.py', 'w') as f:
        f.write(content)
    print("Replaced sync successfully")
else:
    print("Search block not found")
