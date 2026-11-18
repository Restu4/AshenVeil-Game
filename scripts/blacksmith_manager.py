"""Blacksmith forging: bounded, material-costed equipment upgrades.

Upgrade levels are keyed by the real item ID.  Because the Phase 6 inventory
already treats equipment as unique, one level map is enough to preserve each
item's identity, rarity and invested gold without spawning duplicate items.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Callable

from scripts.item_database import ItemDef, STAT_KEYS, get_item
from scripts.village_data import MAX_SAVE_ENTRIES, MAX_UPGRADE_LEVEL, upgrade_config


class BlacksmithManager:
    def __init__(self, inventory, notify: Callable[[str], None] | None = None,
                 on_change: Callable[[], None] | None = None) -> None:
        self.inventory = inventory
        self.notify = notify
        self.on_change = on_change
        raw = upgrade_config()
        self.max_level = max(0, min(MAX_UPGRADE_LEVEL,
                                    int(raw.get("max_level", MAX_UPGRADE_LEVEL))))
        self.allowed_slots = tuple(
            str(slot) for slot in raw.get(
                "allowed_slots", ("weapon", "helmet", "armor", "gloves", "boots")
            )
        )
        self.stat_steps = raw.get("stat_steps", {}) if isinstance(
            raw.get("stat_steps"), dict) else {}
        self.costs: dict[int, dict] = {}
        records = raw.get("levels")
        if isinstance(records, list):
            for record in records:
                if not isinstance(record, dict):
                    continue
                try:
                    level = max(1, min(self.max_level, int(record.get("level", 0))))
                except (TypeError, ValueError):
                    continue
                materials = record.get("materials")
                clean_materials = {}
                if isinstance(materials, dict):
                    for material_id, quantity in materials.items():
                        if get_item(material_id) is None:
                            continue
                        try:
                            count = max(0, int(quantity))
                        except (TypeError, ValueError):
                            continue
                        if count:
                            clean_materials[str(material_id)] = count
                try:
                    gold = max(0, int(record.get("gold", 0)))
                except (TypeError, ValueError):
                    gold = 0
                self.costs[level] = {"gold": gold, "materials": clean_materials}
        self.levels: dict[str, int] = {}
        self.last_message = ""

    # ------------------------------------------------------------------
    def _say(self, text: str) -> None:
        self.last_message = str(text)
        if callable(self.notify):
            self.notify(text)

    def _changed(self) -> None:
        if callable(self.on_change):
            self.on_change()

    def load_state(self, raw) -> None:
        self.levels = {}
        if not isinstance(raw, dict):
            return
        records = raw.get("levels")
        if not isinstance(records, dict):
            return
        for item_id, value in records.items():
            item = get_item(item_id)
            if not self.eligible_item(item) or len(self.levels) >= MAX_SAVE_ENTRIES:
                continue
            try:
                level = max(0, min(self.max_level, int(value)))
            except (TypeError, ValueError):
                continue
            if level:
                self.levels[str(item_id)] = level

    def to_state(self) -> dict:
        return {"levels": dict(self.levels)}

    # ------------------------------------------------------------------
    def eligible_item(self, item: ItemDef | None) -> bool:
        return (item is not None and item.is_equipment
                and item.slot in self.allowed_slots)

    def eligible(self, item_id: str) -> bool:
        return self.eligible_item(get_item(item_id))

    def level(self, item_id: str) -> int:
        try:
            return max(0, min(self.max_level, int(self.levels.get(item_id, 0))))
        except (TypeError, ValueError):
            return 0

    def is_max(self, item_id: str) -> bool:
        return self.level(item_id) >= self.max_level

    def invested_gold(self, item_id: str) -> int:
        level = self.level(item_id)
        return sum(self.costs.get(step, {}).get("gold", 0)
                   for step in range(1, level + 1))

    def resale_bonus(self, item_id: str) -> int:
        return self.invested_gold(item_id) // 2

    def next_cost(self, item_id: str) -> dict:
        level = self.level(item_id) + 1
        if level > self.max_level:
            return {"gold": 0, "materials": {}}
        cost = self.costs.get(level, {"gold": 0, "materials": {}})
        return {
            "gold": max(0, int(cost.get("gold", 0))),
            "materials": dict(cost.get("materials", {})),
        }

    # ------------------------------------------------------------------
    def _derive(self, item: ItemDef | None, level: int) -> ItemDef | None:
        """Build the ItemDef for a given forge level from the base catalog."""
        if item is None or level <= 0:
            return item
        step = self.stat_steps.get(item.slot, {})
        if not isinstance(step, dict):
            step = {}
        stats = dict(item.stats)
        for key, amount in step.items():
            if key not in STAT_KEYS:
                continue
            try:
                value = float(amount)
            except (TypeError, ValueError):
                continue
            stats[key] = stats.get(key, 0.0) + value * level
        invested = sum(self.costs.get(step_no, {}).get("gold", 0)
                       for step_no in range(1, min(level, self.max_level) + 1))
        return replace(
            item,
            name=f"{item.name} +{level}",
            stats=stats,
            value=int(item.value) + invested,
        )

    def effective_item(self, item: ItemDef | None) -> ItemDef | None:
        """Return a derived ItemDef whose stats include all forge levels."""
        if item is None:
            return None
        return self._derive(item, self.level(item.item_id))

    def preview_item(self, item: ItemDef | None) -> ItemDef | None:
        """The item as it would be after the next successful upgrade."""
        if item is None:
            return None
        return self._derive(item, min(self.max_level, self.level(item.item_id) + 1))

    def effective_item_id(self, item_id: str) -> ItemDef | None:
        return self.effective_item(get_item(item_id))

    def clear(self, item_id: str) -> None:
        """Forget forge data when the last copy of an item leaves the satchel."""
        if item_id in self.levels:
            self.levels.pop(item_id, None)
            self._changed()

    def can_upgrade(self, item_id: str) -> tuple[bool, str]:
        item = get_item(item_id)
        if not self.eligible_item(item):
            return False, "ITEM CANNOT BE FORGED"
        if self.inventory.count(item_id) <= 0:
            return False, "ITEM NOT IN SATCHEL"
        if self.is_max(item_id):
            return False, "ALREADY AT +5"
        cost = self.next_cost(item_id)
        if self.inventory.gold < cost["gold"]:
            return False, "NOT ENOUGH GOLD"
        for material_id, quantity in cost["materials"].items():
            if self.inventory.count(material_id) < quantity:
                return False, "MISSING CRAFTING MATERIALS"
        return True, ""

    def upgrade(self, item_id: str) -> bool:
        ok, reason = self.can_upgrade(item_id)
        if not ok:
            self._say(reason)
            return False
        item = get_item(item_id)
        assert item is not None
        cost = self.next_cost(item_id)
        self.inventory.spend_gold(cost["gold"])
        for material_id, quantity in cost["materials"].items():
            self.inventory.remove(material_id, quantity)
        level = self.level(item_id) + 1
        self.levels[item_id] = level
        self._changed()
        self._say(f"{item.name} FORGED TO +{level}")
        return True


__all__ = ["BlacksmithManager"]
