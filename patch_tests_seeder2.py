import sys

with open('tests/data/test_intraday_seeder.py', 'r') as f:
    content = f.read()

search_block = """    assert "No candles returned" in caplog.text"""
replace_block = """    assert any("No candles returned" in record.message for record in caplog.records)"""

content = content.replace(search_block, replace_block)

search_block2 = """            # Just create dummy candles for whatever range
            candles = []
            for i in range(100):
                dt = from_date + datetime.timedelta(minutes=15*i)
                # Ensure it is a valid datetime or date
                if not hasattr(dt, "isoformat"):
                    dt = datetime.datetime.combine(dt, datetime.time(9, 15))

                candles.append({"""

replace_block2 = """            # Just create dummy candles for whatever range
            import datetime as dt_mod
            import pytz
            ist = pytz.timezone("Asia/Kolkata")
            candles = []
            for i in range(100):
                # Always create datetime object to prevent astimezone err
                if isinstance(from_date, dt_mod.datetime):
                    dt = from_date + dt_mod.timedelta(minutes=15*i)
                else:
                    dt = dt_mod.datetime.combine(from_date, dt_mod.time(9, 15)) + dt_mod.timedelta(minutes=15*i)
                dt = ist.localize(dt)

                candles.append({"""

content = content.replace(search_block2, replace_block2)

with open('tests/data/test_intraday_seeder.py', 'w') as f:
    f.write(content)

print("Applied fix for test_intraday_seeder")
