#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

from commands.clock import ClockCommand
from commands.remind import RemindCommand
from commands.shopping import ShoppingCommand
from commands.timer import TimerCommand
from commands.unhandled import UnhandledCommand
from config import Config
from dispatcher import Dispatcher
from pipeline import Pipeline
from recognizer import SpeechRecognizer
from speaker import PiperSpeaker
from tasks.vikunja import VikunjaClient
from volume_ducker import VolumeDucker
from workers.due_task_watcher import DueTaskWatcher


def main() -> None:
    load_dotenv()

    config = Config.load("config.json")

    vikunja_token = os.environ.get("VIKUNJA_TOKEN", "")
    if not vikunja_token:
        sys.exit("VIKUNJA_TOKEN is not set")

    vikunja = VikunjaClient(config.vikunja_url, vikunja_token)
    speaker = PiperSpeaker(
        config.piper_bin, config.piper_model, config.piper_sample_rate
    )
    volume = VolumeDucker(config.volume_duck_level)

    handlers = [
        RemindCommand(vikunja, speaker, config.vikunja_project_id),
        ShoppingCommand(vikunja, speaker, config.vikunja_shopping_project_id),
        ClockCommand(speaker),
        TimerCommand(speaker),
        UnhandledCommand(speaker),
    ]
    dispatcher = Dispatcher(handlers)

    print(f"Loading Whisper model '{config.whisper_model}'...")
    recognizer = SpeechRecognizer(config.whisper_model)

    DueTaskWatcher(vikunja, speaker, config.vikunja_project_id).start()

    print("Ready. Listening for wake word...\n")
    speaker.speak("Ready.")

    Pipeline(config, volume, recognizer, dispatcher).run()


if __name__ == "__main__":
    main()
