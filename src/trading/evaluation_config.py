"""Frozen evaluation-mode constants for the 4-week run."""

from __future__ import annotations

CONFIDENCE_THRESHOLD: float = 0.65
PCR_BANDS: tuple[float, float] = (0.8, 1.3)
NO_TWEAK_MODE: bool = True
MAX_TRADES_PER_DAY: int = 3
PCR_UNAVAILABLE_MAX_MINUTES: int = 30
SUMMARY_EVERY_N_CYCLES: int = 5
