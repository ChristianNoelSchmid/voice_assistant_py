from __future__ import annotations

import time
from typing import TYPE_CHECKING

from recognizer import FinalEvent, RecognitionEvent

if TYPE_CHECKING:
    from commands import CommandHandler

COMMAND_TIMEOUT = 10.0


class Dispatcher:
    """State machine: Idle → Active on external wake signal, dispatches commands to handlers."""

    def __init__(self, handlers: list[CommandHandler]) -> None:
        self._handlers = handlers
        self._active = False
        self._deadline = 0.0

    def activate(self) -> None:
        """Transition to Active state. Called by the external wake word detector."""
        print(
            f"[Activated] Listening for a command ({COMMAND_TIMEOUT:.0f}s timeout)...",
            flush=True,
        )
        self._active = True
        self._deadline = time.monotonic() + COMMAND_TIMEOUT

    def is_active(self) -> bool:
        """Return True while waiting for a command, timing out if the deadline has passed."""
        if self._active and time.monotonic() >= self._deadline:
            print("[Timed out — back to idle]", flush=True)
            self._active = False
        return self._active

    def dispatch(self, event: RecognitionEvent) -> None:
        """Route a finalized recognition event to the first matching handler."""
        if not isinstance(event, FinalEvent):
            return
        # Return to idle before running handlers so audio buffered during playback
        # cannot re-trigger a command.
        self._active = False
        for handler in self._handlers:
            if handler.try_handle(event.text):
                break
