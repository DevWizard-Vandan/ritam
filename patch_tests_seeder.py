import sys

with open('tests/data/test_intraday_seeder.py', 'r') as f:
    content = f.read()

append_block = """

@patch("src.data.kite_client.get_client")
def test_seed_intraday_history_zero_candles(mock_get_client, caplog):
    mock_kite = MagicMock()
    mock_get_client.return_value = mock_kite
    mock_kite.instruments.return_value = [{"instrument_token": 256265, "tradingsymbol": "NIFTY 50"}]

    mock_kite.historical_data.return_value = []

    inserted = seed_intraday_history("NSE:NIFTY 50", days_back=1)

    assert inserted == 0
    assert "No candles returned" in caplog.text

@patch("src.data.kite_client.get_client")
def test_seed_intraday_history_chunked_fetch(mock_get_client):
    mock_kite = MagicMock()
    mock_get_client.return_value = mock_kite
    mock_kite.instruments.return_value = [{"instrument_token": 256265, "tradingsymbol": "NIFTY 50"}]

    import datetime

    # 100 candles per chunk, we will pretend we fetch 2 chunks
    def mock_historical_data(**kwargs):
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
        return candles

    mock_kite.historical_data.side_effect = mock_historical_data

    # days_back=60 will be split into at least 2 chunks (45 days max per chunk)
    inserted = seed_intraday_history("NSE:NIFTY 50", days_back=60)

    # Total should be around 200 (2 chunks * 100 candles) since unique timestamps are used.
    # We just ensure it's successfully chunked and inserted.
    assert mock_kite.historical_data.call_count >= 2
    assert inserted >= 200
"""

content += append_block

with open('tests/data/test_intraday_seeder.py', 'w') as f:
    f.write(content)
print("Updated test_intraday_seeder.py")
