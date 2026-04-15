"""Historical analog finder based on candle-pattern similarity from SQLite data."""

from __future__ import annotations

import math
from typing import Iterable

from src.config import settings
from src.data.db import read_candles, read_intraday_candles


def _extract_close_series(candles: Iterable[dict]) -> list[float]:
    closes: list[float] = []
    for candle in candles:
        close = candle.get("close")
        if close is None:
            return []
        try:
            closes.append(float(close))
        except (TypeError, ValueError):
            return []
    return closes


def _pct_returns(closes: list[float]) -> list[float]:
    if len(closes) < 2:
        return []

    returns: list[float] = []
    for prev_close, close in zip(closes, closes[1:]):
        if prev_close == 0:
            return []
        returns.append(((close - prev_close) / prev_close) * 100.0)
    return returns


def _cosine_similarity(a: list[float], b: list[float]) -> float | None:
    if len(a) != len(b) or not a:
        return None

    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return None

    score = dot / (norm_a * norm_b)
    return max(-1.0, min(1.0, score))


def _dtw_distance(a: list[float], b: list[float]) -> float:
    n = len(a)
    m = len(b)
    dtw = [[math.inf] * (m + 1) for _ in range(n + 1)]
    dtw[0][0] = 0.0

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = abs(a[i - 1] - b[j - 1])
            dtw[i][j] = cost + min(dtw[i - 1][j], dtw[i][j - 1], dtw[i - 1][j - 1])

    return dtw[n][m]


def _dtw_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    return 1.0 / (1.0 + _dtw_distance(a, b))


def _to_date(timestamp_value: str) -> str:
    if "T" in timestamp_value:
        return timestamp_value.split("T", 1)[0]
    if " " in timestamp_value:
        return timestamp_value.split(" ", 1)[0]
    return timestamp_value


def _to_daily_closes(candles: list[dict]) -> list[dict]:
    """Return one entry per date, keeping the last close of each day."""
    seen = {}
    for candle in candles:
        timestamp_value = str(candle.get("timestamp_ist", ""))
        if len(timestamp_value) < 10:
            continue
        date_value = timestamp_value[:10]
        seen[date_value] = candle
    return [seen[day] for day in sorted(seen)]


def find_analogs(
    current_window: list[dict],
    top_n: int = 5,
    symbol: str = settings.NIFTY_SYMBOL,
) -> list[dict]:
    """
    Find the most similar historical windows versus the current daily candle window.

    Args:
        current_window: Last N daily candles, each containing at least {timestamp_ist, close}.
        top_n: Number of best matches to return.
        symbol: Instrument symbol used to query historical candles.

    Returns:
        List of dicts with start_date, end_date, similarity_score, and next_5day_return.
    """
    if top_n <= 0 or len(current_window) < 2:
        return []

    current_closes = _extract_close_series(current_window)
    current_returns = _pct_returns(current_closes)
    if not current_returns:
        return []

    window_len = len(current_window)

    historical_candles = read_candles(
        symbol=symbol,
        from_date="2000-01-01",
        to_date="2100-01-01",
    )
    historical_daily = _to_daily_closes(historical_candles)

    if len(historical_daily) < window_len + 5:
        return []

    matches: list[dict] = []
    last_start_index = len(historical_daily) - window_len - 5

    for start_idx in range(last_start_index + 1):
        window = historical_daily[start_idx : start_idx + window_len]
        window_closes = _extract_close_series(window)
        window_returns = _pct_returns(window_closes)
        if not window_returns:
            continue

        similarity = _cosine_similarity(current_returns, window_returns)
        if similarity is None:
            similarity = _dtw_similarity(current_returns, window_returns)

        end_idx = start_idx + window_len - 1
        next_5_idx = end_idx + 5
        end_close = historical_daily[end_idx].get("close")
        next_5_close = historical_daily[next_5_idx].get("close")

        try:
            end_close = float(end_close)
            next_5_close = float(next_5_close)
        except (TypeError, ValueError):
            continue

        if end_close == 0:
            continue

        next_5day_return = ((next_5_close - end_close) / end_close) * 100.0

        matches.append(
            {
                "start_date": _to_date(str(window[0].get("timestamp_ist", ""))),
                "end_date": _to_date(str(window[-1].get("timestamp_ist", ""))),
                "similarity_score": round(float(similarity), 6),
                "next_5day_return": round(next_5day_return, 4),
            }
        )

    matches.sort(key=lambda item: item["similarity_score"], reverse=True)
    return matches[:top_n]


def find_intraday_analogs(
    current_window: list[dict],
    top_n: int = 5,
    symbol: str | None = None,
    window_size: int = 20,
) -> list[dict]:
    """
    Find the most similar historical 15-min intraday windows vs the current window.

    Args:
        current_window: Last N 15-min candles from intraday_candles, each containing
            at least {timestamp_ist, close}.
        top_n: Number of best matches to return.
        symbol: Instrument symbol used to query historical intraday candles.
            Defaults to settings.INTRADAY_SYMBOL if not provided.
        window_size: Number of 15-min candles per comparison window (default 20 = 5 hours).

    Returns:
        List of dicts with start_date, end_date, similarity_score, and next_5candle_return.
        Returns [] if current_window has fewer than 2 candles or insufficient history.
    """
    if symbol is None:
        symbol = settings.INTRADAY_SYMBOL
    if top_n <= 0 or len(current_window) < max(2, window_size):
        return []

    current_closes = _extract_close_series(current_window)
    current_returns = _pct_returns(current_closes)
    if not current_returns:
        return []

    window_len = len(current_window)
    outcome_candles = 5  # resolve outcome after 5 candles (75 minutes)

    historical = read_intraday_candles(symbol=symbol)

    if len(historical) < window_len + outcome_candles:
        return []

    matches: list[dict] = []
    last_start_index = len(historical) - window_len - outcome_candles

    for start_idx in range(last_start_index + 1):
        window = historical[start_idx : start_idx + window_len]
        window_closes = _extract_close_series(window)
        window_returns = _pct_returns(window_closes)
        if not window_returns:
            continue

        similarity = _cosine_similarity(current_returns, window_returns)
        if similarity is None:
            similarity = _dtw_similarity(current_returns, window_returns)

        end_idx = start_idx + window_len - 1
        next_idx = end_idx + outcome_candles
        end_close = historical[end_idx].get("close")
        next_close = historical[next_idx].get("close")

        try:
            end_close = float(end_close)
            next_close = float(next_close)
        except (TypeError, ValueError):
            continue

        if end_close == 0:
            continue

        next_5candle_return = ((next_close - end_close) / end_close) * 100.0

        matches.append(
            {
                "start_date": _to_date(str(window[0].get("timestamp_ist", ""))),
                "end_date": _to_date(str(window[-1].get("timestamp_ist", ""))),
                "similarity_score": round(float(similarity), 6),
                "next_5candle_return": round(next_5candle_return, 4),
            }
        )

    matches.sort(key=lambda item: item["similarity_score"], reverse=True)
    return matches[:top_n]


class AnalogFinder:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def find_analogs(
        self,
        current_window: list[dict],
        top_n: int = 5,
        symbol: str = settings.NIFTY_SYMBOL,
    ) -> list[dict]:
        return find_analogs(
            current_window=current_window,
            top_n=top_n,
            symbol=symbol,
        )
