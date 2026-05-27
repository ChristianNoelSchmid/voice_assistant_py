from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from faster_whisper import WhisperModel

SAMPLE_RATE = 16000
_SILENCE_RMS = 10  # int16 RMS below this counts as silence
_SILENCE_FRAMES = (
    4  # consecutive silent chunks to end an utterance (~1 s at 4000/16000)
)
_MIN_SPEECH_FRAMES = 2  # minimum speech chunks before transcribing (~0.5 s)


@dataclass
class PartialEvent:
    """An in-progress hypothesis — text may change as more audio arrives."""

    text: str


@dataclass
class FinalEvent:
    """A stable, end-of-utterance transcript."""

    text: str


RecognitionEvent = PartialEvent | FinalEvent


class SpeechRecognizer:
    """Buffers PCM audio and transcribes with Whisper when end-of-speech is detected."""

    def __init__(self, model_name: str) -> None:
        self._model = WhisperModel(model_name, device="cpu", compute_type="int8")
        self._buffer: list[bytes] = []
        self._silent_frames = 0
        self._speech_frames = 0

    def reset(self) -> None:
        """Discard buffered audio and VAD state — call when entering active mode."""
        self._buffer = []
        self._silent_frames = 0
        self._speech_frames = 0

    def process(self, data: bytes) -> RecognitionEvent | None:
        """Buffer a PCM chunk; return FinalEvent when end-of-speech is detected."""
        samples = np.frombuffer(data, dtype=np.int16)
        rms = float(np.sqrt(np.mean(samples.astype(np.float32) ** 2)))

        is_silent = rms < _SILENCE_RMS
        print(
            f"[VAD] rms={rms:.0f} {'S' if is_silent else 'X'} speech={self._speech_frames} silent={self._silent_frames}",
            flush=True,
        )
        if is_silent:
            self._silent_frames += 1
        else:
            self._silent_frames = 0
            self._speech_frames += 1

        self._buffer.append(data)

        if (
            self._silent_frames >= _SILENCE_FRAMES
            and self._speech_frames >= _MIN_SPEECH_FRAMES
        ):
            text = self._transcribe()
            self.reset()
            if text:
                print(text)
                return FinalEvent(text)
            else:
                return None

        return None

    def _transcribe(self) -> str:
        audio = (
            np.frombuffer(b"".join(self._buffer), dtype=np.int16).astype(np.float32)
            / 32768.0
        )
        segments, _ = self._model.transcribe(audio, language="en", beam_size=1)
        return " ".join(s.text.strip() for s in segments).strip()
