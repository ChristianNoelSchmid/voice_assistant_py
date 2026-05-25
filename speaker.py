from __future__ import annotations

import asyncio
import sys
from abc import ABC, abstractmethod

import numpy as np
import sounddevice as sd


class Speaker(ABC):
    """Abstraction over a text-to-speech backend."""

    @abstractmethod
    async def speak(self, text: str) -> None:
        """Synthesise *text* and block until playback has fully completed."""
        ...


class PiperSpeaker(Speaker):
    """Speaker backed by a local Piper process.

    Spawns piper with --output-raw, feeds text to its stdin, then plays the
    resulting raw 16-bit PCM through the default output device via sounddevice.
    """

    def __init__(self, bin_path: str, model_path: str, sample_rate: int = 22050) -> None:
        self._bin = bin_path
        self._model = model_path
        self._rate = sample_rate

    async def speak(self, text: str) -> None:
        """Synthesise *text* with Piper and block until playback finishes."""
        proc = await asyncio.create_subprocess_exec(
            self._bin,
            "--model", self._model,
            "--output-raw",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate(input=text.encode())
        if proc.returncode != 0:
            print(
                f"[Speaker] piper failed (exit {proc.returncode}): {stderr.decode()}",
                file=sys.stderr,
            )
            return

        samples = np.frombuffer(stdout, dtype=np.int16)
        loop = asyncio.get_running_loop()
        # sd.play + sd.wait are blocking; run them in a thread to keep the event loop free.
        await loop.run_in_executor(
            None, lambda: sd.play(samples, samplerate=self._rate, blocking=True)
        )
