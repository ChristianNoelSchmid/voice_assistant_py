from __future__ import annotations

from datetime import datetime
from typing import Optional

from commands import CommandHandler
from speaker import Speaker


class ClockCommand(CommandHandler):
    """Handles 'what time is it' and similar queries by speaking the current time."""

    def __init__(self, speaker: Speaker) -> None:
        self._speaker = speaker

    def parse(self, text: str) -> Optional[str]:
        """Match any utterance containing the word 'time'."""
        return text if "time" in text else None

    def handle(self, match: str) -> None:
        now = datetime.now()
        hour = now.hour % 12 or 12
        ampm = "PM" if now.hour >= 12 else "AM"
        self._speaker.speak(f"It is {hour} {now.minute:02d} {ampm}")
