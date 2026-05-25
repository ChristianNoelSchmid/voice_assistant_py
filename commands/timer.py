from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Optional

from commands import CommandHandler
from speaker import Speaker
from tokens.timer_token import TimerToken
from tokens.timer_token import parse as parse_timer


@dataclass
class TimerMatch:
    token: TimerToken


class TimerCommand(CommandHandler):
    """Handles 'timer [for] N minutes/hours/seconds' → counts down and announces when done."""

    def __init__(self, speaker: Speaker) -> None:
        self._speaker = speaker

    def parse(self, text: str) -> Optional[TimerMatch]:
        result = parse_timer(text)
        if result is None:
            return None
        token, _ = result
        return TimerMatch(token=token)

    def handle(self, match: TimerMatch) -> None:
        seconds = match.token.seconds
        label = _format_duration(seconds)
        print(f"[Timer] Set for {label}")
        self._speaker.speak(f"Timer set for {label}.")
        threading.Timer(seconds, self._announce, args=(label,)).start()

    def _announce(self, label: str) -> None:
        print(f"[Timer] Elapsed: {label}")
        self._speaker.speak(f"Timer done. Your {label} timer has elapsed.")


def _format_duration(seconds: int) -> str:
    if seconds % 3600 == 0:
        n = seconds // 3600
        return f"{n} hour{'s' if n != 1 else ''}"
    if seconds % 60 == 0:
        n = seconds // 60
        return f"{n} minute{'s' if n != 1 else ''}"
    return f"{seconds} second{'s' if seconds != 1 else ''}"
