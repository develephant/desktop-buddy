import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import QPoint
from PySide6.QtGui import QPixmap


class Sprite:
    """Loads a drop-in sprite directory and drives its animation states."""

    def __init__(self, name: str = "default") -> None:
        self.sprites_root = Path(__file__).parent / "sprites"
        self.sprite_dir = self.sprites_root / name
        if not self.sprite_dir.is_dir():
            raise FileNotFoundError(f"Sprite directory not found: {self.sprite_dir}")

        manifest_path = self.sprite_dir / "sprite.json"
        with open(manifest_path, "r", encoding="utf-8") as f:
            self._manifest = json.load(f)

        self.width = int(self._manifest.get("width", 128))
        self.height = int(self._manifest.get("height", 128))
        self.global_fps = float(self._manifest.get("fps", 8))

        self.states: dict[str, dict[str, Any]] = {}
        self.frames: dict[str, list[QPixmap]] = {}
        for state_name, state_cfg in self._manifest.get("states", {}).items():
            frame_files = state_cfg.get("frames", [])
            if not frame_files:
                continue
            self.states[state_name] = {
                "fps": float(state_cfg.get("fps", self.global_fps)),
                "loop": bool(state_cfg.get("loop", True)),
            }
            self.frames[state_name] = [
                QPixmap(str(self.sprite_dir / filename))
                for filename in frame_files
            ]

        if not self.frames:
            raise ValueError("No valid animation states found in sprite.json")

        self._first_state = next(iter(self.frames))
        fallback = self._manifest.get("default_state", "idle")
        self._fallback_state = fallback if fallback in self.frames else self._first_state
        self.default_state = self._fallback_state

        self._time_table: dict[int, str] = {}
        for state_name, hours in self._manifest.get("time_states", {}).items():
            if state_name not in self.frames:
                continue
            for h in hours:
                if isinstance(h, int) and 0 <= h <= 23:
                    self._time_table[h] = state_name

        self.statics: dict[str, dict[str, Any]] = {}
        for layer in ("base", "overlay"):
            cfg = self._manifest.get("statics", {}).get(layer)
            if cfg:
                image = cfg.get("image")
                pixmap = QPixmap(str(self.sprite_dir / image)) if image else None
                self.statics[layer] = {
                    "pixmap": pixmap,
                    "pos": QPoint(int(cfg.get("x", 0)), int(cfg.get("y", 0))),
                }
            else:
                self.statics[layer] = {"pixmap": None, "pos": QPoint(0, 0)}

        self._state = self.default_state
        self._frame_index = 0
        self._accumulator = 0.0
        self._last_time = time.monotonic()

    @property
    def state(self) -> str:
        return self._state

    def _resolve(self, name: str) -> str:
        if name in self.frames:
            return name
        return self._fallback_state if self._fallback_state in self.frames else self._first_state

    def ambient_state(self) -> str:
        """Return the state the pet should be in based on the current hour."""
        hour = datetime.now().hour
        return self._time_table.get(hour, self._fallback_state)

    def set_state(self, name: str) -> None:
        self._state = self._resolve(name)
        self._frame_index = 0
        self._accumulator = 0.0

    def size(self) -> tuple[int, int]:
        return self.width, self.height

    def base(self) -> tuple[QPixmap | None, QPoint]:
        return self.statics["base"]["pixmap"], self.statics["base"]["pos"]

    def overlay(self) -> tuple[QPixmap | None, QPoint]:
        return self.statics["overlay"]["pixmap"], self.statics["overlay"]["pos"]

    def current_frame(self) -> QPixmap:
        return self.frames[self._state][self._frame_index]

    def update(self, dt: float | None = None) -> None:
        if self._state not in self.frames:
            return
        if dt is None:
            now = time.monotonic()
            dt = now - self._last_time
            self._last_time = now

        cfg = self.states[self._state]
        fps = cfg["fps"]
        if fps <= 0:
            return

        self._accumulator += dt
        frame_duration = 1.0 / fps
        frames = self.frames[self._state]
        if len(frames) <= 1:
            return

        while self._accumulator >= frame_duration:
            self._accumulator -= frame_duration
            self._frame_index += 1
            if self._frame_index >= len(frames):
                if cfg["loop"]:
                    self._frame_index = 0
                else:
                    self._frame_index = 0
                    self._state = self._resolve(self.default_state)
                    break

    def reset(self) -> None:
        self._state = self.default_state
        self._frame_index = 0
        self._accumulator = 0.0
