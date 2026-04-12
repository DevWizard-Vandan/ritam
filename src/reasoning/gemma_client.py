"""
Gemma 4 reasoning client via Ollama (OpenAI-compatible API).
Falls back to Gemini 2.5 Flash API if Ollama is offline.

Ollama setup (one-time manual step):
  ollama pull gemma4:2b    # quick reasoning, always on
  ollama pull gemma4:26b   # deep reasoning, on demand
  ollama serve             # start server at localhost:11434
"""
import os
import requests
from loguru import logger
from src.config import settings

_OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
GEMMA_SMALL = "gemma4:2b"
GEMMA_LARGE = "gemma4:26b"

_gemini_client = None


def _extract_content(response_json: dict) -> str:
    candidates = [
        (response_json.get("response") or "").strip(),
        ((response_json.get("message") or {}).get("content") or "").strip(),
        (response_json.get("thinking") or "").strip(),
    ]
    return next((c for c in candidates if c), "")


def _is_ollama_running() -> bool:
    """Check if Ollama server is reachable."""
    try:
        r = requests.get(f"{_OLLAMA_BASE}/api/tags", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def _gemini_fallback(prompt: str) -> str:
    """Call Gemini 2.5 Flash API as cloud fallback."""
    import google.generativeai as genai
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        logger.error("No GEMINI_API_KEY set — cannot fall back to Gemini")
        return "REASONING_UNAVAILABLE"
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(prompt)
    logger.info("Used Gemini 2.5 Flash (cloud fallback)")
    return response.text


def quick_reason(prompt: str) -> str:
    """Fast reasoning using Gemma 4 E2B. Falls back to Gemini if offline."""
    if _is_ollama_running():
        payload = {
            "model": GEMMA_SMALL,
            "prompt": prompt,
            "stream": False,
            "options": {"think": False}
        }
        try:
            resp = requests.post(f"{_OLLAMA_BASE}/api/generate", json=payload, timeout=30)
            resp.raise_for_status()
            response_json = resp.json()
            content = _extract_content(response_json)
            if not content:
                logger.warning(f"Gemma returned empty content. Raw: {str(response_json)[:500]}")
                logger.warning("Falling back to Gemini due to empty Ollama response")
                return _gemini_fallback(prompt)
            logger.debug(f"quick_reason via {GEMMA_SMALL}")
            return content
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            # Fall through to Gemini
    logger.warning("Ollama offline or failed — falling back to Gemini for quick_reason")
    return _gemini_fallback(prompt)


def deep_reason(prompt: str) -> str:
    """Deep reasoning using Gemma 4 26B. Falls back to Gemini if offline."""
    if _is_ollama_running():
        payload = {
            "model": GEMMA_LARGE,
            "prompt": prompt,
            "stream": False,
            "options": {"think": False}
        }
        try:
            resp = requests.post(f"{_OLLAMA_BASE}/api/generate", json=payload, timeout=120)
            resp.raise_for_status()
            response_json = resp.json()
            content = _extract_content(response_json)
            if not content:
                logger.warning(f"Gemma returned empty content. Raw: {str(response_json)[:500]}")
                logger.warning("Falling back to Gemini due to empty Ollama response")
                return _gemini_fallback(prompt)
            logger.debug(f"deep_reason via {GEMMA_LARGE}")
            return content
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            # Fall through to Gemini
    logger.warning("Ollama offline or failed — falling back to Gemini for deep_reason")
    return _gemini_fallback(prompt)
