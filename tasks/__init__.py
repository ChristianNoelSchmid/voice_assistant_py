from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional


class TaskClient(ABC):
    """Abstraction over a task-management backend (e.g. Vikunja)."""

    @abstractmethod
    def create_task(
        self,
        title: str,
        due_date: Optional[datetime],
        repeat_after: Optional[int],
        repeat_mode: Optional[int],
        project_id: int,
    ) -> None:
        """Create a new task in *project_id* with an optional due date and recurrence.

        repeat_after and repeat_mode are backend-specific; see VikunjaClient for semantics.
        """
        ...
