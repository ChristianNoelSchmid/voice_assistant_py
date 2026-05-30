from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from commands import CommandHandler
from speaker import Speaker
from tokens.duration_token import DurationToken
from tokens.duration_token import parse as parse_duration
from tokens.timer_token import parse as parse_timer
from workers.timer_watcher import TimerWatcher


@dataclass
class TimerMatch:
    duration: DurationToken


class TimerCommand(CommandHandler):
    """Handles utterances containing 'timer' and a duration, e.g. 'timer 5 minutes'."""

    def __init__(self, watcher: TimerWatcher, speaker: Speaker) -> None:
        self._watcher = watcher
        self._speaker = speaker

    def parse(self, text: str) -> Optional[TimerMatch]:
        if parse_timer(text) is None:
            return None
        result = parse_duration(text)
        if result is None:
            return None
        token, _ = result
        return TimerMatch(duration=token)

    def handle(self, match: TimerMatch) -> None:
        label = _format_duration(match.duration.seconds)
        print(f"[Timer] Set for {label}")
        self._speaker.speak(f"Timer set for {label}.")
        self._watcher.add(match.duration.seconds, label)


def _format_duration(seconds: int) -> str:
    if seconds % 3600 == 0:
        n = seconds // 3600
        return f"{n} hour{'s' if n != 1 else ''}"
    if seconds % 60 == 0:
        n = seconds // 60
        return f"{n} minute{'s' if n != 1 else ''}"
    return f"{seconds} second{'s' if seconds != 1 else ''}"
