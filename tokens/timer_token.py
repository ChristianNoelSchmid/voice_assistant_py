from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

_UNIT_SECONDS: dict[str, int] = {"second": 1, "minute": 60, "hour": 3600}

# Matches "timer [for] N (hours|minutes|seconds)" anywhere in an utterance.
_TIMER_PAT = re.compile(
    r"(?i)\btimer\s+(?:for\s+)?(\d+)\s+(hours?|minutes?|seconds?)\b"
)


@dataclass
class TimerToken:
    seconds: int


def parse(text: str) -> Optional[tuple[TimerToken, tuple[int, int]]]:
    """Parse a timer duration from *text*, returning (token, (start, end)) or None."""
    m = _TIMER_PAT.search(text)
    if not m:
        return None
    count = int(m.group(1))
    unit = m.group(2).lower().rstrip("s")
    return TimerToken(seconds=count * _UNIT_SECONDS[unit]), (m.start(), m.end())
