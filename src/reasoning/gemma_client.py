"""
Gemma 4 reasoning client via Ollama (OpenAI-compatible API).
Falls back to Gemini 2.5 Flash API if Ollama is offline.
"""
from loguru import logger
from src.config import settings

def _call_flash_lite(prompt: str) -> str:
    """Uses GEMINI_API_KEY_1 — Account A"""
    import google.generativeai as genai
    genai.configure(api_key=settings.GEMINI_API_KEY_1)
    model_name = settings.GEMINI_PRO_MODEL if settings.GEMINI_USE_PRO else settings.GEMINI_FLASH_LITE_MODEL
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(prompt)
    return response.text.strip()

def _call_flash(prompt: str) -> str:
    """Uses GEMINI_API_KEY_2 — Account B"""
    import google.generativeai as genai
    genai.configure(api_key=settings.GEMINI_API_KEY_2)
    model_name = settings.GEMINI_PRO_MODEL if settings.GEMINI_USE_PRO else settings.GEMINI_FLASH_MODEL
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(prompt)
    return response.text.strip()

def quick_reason(prompt: str) -> str:
    try:
        result = _call_flash_lite(prompt)
        logger.debug(f"quick_reason via {'Gemini Pro' if settings.GEMINI_USE_PRO else 'Gemini Flash-Lite'} [key_1]")
        return result
    except Exception as e:
        logger.warning(f"Key 1 failed: {e} — falling back to Key 2")
        try:
            return _call_flash(prompt)
        except Exception as e2:
            logger.error(f"Both keys failed for quick_reason: {e2}")
            return "baseline"

def deep_reason(prompt: str) -> str:
    try:
        result = _call_flash(prompt)
        logger.debug(f"deep_reason via {'Gemini Pro' if settings.GEMINI_USE_PRO else 'Gemini Flash'} [key_2]")
        return result
    except Exception as e:
        logger.warning(f"Key 2 failed: {e} — falling back to Key 1")
        try:
            return _call_flash_lite(prompt)
        except Exception as e2:
            logger.error(f"Both keys failed for deep_reason: {e2}")
            return ""
