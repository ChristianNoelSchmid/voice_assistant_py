from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

# "at 1244 PM" — no symbol or space between
_AT_TIME_WITHOUT_MINUTES = re.compile(r"(?i)\b(\d{1,2})\s*(am?|pm?)\b")
_AT_TIME_WITH_MINUTES = re.compile(r"(?i)\b(\d{1,2})(?:-|:|.|\s)?(\d{2})\s*(am?|pm?)\b")
_AT_NOON = re.compile(r"(?i)\bnoon\b")
_AT_MIDNIGHT = re.compile(r"(?i)\bmidnight\b")


@dataclass
class TimeToken:
    """A clock time parsed from phrases like 'at 9:30 PM', 'at noon', or 'at midnight'."""

    hour: int  # 0–23
    minute: int  # 0–59


def _apply_ampm(hour: int, minute: int, ampm: str) -> tuple[int, int]:
    if ampm.lower()[0] == "p" and hour != 12:
        hour += 12
    elif ampm.lower()[0] == "a" and hour == 12:
        hour = 0
    return min(hour, 23), min(minute, 59)


def parse(text: str) -> Optional[tuple[TimeToken, tuple[int, int]]]:
    """Parse a clock time from *text*, returning (token, (start, end)) or None."""
    m = _AT_NOON.search(text)
    if m:
        return TimeToken(hour=12, minute=0), (m.start(), m.end())

    m = _AT_MIDNIGHT.search(text)
    if m:
        return TimeToken(hour=0, minute=0), (m.start(), m.end())

    m = _AT_TIME_WITH_MINUTES.search(text)
    if m:
        hour, minute = _apply_ampm(int(m.group(1)), int(m.group(2) or 0), m.group(3))
        return TimeToken(hour=hour, minute=minute), (m.start(), m.end())

    m = _AT_TIME_WITHOUT_MINUTES.search(text)
    if m:
        hour, minute = _apply_ampm(int(m.group(1)), 0, m.group(2))
        return TimeToken(hour=hour, minute=minute), (m.start(), m.end())

    return None
