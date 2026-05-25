#!/usr/bin/env python3
from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading

import numpy as np
import sounddevice as sd
from dotenv import load_dotenv

from commands.clock import ClockCommand
from commands.remind import RemindCommand
from commands.shopping import ShoppingCommand
from commands.unhandled import UnhandledCommand
from config import Config
from dispatcher import Dispatcher
from recognizer import SpeechRecognizer
from speaker import PiperSpeaker
from tasks.vikunja import VikunjaClient
from volume import VolumeController

AUDIO_SAMPLE_RATE = 16000
AUDIO_CHUNK = 1024
AUDIO_QUEUE_MAX = 64


def main() -> None:
    load_dotenv()

    config = Config.load("config.json")

    vikunja_token = os.environ.get("VIKUNJA_TOKEN", "")
    if not vikunja_token:
        sys.exit("VIKUNJA_TOKEN is not set")

    vikunja = VikunjaClient(config.vikunja_url, vikunja_token)
    speaker = PiperSpeaker(config.piper_bin, config.piper_model, config.piper_sample_rate)
    volume = VolumeController(config.volume_duck_level)

    handlers = [
        RemindCommand(vikunja, speaker, config.vikunja_project_id),
        ShoppingCommand(vikunja, speaker, config.vikunja_shopping_project_id),
        ClockCommand(speaker),
        UnhandledCommand(speaker),
    ]
    dispatcher = Dispatcher(handlers)

    print(f"Loading model from '{config.vosk_model}'...")
    recognizer = SpeechRecognizer(config.vosk_model)

    audio_queue: queue.Queue[bytes] = queue.Queue(maxsize=AUDIO_QUEUE_MAX)
    wake_queue: queue.Queue[None] = queue.Queue()

    def audio_callback(indata: np.ndarray, frames: int, time_info, status) -> None:
        pcm = (indata[:, 0] * 32767).astype(np.int16).tobytes()
        try:
            audio_queue.put_nowait(pcm)
        except queue.Full:
            pass

    # Spawn the Python wake word detector as a child process. It writes "wake" to
    # stdout each time the wake word fires; we read that on a background thread.
    wakeword_proc = subprocess.Popen(
        [sys.executable, config.wakeword_script, config.wakeword_model,
         "--threshold", str(config.wakeword_threshold)],
        stdout=subprocess.PIPE,
    )

    def watch_wakeword() -> None:
        for line in wakeword_proc.stdout:
            if line.strip() == b"wake":
                wake_queue.put(None)
        print("[Wakeword] detector exited — wake detection stopped", file=sys.stderr)

    threading.Thread(target=watch_wakeword, daemon=True).start()

    print("Ready. Listening for wake word...\n")
    speaker.speak("Ready.")

    ducked = False

    with sd.InputStream(
        samplerate=AUDIO_SAMPLE_RATE,
        channels=1,
        dtype="float32",
        blocksize=AUDIO_CHUNK,
        callback=audio_callback,
    ):
        while True:
            # Non-blocking wake signal check before consuming the next audio chunk.
            try:
                wake_queue.get_nowait()
                if not ducked:
                    volume.duck()
                    ducked = True
                dispatcher.activate()
                recognizer.reset()
            except queue.Empty:
                pass

            # Wait up to 50 ms for a chunk; short timeout keeps the wake check responsive.
            try:
                chunk = audio_queue.get(timeout=0.05)
            except queue.Empty:
                if ducked and not dispatcher.is_active():
                    volume.unduck()
                    ducked = False
                continue

            if not dispatcher.is_active():
                if ducked:
                    volume.unduck()
                    ducked = False
                continue

            event = recognizer.process(chunk)
            if event is not None:
                dispatcher.dispatch(event)
                # dispatch() only deactivates for FinalEvents; unduck only then.
                if ducked and not dispatcher.is_active():
                    volume.unduck()
                    ducked = False

    wakeword_proc.kill()


if __name__ == "__main__":
    main()
