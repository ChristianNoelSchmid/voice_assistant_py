from __future__ import annotations

import queue
import subprocess
import sys
import threading
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


class QueuedSpeaker(Speaker):
    """Non-blocking speaker that serialises utterances on a dedicated thread.

    Callers return immediately from speak(); the background thread processes
    each item in order so playback never overlaps.
    """

    def __init__(self, backend: Speaker) -> None:
        self._backend = backend
        self._queue: queue.Queue[str] = queue.Queue()
        thread = threading.Thread(target=self._worker, daemon=True, name="Speaker")
        thread.start()

    def speak(self, text: str) -> None:
        self._queue.put(text)

    def _worker(self) -> None:
        while True:
            text = self._queue.get()
            self._backend.speak(text)
            self._queue.task_done()
