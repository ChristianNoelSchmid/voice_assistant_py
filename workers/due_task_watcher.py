from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta, timezone

from speaker import Speaker
from tasks.vikunja import TaskDueDate, VikunjaClient

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
        self._upcoming_reminders: list[TaskDueDate] = []

    def run(self) -> None:
        while True:
            while self._upcoming_reminders:
                reminder = self._upcoming_reminders.pop(0)
                print(f"[Watcher] Due: {reminder.title!r}")
                self._speaker.speak(f"Reminder: {reminder.title}")

            now = datetime.now(timezone.utc)
            self._refresh(now)

            seconds_until_poll = _POLL_INTERVAL
            if self._upcoming_reminders:
                sleep_for = min(
                    (self._upcoming_reminders[0].remind_at - now).total_seconds(),
                    _POLL_INTERVAL,
                )
            else:
                sleep_for = seconds_until_poll

            time.sleep(sleep_for)

    def _refresh(self, now: datetime):
        try:
            task_due_dates = self._client.get_project_task_due_dates(self._project_id)
            task_due_dates.sort(key=lambda x: x.remind_at)

            self._upcoming_reminders = list(
                filter(
                    lambda dd: (
                        now + timedelta(seconds=_POLL_INTERVAL + 10) > dd.remind_at
                    ),
                    task_due_dates,
                )
            )

            print(
                f"[Watcher] Cache refreshed: {len(self._upcoming_reminders)} upcoming reminder(s) ({len(task_due_dates)} total)"
            )
        except Exception as e:
            print(f"[Watcher] Failed to refresh cache: {e}")
