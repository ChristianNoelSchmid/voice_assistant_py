from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

_REMIND = re.compile(r"")


@dataclass
class RemindToken:
    """Marks an utterance as a reminder request.

    content is empty at parse time; RemindCommand fills it in after subtracting
    all other token spans from the transcript.
    """

    content: str = field(default="")


def parse(text: str) -> Optional[tuple[RemindToken, tuple[int, int]]]:
    """Detect the 'remind'/'reminds' trigger word in *text*."""
    m = _REMIND.search(text)
    if m:
        return RemindToken(), (m.start(), m.end())
    return None
