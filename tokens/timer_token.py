from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

_TIMER_PAT = re.compile(r"(?i)\btimer\b")


@dataclass
class TimerToken:
    pass


def parse(text: str) -> Optional[TimerToken]:
    return TimerToken() if _TIMER_PAT.search(text) else None
