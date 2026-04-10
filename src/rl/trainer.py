"""PPO trainer for Nifty trading environment."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from stable_baselines3 import PPO

from src.data.db import read_candles
from src.rl.trading_env import NiftyTradingEnv
from src.utils.date_utils import normalize_date_bounds


def _load_candles_dataframe(
    start_date: str,
    end_date: str,
    symbol: str = "NSE:NIFTY 50",
) -> pd.DataFrame:
    normalized_start, normalized_end = normalize_date_bounds(start_date, end_date)
    candles = read_candles(
        symbol=symbol,
        from_date=normalized_start,
        to_date=normalized_end,
    )
    frame = pd.DataFrame(candles)
    if frame.empty:
        raise ValueError("No candles found for the training period")

    frame = frame.sort_values("timestamp_ist").reset_index(drop=True)
    return frame[["open", "high", "low", "close", "volume"]]


def train_agent(start_date: str, end_date: str) -> Path:
    """Train PPO on Nifty candles and save the model artifact."""
    candles = _load_candles_dataframe(start_date=start_date, end_date=end_date)
    env = NiftyTradingEnv(candles=candles)

    model = PPO("MlpPolicy", env, verbose=0)
    model.learn(total_timesteps=2_000)

    model_path = Path("models") / "ppo_nifty.zip"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model.save(str(model_path.with_suffix("")))
    return model_path
