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

from scripts.item_database import EQUIPMENT_SLOTS, get_item
from scripts.progression_config import (
    ATTRIBUTE_KEYS,
    MAX_ATTRIBUTE_RANK,
    MAX_DEFEATED_KEYS,
    MAX_LEVEL,
    START_LEVEL,
    attribute_points_for_level,
    clamp_int,
    exp_for_level,
    skill_points_for_level,
)
from scripts.skill_tree_config import VALID_NODE_IDS
from scripts.village_data import (
    DIALOGUE_IDS, MAX_SAVE_ENTRIES, MAX_UPGRADE_LEVEL, NPC_IDS,
)
from settings import BASE_DIR

SAVE_VERSION = 1
SAVE_DIR = BASE_DIR / "save"
SAVE_FILE = SAVE_DIR / "progress.json"
LOCAL_STORAGE_KEY = "ashen_veil_progress"

# A deliberately small starting kit.  The blade sits in the satchel but is not
# pre-equipped, keeping the untouched combat tuning identical to Phase 5.
DEFAULT_ITEMS = (
    {"id": "rusted_blade", "qty": 1},
    {"id": "minor_health_potion", "qty": 3},
    {"id": "void_potion", "qty": 2},
)
DEFAULT_EQUIPMENT = {
    "weapon": None,
    "helmet": None,
    "armor": None,
    "gloves": None,
    "boots": None,
    "ring": None,
    "necklace": None,
}


def default_save_file() -> Path:
    """Allow tools/tests (and power users) to redirect the profile."""
    override = os.environ.get("ASHEN_VEIL_SAVE")
    return Path(override) if override else SAVE_FILE


def default_inventory_data() -> dict:
    """Fresh satchel, starting consumables and the equipped village blade."""
    return {
        "gold": 120,
        "capacity": 28,
        "items": list(deepcopy(DEFAULT_ITEMS)),
        "equipped": dict(DEFAULT_EQUIPMENT),
    }


def default_player_data() -> dict:
    """A level-1 wanderer with no spent points or skill nodes."""
    return {
        "level": START_LEVEL,
        "exp": 0,
        "total_exp": 0,
        "attributes": {key: 0 for key in ATTRIBUTE_KEYS},
        "attribute_points": 0,
        "skill_points": 0,
        "skill_nodes": [],
    }


def default_npc_state() -> dict:
    """Phase 8: one small state record per village NPC."""
    return {
        npc_id: {"talked": False, "interactions": 0}
        for npc_id in NPC_IDS
    }


def default_dialogue_state() -> dict:
    """Phase 8: seen conversations and persistent story flags."""
    return {"seen": [], "flags": {}}


def default_shop_state() -> dict:
    """Phase 8: count of limited stock already bought, per item ID."""
    return {"purchases": {}}


def default_upgrade_state() -> dict:
    """Phase 8: blacksmith levels keyed by real equipment ID."""
    return {"levels": {}}


def default_quest_flags() -> dict:
    """Phase 8: reserved for future quests; empty in this build."""
    return {}


def default_data() -> dict:
    """A brand new profile: level 1, nothing completed, starter satchel."""
    return {
        "version": SAVE_VERSION,
        "levels": {},
        "player": default_player_data(),
        "inventory": default_inventory_data(),
        "defeated_enemies": [],
        # Additive Phase 8 village state.  Older saves simply omit these keys.
        "npc_state": default_npc_state(),
        "dialogue": default_dialogue_state(),
        "shop": default_shop_state(),
        "upgrades": default_upgrade_state(),
        "quest_flags": default_quest_flags(),
    }


def _number(value, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _clean_inventory(raw, player_level: int) -> dict:
    """Validate stored items/equipment; invalid IDs never reach the game."""
    clean = default_inventory_data()
    if not isinstance(raw, dict):
        return clean

    clean["gold"] = max(0, min(9_999_999, int(_number(raw.get("gold", 120), 120))))
    clean["capacity"] = max(12, min(28, int(_number(raw.get("capacity", 28), 28))))

    by_id: dict[str, int] = {}
    records = raw.get("items")
    if isinstance(records, (list, tuple)):
        for record in records:
            if not isinstance(record, dict):
                continue
            item_id = record.get("id")
            item = get_item(item_id)
            if item is None:
                continue
            quantity = max(1, int(_number(record.get("qty", 1), 1)))
            if item.stackable:
                by_id[item.item_id] = min(
                    item.max_stack,
                    by_id.get(item.item_id, 0) + quantity,
                )
            elif item.item_id not in by_id:
                by_id[item.item_id] = 1
            if len(by_id) >= clean["capacity"]:
                break

    equipped_raw = raw.get("equipped")
    equipped = dict(DEFAULT_EQUIPMENT)
    if isinstance(equipped_raw, dict):
        for slot in EQUIPMENT_SLOTS:
            item_id = equipped_raw.get(slot)
            item = get_item(item_id)
            if item is None or not item.is_equipment or item.slot != slot:
                continue
            if item.level_requirement > player_level:
                continue
            # Equipment without an owned copy would grant free stats.
            if item.item_id not in by_id:
                continue
            equipped[slot] = item.item_id
    clean["equipped"] = equipped
    clean["items"] = [
        {"id": item_id, "qty": quantity}
        for item_id, quantity in by_id.items()
    ]
    return clean


def _clean_player(raw) -> dict:
    """Validate every Phase 7 progression field; junk never reaches the game."""
    clean = default_player_data()
    if not isinstance(raw, dict):
        return clean

    # The historical 1..99 clamp is deliberately kept here: Phase 5 saves may
    # legitimately contain higher levels.  Gameplay itself caps at MAX_LEVEL in
    # ExpManager, which is also where a level-up writes the corrected value.
    clean["level"] = max(1, min(99, clamp_int(
        raw.get("level", START_LEVEL), 1, 99, START_LEVEL
    )))

    need = max(1, exp_for_level(clean["level"]))
    clean["exp"] = clamp_int(raw.get("exp", 0), 0, need, 0)
    clean["total_exp"] = max(
        clean["exp"],
        clamp_int(raw.get("total_exp", clean["exp"]), 0, 10 ** 9, clean["exp"]),
    )

    attrs = raw.get("attributes")
    if isinstance(attrs, dict):
        for key in ATTRIBUTE_KEYS:
            clean["attributes"][key] = clamp_int(
                attrs.get(key, 0), 0, MAX_ATTRIBUTE_RANK, 0
            )

    # Phase 5/6 profiles have no point counters: award what their saved level
    # already earned, minus attributes actually present in that old profile.
    legacy_attr = max(
        0,
        attribute_points_for_level(clean["level"]) - sum(
            clean["attributes"].values()
        ),
    )
    clean["attribute_points"] = clamp_int(
        raw.get("attribute_points", legacy_attr), 0, 10 ** 6, 0
    )
    clean["skill_points"] = clamp_int(
        raw.get("skill_points", skill_points_for_level(clean["level"])),
        0, 10 ** 6, 0,
    )

    nodes = raw.get("skill_nodes")
    if isinstance(nodes, (list, tuple, set)):
        for node_id in nodes:
            if isinstance(node_id, str) and node_id in VALID_NODE_IDS:
                if node_id not in clean["skill_nodes"]:
                    clean["skill_nodes"].append(node_id)
    return clean


def _clean_defeated(raw) -> list[str]:
    """Deduplicate and bound the persistent anti-farming marker list."""
    clean: list[str] = []
    if isinstance(raw, (list, tuple, set)):
        for key in raw:
            if isinstance(key, str) and key and key not in clean:
                clean.append(key[:80])
            if len(clean) >= MAX_DEFEATED_KEYS:
                break
    return clean


def _clean_count(value, low: int = 0, high: int = 9999) -> int:
    """Integer clamp that also rejects NaN/Infinity from hand-edited saves."""
    number = _number(value, 0.0)
    if number != number or number in (float("inf"), float("-inf")):
        return low
    return max(low, min(high, int(number)))


def _clean_npc_state(raw) -> dict:
    """Keep only known NPC IDs and bounded counters."""
    clean = default_npc_state()
    if not isinstance(raw, dict):
        return clean
    for npc_id in NPC_IDS:
        entry = raw.get(npc_id)
        if not isinstance(entry, dict):
            continue
        clean[npc_id]["talked"] = bool(entry.get("talked", False))
        clean[npc_id]["interactions"] = _clean_count(
            entry.get("interactions", 0), 0, 9999
        )
    return clean


def _clean_dialogue_state(raw) -> dict:
    """Validate seen IDs and story flags without trusting the file shape."""
    clean = default_dialogue_state()
    if not isinstance(raw, dict):
        return clean
    seen = raw.get("seen")
    if isinstance(seen, (list, tuple, set)):
        for dialogue_id in seen:
            if (isinstance(dialogue_id, str) and dialogue_id in DIALOGUE_IDS
                    and dialogue_id not in clean["seen"]):
                clean["seen"].append(dialogue_id)
    flags = raw.get("flags")
    if isinstance(flags, dict):
        for key, value in flags.items():
            if len(clean["flags"]) >= MAX_SAVE_ENTRIES:
                break
            name = str(key).strip().lower()[:48]
            if name:
                clean["flags"][name] = bool(value)
    return clean


def _clean_shop_state(raw) -> dict:
    """Limited-stock counters only for real item IDs."""
    clean = default_shop_state()
    if not isinstance(raw, dict):
        return clean
    records = raw.get("purchases")
    if isinstance(records, dict):
        for key, value in records.items():
            if get_item(key) is None:
                continue
            if len(clean["purchases"]) >= MAX_SAVE_ENTRIES:
                break
            count = _clean_count(value, 0, 9999)
            if count:
                clean["purchases"][str(key)] = count
    return clean


def _clean_upgrade_state(raw) -> dict:
    """Forge levels only for real equipment, clamped to +0..+5."""
    clean = default_upgrade_state()
    if not isinstance(raw, dict):
        return clean
    records = raw.get("levels")
    if isinstance(records, dict):
        for key, value in records.items():
            item = get_item(key)
            if item is None or not item.is_equipment:
                continue
            if len(clean["levels"]) >= MAX_SAVE_ENTRIES:
                break
            level = _clean_count(value, 0, MAX_UPGRADE_LEVEL)
            if level:
                clean["levels"][str(key)] = level
    return clean


def _clean_quest_flags(raw) -> dict:
    """Forward-compatible quest flags: arbitrary keys, bounded and boolean."""
    clean: dict[str, bool] = {}
    if isinstance(raw, dict):
        for key, value in raw.items():
            if len(clean) >= MAX_SAVE_ENTRIES:
                break
            name = str(key).strip().lower()[:48]
            if name:
                clean[name] = bool(value)
    return clean


def canonical_data(raw) -> dict:
    """Return a well-shaped profile built from arbitrary loaded data."""
    data = default_data()
    if not isinstance(raw, dict):
        return data

    data["player"] = _clean_player(raw.get("player"))
    data["defeated_enemies"] = _clean_defeated(raw.get("defeated_enemies"))

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

    data["inventory"] = _clean_inventory(
        raw.get("inventory"), data["player"]["level"]
    )

    # Additive Phase 8 sections.  Missing keys fall back to empty defaults, so
    # Phase 5/6/7 profiles keep loading unchanged and the version stays 1.
    data["npc_state"] = _clean_npc_state(raw.get("npc_state"))
    data["dialogue"] = _clean_dialogue_state(raw.get("dialogue"))
    data["shop"] = _clean_shop_state(raw.get("shop"))
    data["upgrades"] = _clean_upgrade_state(raw.get("upgrades"))
    data["quest_flags"] = _clean_quest_flags(raw.get("quest_flags"))

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
    "default_dialogue_state",
    "default_inventory_data",
    "default_npc_state",
    "default_player_data",
    "default_quest_flags",
    "default_save_file",
    "default_shop_state",
    "default_upgrade_state",
    "load_profile",
]
