from __future__ import annotations

import queue

import numpy as np
import sounddevice as sd

_SAMPLE_RATE = 16000
_CHUNK = 4000
_QUEUE_MAX = 64


class AudioInput:
    def __init__(self, device: int | str | None = None) -> None:
        self._device = device
        self._native_rate: int = _SAMPLE_RATE
        self._queue: queue.Queue[bytes] = queue.Queue(maxsize=_QUEUE_MAX)
        self._stream: sd.InputStream | None = None

    def _callback(self, indata: np.ndarray, frames: int, time_info, status) -> None:
        try:
            if self._native_rate != _SAMPLE_RATE:
                samples = indata[:, 0].astype(np.float32)
                resampled = np.interp(
                    np.linspace(0, len(samples), _CHUNK, endpoint=False),
                    np.arange(len(samples)),
                    samples,
                ).astype(np.int16)
                self._queue.put_nowait(resampled.tobytes())
            else:
                self._queue.put_nowait(indata.tobytes())
        except queue.Full:
            pass

    def get_chunk(self, timeout: float = 0.05) -> bytes | None:
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def __enter__(self) -> AudioInput:
        device_info = sd.query_devices(self._device, kind="input")
        self._native_rate = int(device_info["default_samplerate"])
        native_blocksize = int(round(_CHUNK * self._native_rate / _SAMPLE_RATE))
        self._stream = sd.InputStream(
            device=self._device,
            samplerate=self._native_rate,
            channels=1,
            dtype="int16",
            blocksize=native_blocksize,
            callback=self._callback,
        )
        self._stream.__enter__()
        return self

    def __exit__(self, *args) -> None:
        if self._stream:
            self._stream.__exit__(*args)
