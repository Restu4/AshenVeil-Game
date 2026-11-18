"""Read-only access to the Phase 8 village data files.

Every NPC, dialogue, stock list and forge recipe lives in ``data/`` so a later
content pass never has to touch gameplay code.  Loading is defensive: a broken
or missing file yields an empty collection rather than taking the game down.
"""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from settings import BASE_DIR

DATA_DIR: Path = BASE_DIR / "data"
NPC_DIR = DATA_DIR / "npcs"
DIALOGUE_DIR = DATA_DIR / "dialogue"
SHOP_DIR = DATA_DIR / "shops"
BLACKSMITH_DIR = DATA_DIR / "blacksmith"

NPC_FILES = ("merchant.json", "blacksmith.json", "veil_keeper.json")
NPC_IDS = ("merchant", "blacksmith", "veil_keeper")
DIALOGUE_IDS = ("merchant", "blacksmith", "veil_keeper")
MAX_UPGRADE_LEVEL = 5
MAX_SAVE_ENTRIES = 96

_cache: dict[str, object] = {}


def load_json(path: Path) -> dict | None:
    try:
        if not path.is_file():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else None
    except (OSError, ValueError, UnicodeError):
        return None


def reload() -> None:
    _cache.clear()


def npc_definitions() -> list[dict]:
    cached = _cache.get("npcs")
    if cached is not None:
        return deepcopy(cached)
    result: list[dict] = []
    for filename in NPC_FILES:
        raw = load_json(NPC_DIR / filename)
        if not isinstance(raw, dict):
            continue
        npc_id = str(raw.get("id", "")).strip().lower()
        if npc_id not in NPC_IDS:
            continue
        result.append(raw)
    _cache["npcs"] = result
    return deepcopy(result)


def dialogue_definition(dialogue_id: str) -> dict | None:
    key = f"dialogue:{dialogue_id}"
    cached = _cache.get(key)
    if cached is not None:
        return deepcopy(cached)
    if dialogue_id not in DIALOGUE_IDS:
        return None
    raw = load_json(DIALOGUE_DIR / f"{dialogue_id}_dialogue.json")
    if isinstance(raw, dict):
        _cache[key] = raw
        return deepcopy(raw)
    return None


def shop_stock() -> dict:
    cached = _cache.get("shop")
    if cached is not None:
        return deepcopy(cached)
    raw = load_json(SHOP_DIR / "merchant_stock.json") or {}
    _cache["shop"] = raw
    return deepcopy(raw)


def upgrade_config() -> dict:
    cached = _cache.get("upgrades")
    if cached is not None:
        return deepcopy(cached)
    raw = load_json(BLACKSMITH_DIR / "upgrades.json") or {}
    _cache["upgrades"] = raw
    return deepcopy(raw)


__all__ = [
    "BLACKSMITH_DIR", "DATA_DIR", "DIALOGUE_DIR", "DIALOGUE_IDS",
    "MAX_SAVE_ENTRIES", "MAX_UPGRADE_LEVEL", "NPC_DIR", "NPC_FILES",
    "NPC_IDS", "SHOP_DIR", "dialogue_definition", "load_json",
    "npc_definitions", "reload", "shop_stock", "upgrade_config",
]
