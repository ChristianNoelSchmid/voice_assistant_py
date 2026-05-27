from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

# "at 1244 PM" — no symbol or space between
_AT_TIME = re.compile(r"(?i)\bat\s+(\d{1,2})(:|.|\s)?(\d{2})?\s*(am?|pm?)\b")
# "at 12 40 4 PM" — ASR splits "forty-four" into tens digit + ones digit
_AT_TIME_SPLIT = re.compile(r"(?i)\bat\s+(\d{1,2})\s+([1-5]0)\s+([1-9])\s*(am?|pm?)\b")
_AT_NOON = re.compile(r"(?i)\bat\s+noon\b")
_AT_MIDNIGHT = re.compile(r"(?i)\bat\s+midnight\b")


@dataclass
class TimeToken:
    """A clock time parsed from phrases like 'at 9:30 PM', 'at noon', or 'at midnight'."""

    hour: int  # 0–23
    minute: int  # 0–59


def _apply_ampm(hour: int, minute: int, ampm: str) -> tuple[int, int]:
    if ampm.lower() == "pm" and hour != 12:
        hour += 12
    elif ampm.lower() == "am" and hour == 12:
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

    # Check split-minute form first ("at 12 40 4 PM") before space form ("at 12 44 PM")
    # so "40 4" isn't accidentally matched as minute=40.
    m = _AT_TIME_SPLIT.search(text)
    if m:
        hour, minute = _apply_ampm(
            int(m.group(1)), int(m.group(2)) + int(m.group(3)), m.group(4)
        )
        return TimeToken(hour=hour, minute=minute), (m.start(), m.end())

    m = _AT_TIME.search(text)
    if m:
        hour, minute = _apply_ampm(int(m.group(1)), int(m.group(3) or 0), m.group(4))
        return TimeToken(hour=hour, minute=minute), (m.start(), m.end())

    return None
