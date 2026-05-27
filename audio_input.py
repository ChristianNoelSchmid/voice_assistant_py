from __future__ import annotations

import queue

import numpy as np
import sounddevice as sd

_SAMPLE_RATE = 16000
_CHUNK = 4000
_QUEUE_MAX = 64


class AudioInput:
    def __init__(self) -> None:
        self._queue: queue.Queue[bytes] = queue.Queue(maxsize=_QUEUE_MAX)
        self._stream: sd.InputStream | None = None

    def _callback(self, indata: np.ndarray, frames: int, time_info, status) -> None:
        try:
            self._queue.put_nowait(indata.tobytes())
        except queue.Full:
            pass

    def get_chunk(self, timeout: float = 0.05) -> bytes | None:
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def __enter__(self) -> AudioInput:
        self._stream = sd.InputStream(
            samplerate=_SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=_CHUNK,
            callback=self._callback,
        )
        self._stream.__enter__()
        return self

    def __exit__(self, *args) -> None:
        if self._stream:
            self._stream.__exit__(*args)
