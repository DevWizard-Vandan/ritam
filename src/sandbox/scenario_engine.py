from dataclasses import dataclass
from typing import Any
import json
from loguru import logger
import yfinance as yf
from datetime import datetime

from src.data.db import read_intraday_candles
from src.reasoning.gemma_client import quick_reason, deep_reason
from src.reasoning.analog_finder import find_intraday_analogs, find_analogs
from src.config import settings

@dataclass
class ScenarioResult:
    date: str | None
    condition: str | None
    data_source: str
    historical_candles: list[dict]
    projected_candles: list[dict]
    condition_parsed: dict | None
    regime: str
    narrative: str
    confidence: float

class ScenarioEngine:
    def _parse_condition(self, condition: str) -> dict:
        prompt = f"""Parse this market condition into a structured event:
'{condition}'
Return JSON only:
{{
  "type": string,
  "magnitude": float or null,
  "direction": "bullish" | "bearish" | "neutral",
  "affected_sector": string or null,
  "confidence": float (0-1),
  "reasoning": string
}}"""
        response_text = quick_reason(prompt)
        try:
            clean_json = response_text.replace('```json', '').replace('```', '').strip()
            return json.loads(clean_json)
        except Exception as e:
            logger.warning(f"Failed to parse condition JSON: {e} - Raw: {response_text}")
            return {}

    def _determine_data_source_and_fetch(self, date_str: str | None) -> tuple[str, list[dict]]:
        if not date_str:
            return "gemini_pure", []

        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            dt = datetime.strptime(date_str[:10], "%Y-%m-%d")

        try:
            intraday_data = read_intraday_candles(symbol=settings.INTRADAY_SYMBOL)
            if intraday_data:
                first_date = datetime.strptime(intraday_data[0]["timestamp_ist"][:10], "%Y-%m-%d")
                last_date = datetime.strptime(intraday_data[-1]["timestamp_ist"][:10], "%Y-%m-%d")

                if first_date <= dt <= last_date:
                    history = [c for c in intraday_data if c["timestamp_ist"][:10] <= date_str[:10]]
                    if history:
                        return "db", history[-50:]
        except Exception as e:
            logger.warning(f"Failed checking DB: {e}")

        if dt >= datetime(1990, 1, 1):
            try:
                df = yf.download("^NSEI", start=dt.strftime("%Y-%m-%d"), period="3mo")
                if not df.empty:
                    hist = []
                    for i, row in df.iterrows():
                        hist.append({
                            "timestamp_ist": i.strftime("%Y-%m-%d"),
                            "open": float(row['Open'].iloc[0]) if isinstance(row['Open'], type(df)) else float(row['Open']),
                            "high": float(row['High'].iloc[0]) if isinstance(row['High'], type(df)) else float(row['High']),
                            "low": float(row['Low'].iloc[0]) if isinstance(row['Low'], type(df)) else float(row['Low']),
                            "close": float(row['Close'].iloc[0]) if isinstance(row['Close'], type(df)) else float(row['Close']),
                            "volume": float(row['Volume'].iloc[0]) if isinstance(row['Volume'], type(df)) else float(row['Volume']),
                        })
                    return "yfinance", hist
            except Exception as e:
                logger.warning(f"Failed fetching from yfinance: {e}")

        return "gemini_pure", []

    def run(
        self,
        condition: str | None,
        date: str | None,
        candles_ahead: int = 20
    ) -> ScenarioResult:
        if condition is None and date is None:
            raise ValueError("At least one of condition or date must be provided")

        condition_parsed = None
        if condition is not None:
            condition_parsed = self._parse_condition(condition)

        data_source, historical_candles = self._determine_data_source_and_fetch(date)

        projected_candles = []
        regime = "baseline"
        narrative = ""
        confidence = 0.0

        if data_source in ("db", "yfinance") and historical_candles:
            if data_source == "db":
                analogs = find_intraday_analogs(historical_candles[-20:])
            else:
                analogs = find_analogs(historical_candles[-20:])

            prompt = f"""Given this market context: {regime}, these historical analogs:
{analogs}, and this condition: {condition_parsed},
predict the next {candles_ahead} candles as a JSON array.
Each candle: {{"time", "open", "high", "low", "close", "volume"}}.
Also provide: regime (Crisis/Ranging/Trending Up),
narrative (2-3 sentences), confidence (0-1).
Return JSON only in the following format:
{{
  "projected_candles": [...],
  "regime": "...",
  "narrative": "...",
  "confidence": 0.0
}}"""
            response_text = quick_reason(prompt)
            try:
                clean_json = response_text.replace('```json', '').replace('```', '').strip()
                parsed = json.loads(clean_json)
                projected_candles = parsed.get("projected_candles", [])
                regime = parsed.get("regime", regime)
                narrative = parsed.get("narrative", narrative)
                confidence = float(parsed.get("confidence", confidence))
            except Exception as e:
                logger.warning(f"Failed to parse A case scenario: {e}")
        else:
            prompt = f"""Context: {condition}
Imagine Indian equity markets in this scenario.
Generate {candles_ahead} plausible OHLCV candles as JSON array.
Each candle: {{"time": unix, "open": float, "high": float, "low": float, "close": float, "volume": float}}.
Start from a base Nifty value of 22000.
Also return: regime, narrative (3-4 sentences), confidence (0-1).
Return JSON only in the following format:
{{
  "projected_candles": [...],
  "regime": "...",
  "narrative": "...",
  "confidence": 0.0
}}"""
            response_text = deep_reason(prompt)
            try:
                clean_json = response_text.replace('```json', '').replace('```', '').strip()
                parsed = json.loads(clean_json)
                projected_candles = parsed.get("projected_candles", [])
                regime = parsed.get("regime", regime)
                narrative = parsed.get("narrative", narrative)
                confidence = float(parsed.get("confidence", confidence))
            except Exception as e:
                logger.warning(f"Failed to parse B case scenario: {e}")

        return ScenarioResult(
            date=date,
            condition=condition,
            data_source=data_source,
            historical_candles=historical_candles,
            projected_candles=projected_candles,
            condition_parsed=condition_parsed,
            regime=regime,
            narrative=narrative,
            confidence=confidence
        )
