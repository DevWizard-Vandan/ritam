"""Clean and normalize headlines before FinBERT scoring."""
import re


def clean_headline(text: str) -> str:
    text = text.strip()
    text = re.sub(r"https?://\S+", "", text)  # remove URLs
    text = re.sub(r"\s+", " ", text)           # normalize whitespace
    text = text[:512]                          # FinBERT max input length
    return text


def clean_headlines(headlines: list[str]) -> list[str]:
    return [clean_headline(h) for h in headlines if h and h.strip()]
