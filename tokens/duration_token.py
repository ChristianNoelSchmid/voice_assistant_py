from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

_WORD_NUMS: dict[str, int] = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "fifteen": 15,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "ninety": 90,
}

_UNIT_SECONDS: dict[str, int] = {"second": 1, "minute": 60, "hour": 3600}

_WORD_NUM_PAT = "|".join(re.escape(w) for w in _WORD_NUMS)
_IN_DURATION = re.compile(
    rf"(?i)\bin\s+(\d+|{_WORD_NUM_PAT})\s+(hours?|minutes?|seconds?)\b"
)


@dataclass
class DurationToken:
    """A relative offset parsed from phrases like 'in 5 minutes' or 'in one hour'."""

    seconds: int


def parse(text: str) -> Optional[tuple[DurationToken, tuple[int, int]]]:
    """Parse a relative duration from *text*, returning (token, (start, end)) or None."""
    m = _IN_DURATION.search(text)
    if not m:
        return None
    raw = m.group(1).lower()
    count = int(raw) if raw.isdigit() else _WORD_NUMS.get(raw, 1)
    unit = m.group(2).lower().rstrip("s")  # "hours" → "hour", etc.
    seconds = count * _UNIT_SECONDS[unit]
    return DurationToken(seconds=seconds), (m.start(), m.end())
