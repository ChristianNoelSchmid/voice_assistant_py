from __future__ import annotations

from abc import ABC, abstractmethod

from tokens.normalize import normalize


class CommandHandler(ABC):
    """Base class for voice command handlers.

    Subclasses implement parse() and handle(). The try_handle() method
    normalizes the transcript, calls parse(), and if it matches calls handle()
    and returns True so the dispatcher knows the command was claimed.
    """

    @abstractmethod
    def parse(self, text: str):
        """Try to extract a typed match from normalized *text*. Return None to skip."""
        ...

    @abstractmethod
    def handle(self, match) -> None:
        """Act on a successfully parsed match object."""
        ...

    def try_handle(self, text: str) -> bool:
        """Normalize, parse, and handle. Returns True if this handler claimed the command."""
        normalized = normalize(text)
        match = self.parse(normalized)
        if match is not None:
            self.handle(match)
            return True
        return False
