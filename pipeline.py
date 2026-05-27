from __future__ import annotations

import queue
import subprocess
import sys
import threading

from audio_input import AudioInput
from config import Config
from dispatcher import Dispatcher
from recognizer import SpeechRecognizer
from volume_ducker import VolumeDucker


class Pipeline:
    def __init__(
        self,
        config: Config,
        volume: VolumeDucker,
        recognizer: SpeechRecognizer,
        dispatcher: Dispatcher,
    ) -> None:
        self._config = config
        self._volume = volume
        self._recognizer = recognizer
        self._dispatcher = dispatcher

        self._wake_queue: queue.Queue[None] = queue.Queue()
        self._ducked = False
        self._wakeword_proc: subprocess.Popen | None = None

    def _start_wakeword(self) -> None:
        # Spawn the Python wake word detector as a child process. It writes "wake" to
        # stdout each time the wake word fires; we read that on a background thread.
        self._wakeword_proc = subprocess.Popen(
            [
                sys.executable,
                self._config.wakeword_script,
                self._config.wakeword_model,
                "--threshold",
                str(self._config.wakeword_threshold),
            ],
            stdout=subprocess.PIPE,
        )

        proc = self._wakeword_proc

        def watch() -> None:
            for line in proc.stdout:
                if line.strip() == b"wake":
                    self._wake_queue.put(None)
            print(
                "[Wakeword] detector exited — wake detection stopped", file=sys.stderr
            )

        threading.Thread(target=watch, daemon=True).start()

    def run(self) -> None:
        self._start_wakeword()

        with AudioInput() as audio:
            while True:
                # Non-blocking wake signal check before consuming the next audio chunk.
                try:
                    self._wake_queue.get_nowait()
                    if not self._ducked:
                        self._volume.duck()
                        self._ducked = True
                    self._dispatcher.activate()
                    self._recognizer.reset()
                except queue.Empty:
                    pass

                # Wait up to 50 ms for a chunk; short timeout keeps the wake check responsive.
                chunk = audio.get_chunk(timeout=0.05)
                if chunk is None:
                    if self._ducked and not self._dispatcher.is_active():
                        self._volume.unduck()
                        self._ducked = False
                    continue

                if not self._dispatcher.is_active():
                    if self._ducked:
                        self._volume.unduck()
                        self._ducked = False
                    continue

                event = self._recognizer.process(chunk)
                if event is not None:
                    self._dispatcher.dispatch(event)
                    # dispatch() only deactivates for FinalEvents; unduck only then.
                    if self._ducked and not self._dispatcher.is_active():
                        self._volume.unduck()
                        self._ducked = False

        if self._wakeword_proc:
            self._wakeword_proc.kill()
