"""Shared date helper utilities."""
from __future__ import annotations


def normalize_date_bounds(start_date: str, end_date: str) -> tuple[str, str]:
    """Normalize date inputs to full-day ISO bounds when no time is provided."""
    normalized_start = f"{start_date}T00:00:00" if "T" not in start_date else start_date
    normalized_end = f"{end_date}T23:59:59" if "T" not in end_date else end_date
    return normalized_start, normalized_end
