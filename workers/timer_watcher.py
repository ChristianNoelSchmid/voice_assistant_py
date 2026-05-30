from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from speaker import Speaker


@dataclass
class _PendingTimer:
    fire_at: datetime
    label: str


class TimerWatcher(threading.Thread):
    """Background thread that fires speaker announcements when timers elapse."""

    def __init__(self, speaker: Speaker) -> None:
        super().__init__(daemon=True, name="TimerWatcher")
        self._speaker = speaker
        self._timers: list[_PendingTimer] = []
        self._lock = threading.Lock()
        self._event = threading.Event()

    def add(self, seconds: int, label: str) -> None:
        fire_at = datetime.now(timezone.utc) + timedelta(seconds=seconds)
        with self._lock:
            self._timers.append(_PendingTimer(fire_at=fire_at, label=label))
            self._timers.sort(key=lambda t: t.fire_at)
        self._event.set()

    def run(self) -> None:
        while True:
            self._event.clear()

            now = datetime.now(timezone.utc)
            with self._lock:
                due = [t for t in self._timers if t.fire_at <= now]
                self._timers = [t for t in self._timers if t.fire_at > now]

            for timer in due:
                print(f"[TimerWatcher] Elapsed: {timer.label}")
                self._speaker.speak(f"Timer done. Your {timer.label} timer has elapsed.")

            with self._lock:
                sleep_for = (
                    (self._timers[0].fire_at - datetime.now(timezone.utc)).total_seconds()
                    if self._timers
                    else None
                )

            self._event.wait(timeout=sleep_for)
