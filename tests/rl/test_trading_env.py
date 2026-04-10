"""Unit tests for src.rl.trading_env and trainer."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from src.rl.trading_env import NiftyTradingEnv
from src.rl.trainer import _load_candles_dataframe


def _synthetic_candles_frame(rows: int = 30) -> pd.DataFrame:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    records: list[dict] = []
    for idx in range(rows):
        close = 100 + idx
        records.append(
            {
                "timestamp_ist": (start + timedelta(days=idx)).isoformat(),
                "open": close - 0.5,
                "high": close + 1.0,
                "low": close - 1.0,
                "close": close,
                "volume": 1000 + idx,
            }
        )
    return pd.DataFrame(records)


def test_reset_returns_correct_observation_shape():
    env = NiftyTradingEnv(candles=_synthetic_candles_frame())

    observation, info = env.reset()

    assert observation.shape == (20, 5)
    assert observation.dtype == np.float32
    assert isinstance(info, dict)


def test_step_returns_gymnasium_five_tuple():
    env = NiftyTradingEnv(candles=_synthetic_candles_frame())
    env.reset()

    output = env.step(1)

    assert len(output) == 5
    observation, reward, done, truncated, info = output
    assert observation.shape == (20, 5)
    assert isinstance(reward, float)
    assert isinstance(done, bool)
    assert isinstance(truncated, bool)
    assert isinstance(info, dict)


def test_invalid_action_raises_no_error_and_behaves_like_hold():
    env = NiftyTradingEnv(candles=_synthetic_candles_frame())
    env.reset()

    observation, reward, done, truncated, info = env.step(99)

    assert observation.shape == (20, 5)
    assert reward == 0.0
    assert done is False
    assert truncated is False
    assert info["position"] == 0


def test_env_raises_when_rows_are_not_greater_than_window_size():
    frame = _synthetic_candles_frame(rows=20)

    with pytest.raises(ValueError, match="greater than window_size"):
        NiftyTradingEnv(candles=frame)


def test_load_candles_dataframe_normalizes_date_bounds(monkeypatch):
    captured: dict[str, str] = {}

    def _fake_read_candles(**kwargs):
        captured.update(kwargs)
        return _synthetic_candles_frame().to_dict("records")

    monkeypatch.setattr("src.rl.trainer.read_candles", _fake_read_candles)

    frame = _load_candles_dataframe(start_date="2026-01-01", end_date="2026-01-31")

    assert captured["from_date"] == "2026-01-01T00:00:00"
    assert captured["to_date"] == "2026-01-31T23:59:59"
    assert frame.shape[1] == 5
