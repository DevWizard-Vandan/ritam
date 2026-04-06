import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    KITE_API_KEY: str = os.getenv("KITE_API_KEY", "")
    KITE_API_SECRET: str = os.getenv("KITE_API_SECRET", "")
    KITE_ACCESS_TOKEN: str = os.getenv("KITE_ACCESS_TOKEN", "")
    NEWS_API_KEY: str = os.getenv("NEWS_API_KEY", "")
    DB_PATH: str = os.getenv("DB_PATH", "data/market.db")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    ENV: str = os.getenv("ENV", "development")
    NIFTY_SYMBOL: str = "NSE:NIFTY 50"
    MARKET_OPEN: str = "09:15"
    MARKET_CLOSE: str = "15:30"
    TIMEZONE: str = "Asia/Kolkata"

settings = Settings()
