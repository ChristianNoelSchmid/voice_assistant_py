from __future__ import annotations

import json
from dataclasses import dataclass

from vosk import KaldiRecognizer, Model

SAMPLE_RATE = 16000


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
    """Wraps a Vosk KaldiRecognizer, converting raw PCM bytes into RecognitionEvents."""

    def __init__(self, model_path: str) -> None:
        self._model = Model(model_path)
        self._rec = KaldiRecognizer(self._model, float(SAMPLE_RATE))

    def reset(self) -> None:
        """Discard partial state and start fresh — call when entering active mode."""
        self._rec = KaldiRecognizer(self._model, float(SAMPLE_RATE))

    def process(self, data: bytes) -> RecognitionEvent | None:
        """Feed a raw PCM chunk and return an event if one is ready, else None."""
        if self._rec.AcceptWaveform(data):
            text = json.loads(self._rec.Result()).get("text", "").strip()
            return FinalEvent(text) if text else None
        partial = json.loads(self._rec.PartialResult()).get("partial", "").strip()
        return PartialEvent(partial) if partial else None
