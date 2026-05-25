#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import os
import sys

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

AUDIO_SAMPLE_RATE = 16000
AUDIO_CHUNK = 1024
AUDIO_QUEUE_MAX = 64


def _safe_put(q: asyncio.Queue, item: object) -> None:
    """Put *item* onto *q* without blocking; silently drops if the queue is full."""
    try:
        q.put_nowait(item)
    except asyncio.QueueFull:
        pass


async def main() -> None:
    load_dotenv()

    config = Config.load("config.json")

    vikunja_token = os.environ.get("VIKUNJA_TOKEN", "")
    if not vikunja_token:
        sys.exit("VIKUNJA_TOKEN is not set")

    vikunja = VikunjaClient(config.vikunja_url, vikunja_token)
    speaker = PiperSpeaker(config.piper_bin, config.piper_model, config.piper_sample_rate)

    handlers = [
        RemindCommand(vikunja, speaker, config.vikunja_project_id),
        ShoppingCommand(vikunja, speaker, config.vikunja_shopping_project_id),
        ClockCommand(speaker),
        UnhandledCommand(speaker),
    ]
    dispatcher = Dispatcher(handlers)

    print(f"Loading model from '{config.vosk_model}'...")
    recognizer = SpeechRecognizer(config.vosk_model)

    loop = asyncio.get_running_loop()
    audio_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=AUDIO_QUEUE_MAX)
    wake_queue: asyncio.Queue[None] = asyncio.Queue()

    def audio_callback(indata: np.ndarray, frames: int, time_info, status) -> None:
        pcm = (indata[:, 0] * 32767).astype(np.int16).tobytes()
        loop.call_soon_threadsafe(_safe_put, audio_queue, pcm)

    # Spawn the Python wake word detector as a child process. It writes "wake" to
    # stdout each time the wake word fires; we read that here on a background task.
    wakeword_proc = await asyncio.create_subprocess_exec(
        sys.executable,
        config.wakeword_script,
        config.wakeword_model,
        "--threshold", str(config.wakeword_threshold),
        stdout=asyncio.subprocess.PIPE,
    )

    async def watch_wakeword() -> None:
        async for line in wakeword_proc.stdout:
            if line.strip() == b"wake":
                await wake_queue.put(None)
        print("[Wakeword] detector exited — wake detection stopped", file=sys.stderr)

    asyncio.create_task(watch_wakeword())

    print("Ready. Listening for wake word...\n")
    await speaker.speak("Ready.")

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
                dispatcher.activate()
                recognizer.reset()
            except asyncio.QueueEmpty:
                pass

            # Wait up to 50 ms for a chunk; short timeout keeps the wake check responsive.
            try:
                chunk = await asyncio.wait_for(audio_queue.get(), timeout=0.05)
            except asyncio.TimeoutError:
                continue

            if not dispatcher.is_active():
                continue

            # Vosk is CPU-bound; run in a thread so it doesn't stall the event loop.
            event = await loop.run_in_executor(None, recognizer.process, chunk)
            if event is not None:
                await dispatcher.dispatch(event)

    wakeword_proc.kill()


if __name__ == "__main__":
    asyncio.run(main())
