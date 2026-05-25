from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from commands import CommandHandler
from speaker import Speaker
from tasks import TaskClient

_SHOPPING_RE = re.compile(
    r"(?i)(add|put|and )?(.+) (and|to|in)( (my|the))? (grocer(?:y|ies)|shopping)(?: list)?"
)


@dataclass
class ShoppingMatch:
    """Parsed item extracted from an 'add X to my shopping list' utterance."""

    item: str


class ShoppingCommand(CommandHandler):
    """Handles 'add [item] to my (grocery|shopping)[ list]' → adds an item to Vikunja."""

    def __init__(self, client: TaskClient, speaker: Speaker, project_id: int) -> None:
        self._client = client
        self._speaker = speaker
        self._project_id = project_id

    def parse(self, text: str) -> Optional[ShoppingMatch]:
        """Return a ShoppingMatch if text matches the shopping list pattern."""
        m = _SHOPPING_RE.search(text)
        if not m:
            return None
        item = " ".join(m.group(2).split())
        return ShoppingMatch(item=item)

    def handle(self, match: ShoppingMatch) -> None:
        print(f'[Shopping] "{match.item}"')
        try:
            self._client.create_task(
                match.item, None, None, None, self._project_id
            )
            print("[Shopping] Item added.")
            self._speaker.speak(f'Added "{match.item}" to your shopping list.')
        except Exception as e:
            print(f"[Shopping] Failed to add item: {e}")
