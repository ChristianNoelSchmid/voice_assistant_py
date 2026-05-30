#!/usr/bin/env python3
"""Wake word detector using OpenWakeWord. Writes 'wake\\n' to stdout on detection.
Designed to be spawned by the voice assistant and communicate via stdout."""

import argparse
import glob
import os
import sys

import numpy as np
import openwakeword
import sounddevice as sd
from openwakeword.model import Model

SAMPLE_RATE = 16000
CHUNK_SIZE = 1280  # 80 ms at 16 kHz — required frame size for OpenWakeWord


def resolve_model(name: str) -> str:
    """Return the ONNX file path for `name`.

    Accepts either an existing file path or a short name (e.g. 'hey_jarvis'),
    which is resolved against the bundled openwakeword model directory.
    """
    if os.path.isfile(name):
        return name
    model_dir = os.path.join(
        os.path.dirname(openwakeword.__file__), "resources", "models"
    )
    # Exclude preprocessor/utility models from candidate search
    skip = {"embedding_model.onnx", "melspectrogram.onnx", "silero_vad.onnx"}
    candidates = [
        p
        for p in glob.glob(os.path.join(model_dir, f"{name}*.onnx"))
        if os.path.basename(p) not in skip
    ]
    if candidates:
        return candidates[0]
    raise FileNotFoundError(f"No bundled model found for '{name}' in {model_dir}")


def main():
    parser = argparse.ArgumentParser(description="OpenWakeWord detector")
    parser.add_argument(
        "model", help="Model name (e.g. 'hey_jarvis') or path to .onnx file"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.25,
        help="Detection score threshold (default: 0.5)",
    )
    parser.add_argument(
        "--device",
        default=None,
        help="Input device index or name substring (default: system default)",
    )
    args = parser.parse_args()

    model_path = resolve_model(args.model)
    model = Model(wakeword_model_paths=[model_path])
    print(
        f"Wakeword detector ready (model={model_path}, threshold={args.threshold})",
        file=sys.stderr,
        flush=True,
    )

    def callback(indata, frames, time, status):
        if status:
            print(f"Audio status: {status}", file=sys.stderr, flush=True)
        # indata is float32 from sounddevice; OpenWakeWord expects int16
        audio = (indata[:, 0] * 32767).astype(np.int16)
        scores = model.predict(audio)
        if scores and max(scores.values()) >= args.threshold:
            print("wake", flush=True)
            # Reset internal state to avoid repeated triggers from the same utterance
            model.reset()

    # Convert numeric string to int so sounddevice can select by index
    device = args.device
    if device is not None:
        try:
            device = int(device)
        except ValueError:
            pass

    with sd.InputStream(
        device=device,
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        blocksize=CHUNK_SIZE,
        callback=callback,
    ):
        sd.sleep(10_000_000)


if __name__ == "__main__":
    main()
