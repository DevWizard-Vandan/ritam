"""
Gemma 4 reasoning client via Ollama (OpenAI-compatible API).
Falls back to Gemini 2.5 Flash API if Ollama is offline.

Ollama setup (one-time manual step):
  ollama pull gemma4:e4b    # quick reasoning, always on
  ollama pull gemma4:26b   # deep reasoning, on demand
  ollama serve             # start server at localhost:11434
"""
import os
import requests
from openai import OpenAI
from loguru import logger
from src.config import settings

OLLAMA_BASE = "http://localhost:11434/v1"
GEMMA_SMALL = "gemma4:e4b"
GEMMA_LARGE = "gemma4:26b"

_ollama_client = None
_gemini_client = None


def _is_ollama_running() -> bool:
    """Check if Ollama server is reachable."""
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def _get_ollama_client() -> OpenAI:
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OpenAI(base_url=OLLAMA_BASE, api_key="ollama")
    return _ollama_client


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
        client = _get_ollama_client()
        resp = client.chat.completions.create(
            model=GEMMA_SMALL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
            temperature=0.3
        )
        logger.debug(f"quick_reason via {GEMMA_SMALL}")
        return resp.choices[0].message.content
    logger.warning("Ollama offline — falling back to Gemini for quick_reason")
    return _gemini_fallback(prompt)


def deep_reason(prompt: str) -> str:
    """Deep reasoning using Gemma 4 26B. Falls back to Gemini if offline."""
    if _is_ollama_running():
        client = _get_ollama_client()
        resp = client.chat.completions.create(
            model=GEMMA_LARGE,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
            temperature=0.4
        )
        logger.debug(f"deep_reason via {GEMMA_LARGE}")
        return resp.choices[0].message.content
    logger.warning("Ollama offline — falling back to Gemini for deep_reason")
    return _gemini_fallback(prompt)
