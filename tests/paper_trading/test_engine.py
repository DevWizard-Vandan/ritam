
import pytest

@pytest.fixture(autouse=True)
def reset_engine():
    from src.paper_trading.engine import PaperTradingEngine
    PaperTradingEngine._instance = None
    if hasattr(PaperTradingEngine, "_initialized"):
        delattr(PaperTradingEngine, "_initialized")

from src.paper_trading.engine import PaperTradingEngine

# Mock the DB calls to test engine logic purely in memory
@pytest.fixture(autouse=True)
def mock_db_functions(monkeypatch):
    monkeypatch.setattr("src.paper_trading.engine.get_paper_trade_stats", lambda: {"trade_count": 0, "total_pnl": 0.0, "win_rate": 0.0})
    monkeypatch.setattr("src.paper_trading.engine.insert_paper_trade", lambda **kwargs: None)

@pytest.fixture
def engine():
    from src.config.settings import settings
    settings.PAPER_CAPITAL = 100000.0
    settings.PAPER_LOT_SIZE = 50
    return PaperTradingEngine()

def test_open_position_buy(engine):
    engine.open_position("BUY", 22000.0, "2024-01-01T10:00:00Z")

    assert engine.open_pos is not None
    assert engine.open_pos["signal"] == "BUY"
    assert engine.open_pos["entry_price"] == 22000.0
    assert engine.open_pos["entry_time"] == "2024-01-01T10:00:00Z"

def test_pnl_calculation_buy_win(engine):
    engine.open_position("BUY", 22000.0, "2024-01-01T10:00:00Z")
    engine.close_position(22100.0, "2024-01-01T11:00:00Z")

    assert engine.open_pos is None
    assert engine.total_trades == 1
    assert engine.wins == 1
    # PNL = (22100 - 22000) * 50 = 5000
    assert engine.total_pnl == 5000.0

def test_pnl_calculation_sell_win(engine):
    engine.open_position("SELL", 22000.0, "2024-01-01T10:00:00Z")
    engine.close_position(21900.0, "2024-01-01T11:00:00Z")

    assert engine.open_pos is None
    assert engine.total_trades == 1
    assert engine.wins == 1
    # PNL = (22000 - 21900) * 50 = 5000
    assert engine.total_pnl == 5000.0

def test_hold_behavior(engine):
    engine.open_position("HOLD", 22000.0, "2024-01-01T10:00:00Z")

    # Hold shouldn't open position
    assert engine.open_pos is None
    assert engine.total_trades == 0

def test_signal_flip(engine):
    engine.open_position("BUY", 22000.0, "2024-01-01T10:00:00Z")
    # Simulate a signal flip detected in the orchestrator
    # First, it closes the existing
    engine.close_position(22100.0, "2024-01-01T11:00:00Z")
    # Then opens new
    engine.open_position("SELL", 22100.0, "2024-01-01T11:00:00Z")

    assert engine.total_trades == 1
    assert engine.wins == 1
    assert engine.total_pnl == 5000.0

    assert engine.open_pos is not None
    assert engine.open_pos["signal"] == "SELL"

def test_stats_shape(engine):
    stats = engine.get_stats()
    assert "total_trades" in stats
    assert "win_rate" in stats
    assert "total_pnl" in stats
    assert "sharpe_ratio" in stats
    assert "open_position" in stats
