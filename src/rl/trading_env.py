"""Gymnasium trading environment for Nifty OHLCV candles."""
from __future__ import annotations

from typing import Any

import gymnasium as gym
import numpy as np
import pandas as pd
from gymnasium import spaces


class NiftyTradingEnv(gym.Env):
    """Simple single-position trading environment over OHLCV candles.

    Observations are the last ``window_size`` candles normalized feature-wise.
    Actions map to: 0=hold, 1=buy/long, 2=sell/short.
    """

    metadata = {"render_modes": []}

    def __init__(self, candles: pd.DataFrame, window_size: int = 20) -> None:
        super().__init__()

        if candles.empty:
            raise ValueError("Candles dataframe cannot be empty")

        required_columns = ["open", "high", "low", "close", "volume"]
        missing_columns = [col for col in required_columns if col not in candles.columns]
        if missing_columns:
            raise ValueError(f"Missing required candle columns: {missing_columns}")

        self.candles = candles[required_columns].reset_index(drop=True).astype(float)
        self.window_size = window_size

        if len(self.candles) <= self.window_size:
            raise ValueError("Candles length must be greater than window_size")

        self.action_space = spaces.Discrete(3)
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(self.window_size, len(required_columns)),
            dtype=np.float32,
        )

        self._current_step = self.window_size
        self._position = 0  # -1 short, 0 flat, 1 long

    def _get_observation(self) -> np.ndarray:
        window = self.candles.iloc[self._current_step - self.window_size : self._current_step].copy()
        means = window.mean(axis=0)
        stds = window.std(axis=0, ddof=0).replace(0.0, 1.0)
        stds = stds.fillna(1.0)
        normalized = (window - means) / stds
        return normalized.to_numpy(dtype=np.float32)

    def reset(
        self, *, seed: int | None = None, options: dict[str, Any] | None = None
    ) -> tuple[np.ndarray, dict[str, Any]]:
        super().reset(seed=seed)
        self._current_step = self.window_size
        self._position = 0
        observation = self._get_observation()
        return observation, {}

    def step(self, action: int) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        if action not in {0, 1, 2}:
            action = 0  # treat unknown actions as hold

        if action == 1:
            self._position = 1
        elif action == 2:
            self._position = -1

        prev_close = float(self.candles.iloc[self._current_step - 1]["close"])
        next_close = float(self.candles.iloc[self._current_step]["close"])
        price_change_pct = ((next_close - prev_close) / prev_close) * 100
        reward = float(self._position * price_change_pct)

        self._current_step += 1
        terminated = self._current_step >= len(self.candles)
        truncated = False

        if terminated:
            observation = np.zeros(self.observation_space.shape, dtype=np.float32)
        else:
            observation = self._get_observation()

        info: dict[str, Any] = {
            "position": self._position,
            "price_change_pct": price_change_pct,
        }

        return observation, reward, terminated, truncated, info
