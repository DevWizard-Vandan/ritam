"""Backtesting engine utilities built on Backtrader."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
import warnings

import backtrader as bt
warnings.filterwarnings("ignore", message="\nPyarrow will become a required dependency of pandas", category=DeprecationWarning)

import pandas as pd

from src.data.db import read_candles
from src.utils.date_utils import normalize_date_bounds


@dataclass
class BacktestResult:
    """Structured backtest result."""

    trade_log: list[dict[str, Any]]
    metrics: dict[str, float]


class SimpleMovingAverageCrossover(bt.Strategy):
    """Simple MA crossover strategy used as default smoke-test strategy."""

    params = (
        ("fast_period", 5),
        ("slow_period", 10),
    )

    def __init__(self) -> None:
        self.fast_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.fast_period
        )
        self.slow_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.slow_period
        )
        self.crossover = bt.indicators.CrossOver(self.fast_ma, self.slow_ma)
        self._trade_log: list[dict[str, Any]] = []

    @property
    def trade_log(self) -> list[dict[str, Any]]:
        return self._trade_log

    def next(self) -> None:
        if not self.position and self.crossover > 0:
            self.buy()
        elif self.position and self.crossover < 0:
            self.sell()

    def notify_trade(self, trade: bt.Trade) -> None:
        if not trade.isclosed:
            return

        self._trade_log.append(
            {
                "open_datetime": bt.num2date(trade.dtopen).isoformat(),
                "close_datetime": bt.num2date(trade.dtclose).isoformat(),
                "size": float(trade.size),
                "pnl": float(trade.pnl),
                "pnl_comm": float(trade.pnlcomm),
            }
        )


def _candles_to_dataframe(candles: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(candles)
    if frame.empty:
        return frame

    frame["datetime"] = pd.to_datetime(frame["timestamp_ist"], utc=True)
    frame = frame.set_index("datetime")[["open", "high", "low", "close", "volume"]]
    frame = frame.sort_index()
    return frame


def load_nifty_data(
    start_date: str,
    end_date: str,
    symbol: str = "NSE:NIFTY 50",
) -> bt.feeds.PandasData:
    """Load Nifty candles from SQLite and return a Backtrader feed."""
    normalized_start, normalized_end = normalize_date_bounds(start_date, end_date)
    candles = read_candles(
        symbol=symbol,
        from_date=normalized_start,
        to_date=normalized_end,
    )
    dataframe = _candles_to_dataframe(candles)

    if dataframe.empty:
        raise ValueError("No candle data found for the provided range")

    return bt.feeds.PandasData(dataname=dataframe)


def _calculate_cagr(initial_value: float, final_value: float, start: str, end: str) -> float:
    start_dt = datetime.fromisoformat(start)
    end_dt = datetime.fromisoformat(end)
    years = (end_dt - start_dt).total_seconds() / (365.25 * 24 * 3600)
    if years <= 0 or initial_value <= 0:
        return 0.0
    return ((final_value / initial_value) ** (1 / years) - 1) * 100


def run_backtest(
    strategy_class: type[bt.Strategy] = SimpleMovingAverageCrossover,
    start_date: str = "2008-01-01",
    end_date: str = "2009-12-31",
) -> BacktestResult:
    """Run a Backtrader cerebro instance and return trade log + key metrics."""
    cerebro = bt.Cerebro()
    data_feed = load_nifty_data(start_date=start_date, end_date=end_date)
    cerebro.adddata(data_feed)
    cerebro.addstrategy(strategy_class)

    initial_cash = 100_000.0
    cerebro.broker.setcash(initial_cash)
    cerebro.broker.setcommission(commission=0.001)

    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe", timeframe=bt.TimeFrame.Days)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")

    strategies = cerebro.run()
    strategy = strategies[0]

    sharpe_analysis = strategy.analyzers.sharpe.get_analysis()
    drawdown_analysis = strategy.analyzers.drawdown.get_analysis()

    final_value = float(cerebro.broker.getvalue())
    metrics = {
        "initial_cash": initial_cash,
        "final_portfolio_value": final_value,
        "total_return_pct": ((final_value - initial_cash) / initial_cash) * 100,
        "sharpe": float(sharpe_analysis.get("sharperatio", 0.0) or 0.0),
        "max_drawdown": float(drawdown_analysis.get("max", {}).get("drawdown", 0.0)),
        "cagr": _calculate_cagr(initial_cash, final_value, start_date, end_date),
    }

    return BacktestResult(
        trade_log=getattr(strategy, "trade_log", []),
        metrics=metrics,
    )
