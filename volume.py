from __future__ import annotations

import json
import re
import subprocess
import sys


class VolumeController:
    """Ducks other applications' audio output streams via PipeWire.

    Uses pw-dump to enumerate Stream/Output/Audio nodes and wpctl to get/set
    their volumes. The assistant's own TTS creates a new node after duck()
    returns and is therefore never affected.
    """

    def __init__(self, duck_level: float = 0.3) -> None:
        self._duck_level = f"{duck_level:.2f}"
        self._saved: dict[str, str] = {}  # node_id → original volume

    def duck(self) -> None:
        """Lower all active audio output streams to the duck level."""
        if self._saved:
            return
        for node_id, vol in self._stream_nodes():
            _wpctl("set-volume", node_id, self._duck_level)
            self._saved[node_id] = vol
        if self._saved:
            pct = int(float(self._duck_level) * 100)
            print(f"[Volume] ducked {len(self._saved)} stream(s) to {pct}%", flush=True)

    def unduck(self) -> None:
        """Restore streams saved by the last duck() call."""
        if not self._saved:
            return
        for node_id, vol in self._saved.items():
            _wpctl("set-volume", node_id, vol)
        print(f"[Volume] restored {len(self._saved)} stream(s)", flush=True)
        self._saved.clear()

    def _stream_nodes(self) -> list[tuple[str, str]]:
        """Return (node_id, volume) for all active Stream/Output/Audio nodes."""
        try:
            raw = subprocess.run(
                ["pw-dump"], capture_output=True, text=True, timeout=5
            ).stdout
            nodes = json.loads(raw)
        except Exception as exc:
            print(f"[Volume] pw-dump failed: {exc}", file=sys.stderr)
            return []

        streams = []
        for node in nodes:
            if node.get("type") != "PipeWire:Interface:Node":
                continue
            props = node.get("info", {}).get("props", {})
            if props.get("media.class") != "Stream/Output/Audio":
                continue
            node_id = str(node["id"])
            vol = _get_volume(node_id)
            if vol is not None:
                streams.append((node_id, vol))
        return streams


def _get_volume(node_id: str) -> str | None:
    try:
        out = subprocess.run(
            ["wpctl", "get-volume", node_id],
            capture_output=True, text=True, timeout=2,
        ).stdout
        m = re.search(r"Volume:\s*([\d.]+)", out)
        return m.group(1) if m else None
    except Exception as exc:
        print(f"[Volume] could not get volume for node {node_id}: {exc}", file=sys.stderr)
        return None


def _wpctl(*args: str) -> None:
    try:
        subprocess.run(["wpctl", *args], capture_output=True, timeout=2)
    except Exception as exc:
        print(f"[Volume] wpctl {' '.join(args)} failed: {exc}", file=sys.stderr)
