"""Level unlock rules and progression queries on top of the JSON save.

Level 01 is always open.  Every later level unlocks when the previous entry is
marked complete, which in this build means its boss was defeated.  All writes
go through ``SaveManager`` so a browser refresh and a desktop restart see the
same profile.
"""
from __future__ import annotations

from scripts.level_config import LEVELS, get_level, level_index, next_level_id
from scripts.save_manager import SaveManager, default_data


class ProgressionManager:
    def __init__(self, save_manager: SaveManager | None = None) -> None:
        self.save = save_manager or SaveManager()
        self.data = self.save.load()
        self._ensure_entries()

    # ------------------------------------------------------------------
    def _ensure_entries(self) -> None:
        levels = self.data.setdefault("levels", {})
        for level in LEVELS:
            entry = levels.setdefault(level.level_id, {})
            entry.setdefault("completed", False)
            entry.setdefault("boss_defeated", False)
            entry.setdefault("stages_cleared", 0)

    # ------------------------------------------------------------------
    @property
    def player_level(self) -> int:
        return int(self.data.get("player", {}).get("level", 7))

    def entry(self, level_id: str) -> dict:
        return self.data.setdefault("levels", {}).setdefault(
            level_id,
            {"completed": False, "boss_defeated": False, "stages_cleared": 0},
        )

    def is_completed(self, level_id: str) -> bool:
        return bool(self.entry(level_id).get("completed", False))

    def boss_defeated(self, level_id: str) -> bool:
        return bool(self.entry(level_id).get("boss_defeated", False))

    def stages_cleared(self, level_id: str) -> int:
        try:
            return max(0, int(self.entry(level_id).get("stages_cleared", 0)))
        except (TypeError, ValueError):
            return 0

    def is_unlocked(self, level_id: str) -> bool:
        index = level_index(level_id)
        if index <= 0:
            return True
        previous = LEVELS[index - 1]
        return self.is_completed(previous.level_id)

    def is_playable(self, level_id: str) -> bool:
        level = get_level(level_id)
        return bool(level.playable and self.is_unlocked(level_id))

    def unlock_hint(self, level_id: str) -> str:
        if self.is_unlocked(level_id):
            return ""
        index = level_index(level_id)
        if index <= 0:
            return ""
        previous = LEVELS[index - 1]
        return f"CLEAR LEVEL {previous.level_id} TO UNLOCK"

    def status_label(self, level_id: str) -> str:
        level = get_level(level_id)
        if not self.is_unlocked(level_id):
            return "LOCKED"
        if self.is_completed(level_id):
            return "COMPLETE"
        if not level.playable:
            return "UNLOCKED"
        return "AVAILABLE"

    # ------------------------------------------------------------------
    def record_stage(self, level_id: str, stages_cleared: int) -> None:
        entry = self.entry(level_id)
        highest = max(int(entry.get("stages_cleared", 0)), int(stages_cleared))
        if highest != entry.get("stages_cleared"):
            entry["stages_cleared"] = highest
            self.save_now()

    def complete_level(self, level_id: str) -> bool:
        """Mark a level complete, persist it, and report a new unlock."""
        entry = self.entry(level_id)
        level = get_level(level_id)
        was_complete = bool(entry.get("completed", False))
        entry["completed"] = True
        entry["boss_defeated"] = True
        entry["stages_cleared"] = max(
            int(entry.get("stages_cleared", 0)), len(level.stages) or 1
        )
        self.save_now()
        return not was_complete

    def record_player_level(self, level: int) -> None:
        self.data.setdefault("player", {})["level"] = max(1, min(99, int(level)))
        self.save_now()

    def save_now(self) -> bool:
        return self.save.save(self.data)

    # ------------------------------------------------------------------
    def next_unplayed_level(self) -> str:
        """Best selection after returning from a victory screen."""
        for level in LEVELS:
            if (self.is_unlocked(level.level_id)
                    and not self.is_completed(level.level_id)):
                return level.level_id
        return LEVELS[0].level_id

    def selection_after_victory(self, completed_level_id: str) -> str:
        following = next_level_id(completed_level_id)
        if following and self.is_unlocked(following):
            return following
        return self.next_unplayed_level()

    def reset_progress(self) -> None:
        self.data = default_data()
        self._ensure_entries()
        self.save_now()


__all__ = ["ProgressionManager"]
