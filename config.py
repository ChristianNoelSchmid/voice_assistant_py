from __future__ import annotations

import json
from dataclasses import dataclass, fields
from pathlib import Path


@dataclass
class Config:
    """Application configuration loaded from a JSON file.

    All runtime values except VIKUNJA_TOKEN live here; the token stays in
    the environment so it can be kept out of the config file and source control.
    """

    whisper_model: str
    vikunja_url: str
    vikunja_project_id: int
    vikunja_shopping_project_id: int
    piper_bin: str
    piper_model: str
    wakeword_script: str
    wakeword_model: str
    piper_sample_rate: int = 22050
    wakeword_threshold: float = 0.25
    volume_duck_level: float = 0.3
    mic_device: int | str | None = None

    @classmethod
    def load(cls, path: str = "config.json") -> Config:
        """Read and validate config from a JSON file at *path*."""
        with open(path) as f:
            data = json.load(f)
        data["vikunja_url"] = data["vikunja_url"].rstrip("/")
        known = {f.name for f in fields(cls)}
        config = cls(**{k: v for k, v in data.items() if k in known})
        config.validate()
        return config

    def validate(self) -> None:
        """Raise ValueError if any required path is missing or a field is invalid."""
        if not self.whisper_model:
            raise ValueError("whisper_model must not be empty")
        if "/" in self.piper_bin and not Path(self.piper_bin).is_file():
            raise ValueError(f"piper_bin '{self.piper_bin}' not found")
        if not Path(self.piper_model).is_file():
            raise ValueError(f"piper_model '{self.piper_model}' not found")
        if not self.vikunja_url:
            raise ValueError("vikunja_url must not be empty")
        if not Path(self.wakeword_script).is_file():
            raise ValueError(f"wakeword_script '{self.wakeword_script}' not found")
        if not self.wakeword_model:
            raise ValueError("wakeword_model must not be empty")
