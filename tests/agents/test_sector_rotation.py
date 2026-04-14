import pytest
from src.agents.sector_rotation import SectorRotationAgent


SECTORS = {
    "BankNifty": "NSE:NIFTY BANK",
    "IT": "NSE:NIFTY IT",
    "Auto": "NSE:NIFTY AUTO",
    "FMCG": "NSE:NIFTY FMCG",
    "Pharma": "NSE:NIFTY PHARMA",
    "Metal": "NSE:NIFTY METAL",
}


def _make_mock_kite(quotes: dict):
    class MockKite:
        def quote(self, symbols):
            return quotes

    return MockKite()


def test_sector_rotation_collect_returns_pct_change(monkeypatch):
    """collect() computes pct_change per sector when kite responds correctly."""
    quotes = {}
    for sym in SECTORS.values():
        quotes[sym] = {"last_price": 101.0, "ohlc": {"close": 100.0}}

    mock_kite = _make_mock_kite(quotes)

    import src.data.kite_client as kite_mod
    monkeypatch.setattr(kite_mod, "get_client", lambda: mock_kite)

    agent = SectorRotationAgent()
    data = agent.collect()

    assert set(data.keys()) == set(SECTORS.keys())
    for val in data.values():
        assert abs(val - 1.0) < 0.01


def test_sector_rotation_collect_missing_symbol_defaults_zero(monkeypatch):
    """collect() returns 0.0 for sectors missing from the kite response."""
    mock_kite = _make_mock_kite({})  # empty quotes

    import src.data.kite_client as kite_mod
    monkeypatch.setattr(kite_mod, "get_client", lambda: mock_kite)

    agent = SectorRotationAgent()
    data = agent.collect()

    assert set(data.keys()) == set(SECTORS.keys())
    assert all(v == 0.0 for v in data.values())


def test_sector_rotation_collect_kite_exception_returns_neutral(monkeypatch):
    """When kite.quote() raises, collect() returns {sector: 0.0} gracefully."""
    class BrokenKite:
        def quote(self, symbols):
            raise ConnectionError("token expired")

    import src.data.kite_client as kite_mod
    monkeypatch.setattr(kite_mod, "get_client", lambda: BrokenKite())

    agent = SectorRotationAgent()
    data = agent.collect()

    assert set(data.keys()) == set(SECTORS.keys())
    assert all(v == 0.0 for v in data.values())


def test_sector_rotation_collect_get_client_raises_returns_neutral(monkeypatch):
    """When get_client() itself raises (e.g. auth), collect() degrades gracefully."""
    def broken_get_client():
        raise RuntimeError("auth failed")

    import src.data.kite_client as kite_mod
    monkeypatch.setattr(kite_mod, "get_client", broken_get_client)

    agent = SectorRotationAgent()
    data = agent.collect()

    assert set(data.keys()) == set(SECTORS.keys())
    assert all(v == 0.0 for v in data.values())


def test_sector_rotation_reason_bullish():
    """reason() returns bullish signal when weighted score > 0.3."""
    agent = SectorRotationAgent()
    data = {k: 2.0 for k in SECTORS}  # all sectors strongly up
    signal = agent.reason(data)
    assert signal.signal == 1
    assert signal.confidence > 0.3


def test_sector_rotation_reason_bearish():
    """reason() returns bearish signal when weighted score < -0.3."""
    agent = SectorRotationAgent()
    data = {k: -2.0 for k in SECTORS}  # all sectors strongly down
    signal = agent.reason(data)
    assert signal.signal == -1
    assert signal.confidence > 0.3


def test_sector_rotation_reason_neutral():
    """reason() returns neutral signal when weighted score is near 0."""
    agent = SectorRotationAgent()
    data = {k: 0.0 for k in SECTORS}
    signal = agent.reason(data)
    assert signal.signal == 0
