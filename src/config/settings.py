import os
try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - environment fallback
    def load_dotenv(*_args, **_kwargs):
        return False

load_dotenv()

class Settings:
    KITE_API_KEY: str = os.getenv("KITE_API_KEY", "")
    KITE_API_SECRET: str = os.getenv("KITE_API_SECRET", "")
    KITE_ACCESS_TOKEN: str = os.getenv("KITE_ACCESS_TOKEN", "")
    NEWS_API_KEY: str = os.getenv("NEWS_API_KEY", "")

    GEMINI_API_KEY_1: str = os.getenv("GEMINI_API_KEY_1", "")
    GEMINI_API_KEY_2: str = os.getenv("GEMINI_API_KEY_2", "")
    GEMINI_FLASH_LITE_MODEL: str = "gemini-2.5-flash-lite"
    GEMINI_FLASH_MODEL: str = "gemini-2.5-flash"
    GEMINI_PRO_MODEL: str = "gemini-2.5-pro"
    GEMINI_USE_PRO: bool = os.getenv("GEMINI_USE_PRO", "false").lower() == "true"

    DB_PATH: str = os.getenv("DB_PATH", "data/market.db")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    ENV: str = os.getenv("ENV", "development")
    NIFTY_SYMBOL: str = "NSE:NIFTY 50"
    MARKET_OPEN: str = "09:15"
    MARKET_CLOSE: str = "15:30"
    TIMEZONE: str = "Asia/Kolkata"

settings = Settings()
