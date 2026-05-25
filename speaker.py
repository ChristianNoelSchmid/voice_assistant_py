from __future__ import annotations

import subprocess
import sys
from abc import ABC, abstractmethod

import numpy as np
import sounddevice as sd


class Speaker(ABC):
    """Abstraction over a text-to-speech backend."""

    @abstractmethod
    def speak(self, text: str) -> None:
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

    def speak(self, text: str) -> None:
        """Synthesise *text* with Piper and block until playback finishes."""
        proc = subprocess.run(
            [self._bin, "--model", self._model, "--output-raw"],
            input=text.encode(),
            capture_output=True,
        )
        if proc.returncode != 0:
            print(
                f"[Speaker] piper failed (exit {proc.returncode}): {proc.stderr.decode()}",
                file=sys.stderr,
            )
            return
        samples = np.frombuffer(proc.stdout, dtype=np.int16)
        sd.play(samples, samplerate=self._rate, blocking=True)
