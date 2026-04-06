"""
Zerodha Kite Connect client — authentication only.
Returns an authenticated KiteConnect instance.
DO NOT put trading logic here.
"""
from kiteconnect import KiteConnect
from src.config import settings
from loguru import logger


def get_client() -> KiteConnect:
    """Return an authenticated KiteConnect client."""
    if not settings.KITE_API_KEY:
        raise ValueError("KITE_API_KEY not found in .env")
    kite = KiteConnect(api_key=settings.KITE_API_KEY)
    if settings.KITE_ACCESS_TOKEN:
        kite.set_access_token(settings.KITE_ACCESS_TOKEN)
        logger.info("Kite client authenticated via access token")
    else:
        logger.warning("KITE_ACCESS_TOKEN not set — manual login required")
    return kite
