"""Shared helpers for normalizing and displaying time values."""

from __future__ import annotations

from datetime import datetime, time
import re
from typing import Any

_TIME_TEXT_FORMATS = (
    "%H:%M",
    "%H:%M:%S",
    "%H%M",
    "%I:%M %p",
    "%I:%M:%S %p",
)
_TIME_WITH_SECONDS_RE = re.compile(r"(?<!\d)(\d{2}):(\d{2}):\d{2}(?!\d)")


def normalize_clock_time(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, time):
        return value.strftime("%H:%M")
    if isinstance(value, datetime):
        return value.strftime("%H:%M")
    if isinstance(value, (int, float)):
        frac = float(value) % 1.0
        total_minutes = int(round(frac * 24 * 60)) % (24 * 60)
        hh = total_minutes // 60
        mm = total_minutes % 60
        return f"{hh:02d}:{mm:02d}"
    text = str(value).strip()
    if not text:
        return None
    for fmt in _TIME_TEXT_FORMATS:
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.strftime("%H:%M")
        except ValueError:
            continue
    return None


def normalize_clock_time_or_text(value: Any) -> str | None:
    normalized = normalize_clock_time(value)
    if normalized is not None:
        return normalized
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def parse_clock_minutes(value: Any) -> int | None:
    normalized = normalize_clock_time(value)
    if normalized is None:
        return None
    hh, mm = normalized.split(":")
    return int(hh) * 60 + int(mm)


def format_time_display(
    value: Any,
    *,
    blank_fallback: str | None = None,
    preserve_non_time: bool = True,
) -> str | None:
    normalized = normalize_clock_time(value)
    if normalized is not None:
        return normalized
    if value is None:
        return blank_fallback
    text = str(value).strip()
    if not text:
        return blank_fallback
    if preserve_non_time:
        return text
    return blank_fallback


def sanitize_time_text(text: str) -> str:
    return _TIME_WITH_SECONDS_RE.sub(r"\1:\2", text)
