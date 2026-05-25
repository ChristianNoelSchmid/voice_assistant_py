from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from speaker import Speaker
    from tasks.vikunja import VikunjaClient

_POLL_INTERVAL = 10  # 10 minutes


@dataclass(frozen=True, order=True)
class _Reminder:
    remind_at: datetime
    task_id: int
    title: str


class DueTaskWatcher(threading.Thread):
    """Background thread that caches task reminders sorted by time and announces them when due."""

    def __init__(
        self, client: VikunjaClient, speaker: Speaker, project_id: int
    ) -> None:
        super().__init__(daemon=True, name="DueTaskWatcher")
        self._client = client
        self._speaker = speaker
        self._project_id = project_id
        self._cache: list[_Reminder] = []

    def run(self) -> None:
        self._refresh()
        last_poll = time.monotonic()

        while True:
            now = datetime.now(timezone.utc)

            while self._cache and self._cache[0].remind_at <= now:
                reminder = self._cache.pop(0)
                print(f"[Watcher] Due: {reminder.title!r}")
                self._speaker.speak(f"Reminder: {reminder.title}")

            seconds_until_poll = _POLL_INTERVAL - (time.monotonic() - last_poll)
            if self._cache:
                sleep_for = min(
                    (self._cache[0].remind_at - now).total_seconds(), seconds_until_poll
                )
            else:
                sleep_for = seconds_until_poll

            time.sleep(max(0.0, sleep_for))

            if time.monotonic() - last_poll >= _POLL_INTERVAL:
                self._refresh()
                last_poll = time.monotonic()

    def _refresh(self) -> None:
        try:
            tasks = self._client.get_project_tasks(self._project_id)
            now = datetime.now(timezone.utc)
            reminders: list[_Reminder] = []
            for task in tasks:
                for r in task.get("reminders") or []:
                    remind_str = r.get("reminder")
                    if not remind_str:
                        continue
                    try:
                        remind_at = datetime.fromisoformat(
                            remind_str.replace("Z", "+00:00")
                        )
                    except ValueError:
                        continue
                    if remind_at > now:
                        reminders.append(
                            _Reminder(
                                remind_at=remind_at,
                                task_id=task["id"],
                                title=task["title"],
                            )
                        )
            reminders.sort()
            self._cache = reminders
            print(f"[Watcher] Cache refreshed: {len(reminders)} upcoming reminder(s)")
        except Exception as e:
            print(f"[Watcher] Failed to refresh cache: {e}")
