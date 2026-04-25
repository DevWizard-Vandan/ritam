import os
try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - environment fallback
    def load_dotenv(*_args, **_kwargs):
        return False

load_dotenv()


def _normalize_db_path(raw_value: str | None) -> str:
    value = (raw_value or "").strip()
    if value.upper().startswith("DB_PATH="):
        value = value.split("=", 1)[1].strip()
    if "#" in value:
        value = value.split("#", 1)[0].strip()
    return value or "data/market.db"

class Settings:
    PAPER_CAPITAL: float = 100000.0
    PAPER_LOT_SIZE: int = 50
    KITE_API_KEY: str = os.getenv("KITE_API_KEY", "")
    KITE_API_SECRET: str = os.getenv("KITE_API_SECRET", "")
    KITE_ACCESS_TOKEN: str = os.getenv("KITE_ACCESS_TOKEN", "")
    NEWS_API_KEY: str = os.getenv("NEWS_API_KEY", "")

    # 7 Gemini API keys — one per Google account
    GEMINI_API_KEY_1: str = os.getenv("GEMINI_API_KEY_1", "")   # Account A — quick_reason (Flash-Lite)
    GEMINI_API_KEY_2: str = os.getenv("GEMINI_API_KEY_2", "")   # Account B — deep_reason (Flash)
    GEMINI_API_KEY_3: str = os.getenv("GEMINI_API_KEY_3", "")   # Account C — TechnicalPatternAgent
    GEMINI_API_KEY_4: str = os.getenv("GEMINI_API_KEY_4", "")   # Account D — MacroSynthesisAgent
    GEMINI_API_KEY_5: str = os.getenv("GEMINI_API_KEY_5", "")   # Account E — NewsImpactAgent
    GEMINI_API_KEY_6: str = os.getenv("GEMINI_API_KEY_6", "")   # Account F — RegimeCrossCheckAgent
    GEMINI_API_KEY_7: str = os.getenv("GEMINI_API_KEY_7", "")   # Account G — overflow / fallback pool

    # Model names
    GEMINI_FLASH_LITE_MODEL: str = "gemini-2.5-flash-lite"
    GEMINI_FLASH_MODEL: str = "gemini-2.5-flash"
    GEMINI_PRO_MODEL: str = "gemini-2.5-pro"
    GEMINI_USE_PRO: bool = os.getenv("GEMINI_USE_PRO", "false").lower() == "true"

    # RPM limits per model (free tier) — used for logging/monitoring
    GEMINI_FLASH_LITE_RPM: int = 15
    GEMINI_FLASH_RPM: int = 5
    # Force Flash-Lite for all cycle agents (override during testing)
    GEMINI_FORCE_FLASH_LITE: bool = os.getenv(
        "GEMINI_FORCE_FLASH_LITE", "true"
    ).lower() == "true"

    # Scheduler config
    CYCLE_INTERVAL_MINUTES: int = 5
    MARKET_OPEN_TIME: str = "09:15"   # IST
    MARKET_CLOSE_TIME: str = "15:30"  # IST
    SCHEDULER_ENABLED: bool = os.getenv("SCHEDULER_ENABLED", "true").lower() == "true"

    DB_PATH: str = _normalize_db_path(os.getenv("DB_PATH", "data/market.db"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    ENV: str = os.getenv("ENV", "development")
    NIFTY_SYMBOL: str = "NSE:NIFTY 50"
    MARKET_OPEN: str = "09:15"
    MARKET_CLOSE: str = "15:30"
    TIMEZONE: str = "Asia/Kolkata"

    GLOBAL_MARKET_CACHE_TTL_MINUTES: int = 30

    # Intraday data config
    INTRADAY_SYMBOL: str = "NSE:NIFTY 50"
    INTRADAY_INTERVAL: str = "15minute"
    INTRADAY_LOOKBACK_DAYS: int = 60      # seed historical window
    INTRADAY_CANDLES_FOR_ANALOG: int = 20 # window size for analog matching
    INTRADAY_OUTCOME_CANDLES: int = 5     # candles forward to resolve outcome

    # Dual resolution mode
    USE_INTRADAY: bool = True
    # True = 15-min candles (L3), False = daily candles (L1 fallback)

settings = Settings()
