"""Small, forgiving JSON save for ASHEN VEIL progression.

The save is deliberately tiny and versioned.  On desktop it lives next to the
game in ``save/progress.json``.  In Pygbag the same JSON is also mirrored to
``window.localStorage`` so a browser refresh keeps the unlock even if the
virtual filesystem is reset.

Loading never trusts the file: a missing, unreadable, truncated or
wrong-shaped save falls back to a clean default instead of crashing the game.
"""
from __future__ import annotations

import json
import os
import sys
from copy import deepcopy
from pathlib import Path

from settings import BASE_DIR

SAVE_VERSION = 1
SAVE_DIR = BASE_DIR / "save"
SAVE_FILE = SAVE_DIR / "progress.json"
LOCAL_STORAGE_KEY = "ashen_veil_progress"


def default_save_file() -> Path:
    """Allow tools/tests (and power users) to redirect the profile."""
    override = os.environ.get("ASHEN_VEIL_SAVE")
    return Path(override) if override else SAVE_FILE


def default_data() -> dict:
    """A brand new profile: nothing completed, the player keeps their level."""
    return {
        "version": SAVE_VERSION,
        "levels": {},
        "player": {"level": 7},
    }


def _number(value, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def canonical_data(raw) -> dict:
    """Return a well-shaped profile built from arbitrary loaded data."""
    data = default_data()
    if not isinstance(raw, dict):
        return data

    player = raw.get("player")
    if isinstance(player, dict):
        level = int(_number(player.get("level", 7), 7))
        data["player"]["level"] = max(1, min(99, level))

    levels = raw.get("levels")
    if isinstance(levels, dict):
        clean: dict[str, dict] = {}
        for key, entry in levels.items():
            if not isinstance(entry, dict):
                continue
            clean[str(key)] = {
                "completed": bool(entry.get("completed", False)),
                "boss_defeated": bool(entry.get("boss_defeated", False)),
                "stages_cleared": max(
                    0, int(_number(entry.get("stages_cleared", 0), 0))
                ),
            }
        data["levels"] = clean

    version = int(_number(raw.get("version", SAVE_VERSION), SAVE_VERSION))
    data["version"] = max(1, version)
    return data


class SaveManager:
    """Read/write the profile, optionally mirroring it to browser storage."""

    def __init__(self, path: Path | None = None,
                 use_local_storage: bool = True) -> None:
        self.path = Path(path) if path is not None else default_save_file()
        self.use_local_storage = use_local_storage

    # ------------------------------------------------------------------
    def load(self) -> dict:
        raw = self._read_file()
        if raw is None:
            raw = self._read_local_storage()
        return canonical_data(raw)

    def save(self, data: dict) -> bool:
        payload = canonical_data(data)
        payload["version"] = SAVE_VERSION
        text = json.dumps(payload, indent=2, sort_keys=True)
        ok = self._write_file(text)
        # The localStorage mirror is best-effort; it must never raise.
        self._write_local_storage(text)
        return ok

    def exists(self) -> bool:
        try:
            return self.path.is_file()
        except OSError:
            return False

    def clear(self) -> None:
        try:
            self.path.unlink()
        except OSError:
            pass
        self._write_local_storage("")

    # ------------------------------------------------------------------
    def _read_file(self):
        try:
            if not self.path.is_file():
                return None
            text = self.path.read_text(encoding="utf-8")
            if not text.strip():
                return None
            return json.loads(text)
        except (OSError, ValueError, UnicodeError):
            return None

    def _write_file(self, text: str) -> bool:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp = self.path.with_suffix(".tmp")
            temp.write_text(text, encoding="utf-8")
            os.replace(temp, self.path)
            return True
        except (OSError, ValueError):
            return False

    # ------------------------------------------------------------------
    def _storage(self):
        if not self.use_local_storage:
            return None
        if sys.platform != "emscripten":
            return None
        try:
            import platform  # type: ignore[import-not-found]
            window = getattr(platform, "window", None)
            return getattr(window, "localStorage", None)
        except Exception:
            return None

    def _read_local_storage(self):
        storage = self._storage()
        if storage is None:
            return None
        try:
            text = storage.getItem(LOCAL_STORAGE_KEY)
            if not text:
                return None
            return json.loads(text)
        except Exception:
            return None

    def _write_local_storage(self, text: str) -> None:
        storage = self._storage()
        if storage is None:
            return
        try:
            if text:
                storage.setItem(LOCAL_STORAGE_KEY, text)
            else:
                storage.removeItem(LOCAL_STORAGE_KEY)
        except Exception:
            pass


def load_profile(path: Path | None = None) -> dict:
    """Convenience wrapper used by tools and tests."""
    return deepcopy(SaveManager(path).load())


__all__ = [
    "SAVE_FILE",
    "SAVE_VERSION",
    "SaveManager",
    "canonical_data",
    "default_data",
    "default_save_file",
    "load_profile",
]
