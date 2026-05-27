from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import httpx

from tasks import TaskClient


@dataclass(frozen=True, order=True)
class TaskDueDate:
    remind_at: datetime
    task_id: int
    title: str


class VikunjaClient(TaskClient):
    """TaskClient backed by a Vikunja instance.

    base_url should have no trailing slash (Config.load strips it).
    token is the Vikunja API token from VIKUNJA_TOKEN.
    """

    def __init__(self, base_url: str, token: str) -> None:
        self._base_url = base_url
        self._token = token

    def create_task(
        self,
        title: str,
        due_date: Optional[datetime],
        repeat_after: Optional[int],
        repeat_mode: Optional[int],
        project_id: int,
    ) -> None:
        """Create a task via the Vikunja REST API. Uses PUT, not POST."""
        body: dict = {"title": title}
        if due_date is not None:
            body["due_date"] = due_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        if repeat_after is not None:
            body["repeat_after"] = repeat_after
        if repeat_mode is not None:
            body["repeat_mode"] = repeat_mode

        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
        }
        url = f"{self._base_url}/api/v1/projects/{project_id}/tasks"
        with httpx.Client() as client:
            resp = client.put(url, json=body, headers=headers)
            if resp.status_code >= 400:
                raise RuntimeError(
                    f"Vikunja API returned {resp.status_code}: {resp.text}"
                )

    def get_project_task_due_dates(self, project_id: int) -> list[TaskDueDate]:
        """Return all reminder for *project_id*, handling pagination."""
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
        }

        tasks: list[TaskDueDate] = []
        page = 1
        with httpx.Client() as client:
            while True:
                url = f"{self._base_url}/api/v1/projects/{project_id}/tasks"
                resp = client.get(
                    url, headers=headers, params={"page": page, "per_page": 50}
                )
                if resp.status_code >= 400:
                    raise RuntimeError(
                        f"Vikunja API returned {resp.status_code}: {resp.text}"
                    )
                batch: list[dict] = resp.json()

                if not batch:
                    break

                for b in batch:
                    task = self._vinkuja_task_to_due_date(b)
                    if task is not None:
                        tasks.append(task)

                if len(batch) < 50:
                    break

                page += 1
        return tasks

    def _vinkuja_task_to_due_date(self, task) -> TaskDueDate | None:
        if "done" not in task or task["done"]:
            return None

        due_date_str = task["due_date"]
        if not due_date_str:
            return None
        try:
            remind_at = datetime.fromisoformat(due_date_str.replace("Z", "+00:00"))
        except ValueError:
            return None

        if remind_at > datetime.now(timezone.utc):
            return TaskDueDate(
                remind_at=remind_at,
                task_id=task["id"],
                title=task["title"],
            )
