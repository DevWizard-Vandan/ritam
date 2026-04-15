import logging
import math
from typing import Optional, Dict, Any
from src.config.settings import settings
from src.data.db import insert_paper_trade, get_paper_trade_stats

logger = logging.getLogger(__name__)

class PaperTradingEngine:
    """
    Engine to convert BUY/SELL signals into virtual trades.
    Maintains a single active position at a time and tracks P&L.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PaperTradingEngine, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self.capital = settings.PAPER_CAPITAL
        self.lot_size = settings.PAPER_LOT_SIZE
        self.open_pos: Optional[Dict[str, Any]] = None
        self.total_trades = 0
        self.total_pnl = 0.0
        self.wins = 0

        # Initialize stats from DB if exist
        try:
            stats = get_paper_trade_stats()
            self.total_trades = stats.get("trade_count", 0)
            self.total_pnl = stats.get("total_pnl", 0.0)
            self.wins = int(self.total_trades * stats.get("win_rate", 0.0))
        except Exception as e:
            logger.warning(f"Could not load paper trading stats from DB: {e}")

    def open_position(self, signal: str, price: float, timestamp: str) -> None:
        """
        Opens a virtual position if signal is BUY or SELL and no existing position.
        Ignores HOLD signals.
        """
        signal_upper = signal.upper()
        if signal_upper not in ["BUY", "SELL"]:
            return

        if self.open_pos is not None:
            logger.info(f"Cannot open {signal_upper} position: A position is already open.")
            return

        self.open_pos = {
            "signal": signal_upper,
            "entry_price": price,
            "entry_time": timestamp
        }
        logger.info(f"Opened paper {signal_upper} position at {price} on {timestamp}")

    def close_position(self, price: float, timestamp: str) -> None:
        """
        Closes active position, computes and records P&L, determines outcome.
        """
        if self.open_pos is None:
            logger.info("Cannot close position: No position is currently open.")
            return

        signal = self.open_pos["signal"]
        entry_price = self.open_pos["entry_price"]
        entry_time = self.open_pos["entry_time"]

        # Calculate P&L
        if signal == "BUY":
            pnl = (price - entry_price) * self.lot_size
        else: # SELL
            pnl = (entry_price - price) * self.lot_size

        outcome = "WIN" if pnl > 0 else "LOSS"
        if pnl == 0:
            outcome = "TIE"

        # Update in-memory stats
        self.total_trades += 1
        self.total_pnl += pnl
        if outcome == "WIN":
            self.wins += 1

        # Record to DB
        try:
            insert_paper_trade(
                signal=signal,
                entry_price=entry_price,
                entry_time=entry_time,
                exit_price=price,
                exit_time=timestamp,
                pnl=pnl,
                outcome=outcome
            )
            logger.info(f"Closed paper {signal} position at {price} on {timestamp}. PnL: {pnl}. Outcome: {outcome}")
        except Exception as e:
            logger.error(f"Failed to record paper trade to DB: {e}")

        # Clear open position
        self.open_pos = None

    def get_stats(self) -> dict:
        """
        Returns stats: total_trades, win_rate, total_pnl, sharpe_ratio, open_position
        """
        win_rate = float(self.wins) / self.total_trades if self.total_trades > 0 else 0.0

        # Calculate a simplified Sharpe Ratio
        # Assuming risk-free rate is 0.
        # In a real system, we'd calculate standard deviation of daily returns.
        # Since we just have PnL and trade count, we can do a proxy or 0.0.
        # To avoid over-complexity given the constraints, we will return 0.0 if not calculable.
        # A simple proxy: total_pnl / (sqrt(trade_count) * some_factor) - let's keep it simple
        sharpe_ratio = 0.0 # Placeholder for now

        return {
            "total_trades": self.total_trades,
            "win_rate": round(win_rate, 4),
            "total_pnl": round(self.total_pnl, 2),
            "sharpe_ratio": sharpe_ratio,
            "open_position": self.open_pos
        }