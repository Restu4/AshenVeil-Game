"""Seven-slot equipment with a single-authority stat recompute.

Equipped items are stored as validated item IDs.  Every mutation ends in
``recompute()``, which rebuilds the whole stat snapshot from base values.  That
is what makes equip/unequip idempotent: a bonus can never be applied twice, and
removing one item can never leave a stale modifier behind.
"""
from __future__ import annotations

from copy import deepcopy

from scripts.item_database import (
    EQUIPMENT_SLOTS,
    STAT_KEYS,
    ItemDef,
    get_item,
)
from scripts.player_stats import PlayerStats, format_stat, stat_label


class EquipmentManager:
    SLOTS = EQUIPMENT_SLOTS

    def __init__(self, player, stats: PlayerStats, notify=None) -> None:
        self.player = player
        self.stats = stats
        self.notify = notify
        self.skills = None
        self.combat = None
        self.equipped: dict[str, str | None] = {
            slot: None for slot in self.SLOTS
        }

    # ------------------------------------------------------------------
    def attach(self, skills=None, combat=None, notify=None) -> None:
        """Late-bind the systems that must follow stat changes."""
        if skills is not None:
            self.skills = skills
        if combat is not None:
            self.combat = combat
        if notify is not None:
            self.notify = notify
        self.recompute()

    def _say(self, text: str) -> None:
        if callable(self.notify):
            self.notify(text)

    # ------------------------------------------------------------------
    def equipped_item(self, slot: str) -> ItemDef | None:
        item_id = self.equipped.get(slot)
        return get_item(item_id) if item_id else None

    def is_equipped(self, item_id) -> bool:
        if not isinstance(item_id, str):
            return False
        return item_id in [value for value in self.equipped.values() if value]

    def slots_for(self, item_id: str) -> list[str]:
        item = get_item(item_id)
        if item is None or not item.is_equipment:
            return []
        return [slot for slot, value in self.equipped.items() if value == item_id]

    def can_equip(self, item_id: str) -> tuple[bool, str]:
        item = get_item(item_id)
        if item is None:
            return False, "UNKNOWN ITEM"
        if not item.is_equipment:
            return False, "ITEM CANNOT BE EQUIPPED"
        if item.slot not in self.equipped:
            return False, "UNKNOWN EQUIPMENT SLOT"
        if item.level_requirement > self.player.level:
            return False, f"LEVEL {item.level_requirement} REQUIRED"
        return True, ""

    def equip(self, item_id: str) -> tuple[bool, str]:
        ok, reason = self.can_equip(item_id)
        if not ok:
            self._say(reason)
            return False, reason
        item = get_item(item_id)
        assert item is not None
        if self.equipped.get(item.slot) == item_id:
            message = f"{item.name} ALREADY EQUIPPED"
            self._say(message)
            return False, message
        self.equipped[item.slot] = item_id
        self.recompute()
        message = f"{item.name} EQUIPPED"
        self._say(message)
        return True, message

    def unequip(self, slot: str) -> tuple[str | None, str]:
        item_id = self.equipped.get(slot)
        if not item_id:
            message = "NOTHING TO UNEQUIP"
            self._say(message)
            return None, message
        item = get_item(item_id)
        self.equipped[slot] = None
        self.recompute()
        name = item.name if item is not None else str(item_id).upper()
        message = f"{name} UNEQUIPPED"
        self._say(message)
        return item_id, message

    def unequip_item(self, item_id: str) -> tuple[bool, str]:
        for slot in self.slots_for(item_id):
            self.unequip(slot)
            return True, f"{item_id.upper()} UNEQUIPPED"
        return False, "ITEM IS NOT EQUIPPED"

    # ------------------------------------------------------------------
    def recompute(self) -> None:
        """Rebuild every derived value from the untouched base statistics."""
        self.stats.level = self.player.level
        self.stats.reset()
        for slot in self.SLOTS:
            item = self.equipped_item(slot)
            if item is not None and item.is_equipment and item.slot == slot:
                self.stats.apply(item)
        self.stats.level = self.player.level
        self.stats.clamp()

        self.player.stats = self.stats
        self.player.apply_stats(self.stats)

        if self.combat is not None:
            self.combat.crit_chance = self.stats.crit_chance
            crit_multiplier = self.stats.crit_damage
            mods = getattr(self.skills, "mods", None) if self.skills else None
            if mods is not None:
                crit_multiplier *= mods.crit_damage
            self.combat.crit_multiplier = crit_multiplier
        if self.skills is not None:
            energy = getattr(self.skills, "energy", None)
            if energy is not None:
                energy.maximum = self.stats.max_void
                energy.clamp()

    def refresh_level(self) -> None:
        """Call when player level changes so requirements are re-evaluated."""
        self.recompute()

    # ------------------------------------------------------------------
    def comparison(self, item: ItemDef) -> list[tuple[str, float]]:
        """Deltas of ``item`` against what that slot currently provides."""
        if item is None or not item.is_equipment:
            return []
        current = self.equipped_item(item.slot)
        result: list[tuple[str, float]] = []
        for key in STAT_KEYS:
            delta = item.stats.get(key, 0.0) - (
                current.stats.get(key, 0.0) if current is not None else 0.0
            )
            if abs(delta) > 1e-9:
                result.append((key, delta))
        return result

    def comparison_lines(self, item: ItemDef) -> list[str]:
        lines: list[str] = []
        for key, delta in self.comparison(item):
            lines.append(f"{stat_label(key)} {format_stat(key, delta, signed=True)}")
        return lines

    def void_on_kill_amount(self) -> float:
        total = 0.0
        for slot in self.SLOTS:
            item = self.equipped_item(slot)
            if item is not None and item.effect_kind == "void_on_kill":
                total += max(0.0, item.effect_amount)
        return total

    # ------------------------------------------------------------------
    def to_dict(self) -> dict[str, str | None]:
        return deepcopy(self.equipped)

    def load(self, raw) -> int:
        """Validate a stored equipment map; invalid entries are dropped."""
        loaded = 0
        clean: dict[str, str | None] = {slot: None for slot in self.SLOTS}
        if isinstance(raw, dict):
            for slot in self.SLOTS:
                item_id = raw.get(slot)
                if not isinstance(item_id, str) or not item_id:
                    continue
                ok, _ = self.can_equip(item_id)
                if not ok:
                    continue
                item = get_item(item_id)
                if item is None or item.slot != slot:
                    continue
                clean[slot] = item_id
                loaded += 1
        self.equipped = clean
        self.recompute()
        return loaded

    def clear(self) -> None:
        self.equipped = {slot: None for slot in self.SLOTS}
        self.recompute()


__all__ = ["EquipmentManager"]
