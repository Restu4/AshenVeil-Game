"""Data-driven item definitions for ASHEN VEIL.

Every item lives in ``data/items/*.json``.  This module is the single place that
reads and validates those files, so the save manager, inventory, loot and UI all
share exactly one view of what an item is.  A missing or broken file degrades to
an empty catalogue rather than crashing the game.
"""
from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path

from settings import BASE_DIR

ITEM_DIR: Path = BASE_DIR / "data" / "items"
ITEM_FILES = (
    "weapons.json",
    "armor.json",
    "accessories.json",
    "consumables.json",
)
LOOT_FILE = "loot_tables.json"

# Canonical equipment slots, in the order the interface draws them.
EQUIPMENT_SLOTS = (
    "weapon", "helmet", "armor", "gloves", "boots", "ring", "necklace",
)
SLOT_LABELS = {
    "weapon": "WEAPON",
    "helmet": "HELMET",
    "armor": "ARMOR",
    "gloves": "GLOVES",
    "boots": "BOOTS",
    "ring": "RING",
    "necklace": "NECKLACE",
    "consumable": "CONSUMABLE",
    "material": "MATERIAL",
}

# Rarity order drives borders, value and UI colour.  Purple is reserved for
# epic and a restrained glow for legendary; common gear stays plain.
RARITIES = ("common", "uncommon", "rare", "epic", "legendary")
RARITY_ORDER = {name: index for index, name in enumerate(RARITIES)}
RARITY_LABELS = {name: name.upper() for name in RARITIES}
RARITY_COLORS = {
    "common": (166, 158, 148),
    "uncommon": (112, 192, 136),
    "rare": (102, 158, 232),
    "epic": (190, 130, 244),
    "legendary": (240, 186, 92),
}
RARITY_DARK = {
    "common": (68, 64, 62),
    "uncommon": (42, 78, 56),
    "rare": (38, 62, 96),
    "epic": (74, 44, 104),
    "legendary": (94, 66, 30),
}

STAT_KEYS = (
    "attack", "defense", "max_hp", "speed",
    "crit_chance", "crit_damage", "max_void",
)
STAT_LABELS = {
    "attack": "ATTACK",
    "defense": "DEFENSE",
    "max_hp": "MAX HP",
    "speed": "SPEED",
    "crit_chance": "CRIT CHANCE",
    "crit_damage": "CRIT DAMAGE",
    "max_void": "MAX VOID",
}
STAT_IS_PERCENT = {"crit_chance", "crit_damage"}

DEFAULT_LOOT_TABLE: dict = {
    "settings": {"max_drops": 24, "pickup_radius": 52.0,
                 "world_lifetime": 0.0},
    "regular": {},
    "elite": {},
    "boss": {},
}


@dataclass(frozen=True)
class ItemDef:
    item_id: str
    name: str
    description: str
    slot: str
    rarity: str
    icon: str
    value: int
    level_requirement: int
    stats: dict[str, float] = field(default_factory=dict)
    effect: dict = field(default_factory=dict)
    category: str = "equipment"
    stackable: bool = False
    max_stack: int = 1

    @property
    def rarity_color(self) -> tuple[int, int, int]:
        return RARITY_COLORS[self.rarity]

    @property
    def rarity_label(self) -> str:
        return RARITY_LABELS[self.rarity]

    @property
    def slot_label(self) -> str:
        return SLOT_LABELS.get(self.slot, self.slot.upper())

    @property
    def is_equipment(self) -> bool:
        return self.category == "equipment"

    @property
    def is_consumable(self) -> bool:
        return self.category == "consumable"

    @property
    def is_material(self) -> bool:
        return self.category == "material"

    @property
    def effect_kind(self) -> str:
        kind = self.effect.get("kind")
        return kind if isinstance(kind, str) else "none"

    @property
    def effect_amount(self) -> float:
        return _number(self.effect.get("amount", 0.0), 0.0)

    @property
    def effect_text(self) -> str:
        text = self.effect.get("text")
        return str(text) if isinstance(text, str) else ""


def _number(value, fallback: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return fallback
    if result != result or result in (float("inf"), float("-inf")):
        return fallback
    return result


def _integer(value, fallback: int, minimum: int = 0,
             maximum: int = 10_000) -> int:
    return max(minimum, min(maximum, int(_number(value, fallback))))


def _coerce_stats(raw) -> dict[str, float]:
    if not isinstance(raw, dict):
        return {}
    clean: dict[str, float] = {}
    for key, value in raw.items():
        key = str(key).strip().lower()
        if key not in STAT_KEYS:
            continue
        number = _number(value)
        if number == 0.0:
            continue
        clean[key] = number
    return clean


def _coerce_effect(raw) -> dict:
    if not isinstance(raw, dict):
        return {"kind": "none"}
    kind = raw.get("kind", "none")
    if not isinstance(kind, str):
        kind = "none"
    return {
        "kind": kind.strip().lower(),
        "amount": _number(raw.get("amount", 0.0)),
        "text": str(raw.get("text", ""))[:80],
    }


def _category_for(slot: str, raw: dict) -> str:
    declared = raw.get("category")
    if isinstance(declared, str) and declared in {
            "equipment", "consumable", "material"}:
        return declared
    if slot in EQUIPMENT_SLOTS:
        return "equipment"
    if slot == "consumable":
        return "consumable"
    if slot == "material":
        return "material"
    return ""


def _parse_item(item_id: str, raw) -> ItemDef | None:
    if not isinstance(item_id, str) or not item_id.strip():
        return None
    if not isinstance(raw, dict):
        return None
    item_id = item_id.strip()
    slot = str(raw.get("slot", "")).strip().lower()
    category = _category_for(slot, raw)
    if not category:
        return None
    rarity = str(raw.get("rarity", "common")).strip().lower()
    if rarity not in RARITIES:
        rarity = "common"
    name = str(raw.get("name", item_id.replace("_", " ").upper()))
    stackable = bool(raw.get("stackable", category != "equipment"))
    max_stack = 1
    if stackable:
        max_stack = _integer(raw.get("max_stack", 20), 20, 2, 999)
    return ItemDef(
        item_id=item_id,
        name=name[:64] or item_id.upper(),
        description=str(raw.get("description", ""))[:240],
        slot=slot,
        rarity=rarity,
        icon=str(raw.get("icon", "sword")).strip().lower() or "sword",
        value=_integer(raw.get("value", 20), 20, 0, 1_000_000),
        level_requirement=_integer(raw.get("level_requirement", 1), 1, 1, 99),
        stats=_coerce_stats(raw.get("stats")),
        effect=_coerce_effect(raw.get("effect")),
        category=category,
        stackable=stackable,
        max_stack=max_stack,
    )


_cache: dict[str, ItemDef] | None = None
_loot_cache: dict | None = None


def _read_json(path: Path):
    try:
        if not path.is_file():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else None
    except (OSError, ValueError, UnicodeError):
        return None


def _build_catalogue() -> dict[str, ItemDef]:
    result: dict[str, ItemDef] = {}
    for filename in ITEM_FILES:
        payload = _read_json(ITEM_DIR / filename)
        if not payload:
            continue
        for item_id, raw in payload.items():
            item = _parse_item(str(item_id), raw)
            if item is not None:
                result[item.item_id] = item
    return result


def items() -> dict[str, ItemDef]:
    """Return the validated catalogue (loaded once per process)."""
    global _cache
    if _cache is None:
        _cache = _build_catalogue()
    return _cache


def get_item(item_id) -> ItemDef | None:
    if not isinstance(item_id, str):
        return None
    return items().get(item_id.strip())


def item_exists(item_id) -> bool:
    return get_item(item_id) is not None


def items_for_slot(slot: str) -> list[ItemDef]:
    return [item for item in items().values()
            if item.is_equipment and item.slot == slot]


def rarity_color(rarity: str) -> tuple[int, int, int]:
    return RARITY_COLORS.get(str(rarity).lower(), RARITY_COLORS["common"])


def loot_table() -> dict:
    """Return a defensive copy of the drop configuration."""
    global _loot_cache
    if _loot_cache is None:
        payload = _read_json(ITEM_DIR / LOOT_FILE)
        _loot_cache = deepcopy(payload) if isinstance(payload, dict) else {}
        for key, value in DEFAULT_LOOT_TABLE.items():
            _loot_cache.setdefault(key, deepcopy(value))
    return deepcopy(_loot_cache)


def reload() -> None:
    """Drop caches (used by tools that rewrite item data at runtime)."""
    global _cache, _loot_cache
    _cache = None
    _loot_cache = None


__all__ = [
    "EQUIPMENT_SLOTS", "ITEM_DIR", "RARITIES", "RARITY_COLORS", "RARITY_DARK",
    "RARITY_LABELS", "RARITY_ORDER", "SLOT_LABELS", "STAT_KEYS",
    "STAT_LABELS", "STAT_IS_PERCENT", "ItemDef", "get_item", "item_exists",
    "items", "items_for_slot", "loot_table", "rarity_color", "reload",
]
