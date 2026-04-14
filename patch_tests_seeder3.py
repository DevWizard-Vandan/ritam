import sys

with open('tests/data/test_intraday_seeder.py', 'r') as f:
    content = f.read()

search_block = """    @patch("src.data.kite_client.get_client")
    def test_seed_intraday_history_chunked_fetch(mock_get_client):"""

replace_block = """@patch("src.data.kite_client.get_client")
def test_seed_intraday_history_chunked_fetch(mock_get_client):"""

content = content.replace(search_block, replace_block)

search_block2 = """        def mock_historical_data(**kwargs):
            from_date = kwargs['from_date']
            # Just create dummy candles for whatever range
            candles = []
            for i in range(100):
                dt = from_date + datetime.timedelta(minutes=15*i)
                # Ensure it is a valid datetime or date
                if not hasattr(dt, "isoformat"):
                    dt = datetime.datetime.combine(dt, datetime.time(9, 15))

                candles.append({
                    "date": dt,
                    "open": 100, "high": 105, "low": 95, "close": 102, "volume": 1000
                })
            return candles"""

replace_block2 = """    def mock_historical_data(**kwargs):
        from_date = kwargs['from_date']
        # Just create dummy candles for whatever range
        import datetime as dt_mod
        import pytz
        ist = pytz.timezone("Asia/Kolkata")
        candles = []
        for i in range(100):
            if isinstance(from_date, dt_mod.datetime):
                dt = from_date + dt_mod.timedelta(minutes=15*i)
            else:
                dt = dt_mod.datetime.combine(from_date, dt_mod.time(9, 15)) + dt_mod.timedelta(minutes=15*i)
            dt = ist.localize(dt)
            candles.append({
                "date": dt,
                "open": 100, "high": 105, "low": 95, "close": 102, "volume": 1000
            })
        return candles"""

if search_block2 in content:
    content = content.replace(search_block2, replace_block2)
else:
    # it might have the previous patch logic
    import re
    content = re.sub(r"    def mock_historical_data\(.*?return candles", replace_block2, content, flags=re.DOTALL)

with open('tests/data/test_intraday_seeder.py', 'w') as f:
    f.write(content)

print("Applied fix 2 for test_intraday_seeder")
