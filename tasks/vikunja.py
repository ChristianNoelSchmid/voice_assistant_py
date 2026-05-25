from __future__ import annotations

from datetime import datetime
from typing import Optional

import httpx

from tasks import TaskClient


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
            body["reminders"] = [{"relative_period": 0, "relative_to": "due_date"}]
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

    def get_project_tasks(self, project_id: int) -> list[dict]:
        """Return all tasks for *project_id*, handling pagination."""
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
        }
        tasks: list[dict] = []
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
                tasks.extend(batch)
                if len(batch) < 50:
                    break
                page += 1
        return tasks
