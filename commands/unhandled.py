from __future__ import annotations

from commands import CommandHandler
from speaker import Speaker


class UnhandledCommand(CommandHandler):
    """Fallback handler that speaks back any unrecognized command.

    Always matches, so it must be last in the handler list.
    """

    def __init__(self, speaker: Speaker) -> None:
        self._speaker = speaker

    def parse(self, text: str) -> str:
        """Always matches — returns the text verbatim."""
        return text

    async def handle(self, match: str) -> None:
        text = f"Quack! You said {match}"
        print(text)
        await self._speaker.speak(text)
