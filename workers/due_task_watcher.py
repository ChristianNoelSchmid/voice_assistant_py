from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from tasks.vikunja import TaskDueDate

if TYPE_CHECKING:
    from speaker import Speaker
    from tasks.vikunja import VikunjaClient

_POLL_INTERVAL = 10  # 10 minutes


class DueTaskWatcher(threading.Thread):
    """Background thread that caches task reminders sorted by time and announces them when due."""

    def __init__(
        self, client: VikunjaClient, speaker: Speaker, project_id: int
    ) -> None:
        super().__init__(daemon=True, name="DueTaskWatcher")
        self._client = client
        self._speaker = speaker
        self._project_id = project_id
        self._cache: list[TaskDueDate] = []

    def run(self) -> None:
        while True:
            self._refresh()
            last_poll = time.monotonic()

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

    def _refresh(self) -> None:
        try:
            task_due_dates = self._client.get_project_task_due_dates(self._project_id)

            for t in task_due_dates:
                if not any(map(lambda c: c.task_id == t.task_id, self._cache)):
                    self._cache.append(t)

            self._cache.sort(key=lambda x: x.remind_at)

            print(f"[Watcher] Cache refreshed: {len(self._cache)} upcoming reminder(s)")
        except Exception as e:
            print(f"[Watcher] Failed to refresh cache: {e}")
