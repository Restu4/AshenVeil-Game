"""Capacity-limited inventory, stacks, gold and consumable use.

Items are stored as ``(item_id, quantity)`` pairs.  Stackable items merge into
one slot; unique equipment occupies one slot per item ID.  The inventory never
silently destroys anything: ``add`` reports how much actually fit and leaves a
human-readable message for the pickup notification.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from scripts.item_database import ItemDef, get_item

DEFAULT_CAPACITY = 28


@dataclass
class InventoryEntry:
    item_id: str
    quantity: int = 1

    @property
    def item(self) -> ItemDef | None:
        return get_item(self.item_id)


class InventoryManager:
    def __init__(self, capacity: int = DEFAULT_CAPACITY) -> None:
        self.capacity = max(12, min(28, int(capacity)))
        self.entries: list[InventoryEntry] = []
        self.gold = 0
        self.message = ""
        self.player = None
        self.skills = None
        self.notify: Callable[[str], None] | None = None
        self.on_change: Callable[[], None] | None = None

    # ------------------------------------------------------------------
    def attach(self, player=None, skills=None, notify=None,
               on_change=None) -> None:
        if player is not None:
            self.player = player
        if skills is not None:
            self.skills = skills
        if notify is not None:
            self.notify = notify
        if on_change is not None:
            self.on_change = on_change

    def _say(self, text: str) -> None:
        self.message = text
        if callable(self.notify):
            self.notify(text)

    def _changed(self) -> None:
        if callable(self.on_change):
            self.on_change()

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    @property
    def used(self) -> int:
        return len(self.entries)

    @property
    def free(self) -> int:
        return max(0, self.capacity - self.used)

    @property
    def is_full(self) -> bool:
        return self.used >= self.capacity

    def count(self, item_id: str) -> int:
        return sum(entry.quantity for entry in self.entries
                   if entry.item_id == item_id)

    def has(self, item_id: str) -> bool:
        return self.count(item_id) > 0

    def entry_at(self, index: int) -> InventoryEntry | None:
        if 0 <= index < len(self.entries):
            return self.entries[index]
        return None

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------
    def add(self, item_id: str, quantity: int = 1) -> int:
        """Add as many as possible and return the number actually stored."""
        item = get_item(item_id)
        amount = max(0, int(quantity))
        if item is None or amount == 0:
            self._say("UNKNOWN ITEM")
            return 0

        added = 0
        if item.stackable:
            # One stack per item ID, clamped to the definition's max_stack.
            # Any remainder is reported as a full inventory rather than
            # silently creating duplicate stacks.
            for entry in self.entries:
                if entry.item_id != item_id:
                    continue
                room = max(0, item.max_stack - entry.quantity)
                take = min(room, amount)
                if take:
                    entry.quantity += take
                    amount -= take
                    added += take
                break
            if amount > 0 and len(self.entries) < self.capacity:
                take = min(item.max_stack, amount)
                self.entries.append(InventoryEntry(item_id, take))
                amount -= take
                added += take
        else:
            while amount > 0 and len(self.entries) < self.capacity:
                self.entries.append(InventoryEntry(item_id, 1))
                amount -= 1
                added += 1

        if added > 0:
            label = item.name if added == 1 else f"{item.name} X{added}"
            self._say(f"FOUND {label}")
            self._changed()
        if amount > 0:
            self._say("INVENTORY FULL")
        return added

    def remove(self, item_id: str, quantity: int = 1) -> int:
        """Remove up to ``quantity``; returns the number really removed."""
        amount = max(0, int(quantity))
        removed = 0
        for index in range(len(self.entries) - 1, -1, -1):
            entry = self.entries[index]
            if entry.item_id != item_id or removed >= amount:
                continue
            take = min(entry.quantity, amount - removed)
            entry.quantity -= take
            removed += take
            if entry.quantity <= 0:
                self.entries.pop(index)
        if removed:
            self._changed()
        return removed

    def add_gold(self, amount: int) -> int:
        gained = max(0, int(amount))
        self.gold = min(9_999_999, self.gold + gained)
        if gained:
            self._say(f"FOUND {gained} GOLD")
            self._changed()
        return gained

    def spend_gold(self, amount: int) -> bool:
        cost = max(0, int(amount))
        if cost > self.gold:
            return False
        self.gold -= cost
        self._changed()
        return True

    def drop(self, index: int) -> str | None:
        """Remove one whole stack from the grid (used by the Drop button)."""
        entry = self.entry_at(index)
        if entry is None:
            return None
        self.entries.pop(index)
        self._say(f"DROPPED {entry.item_id.upper()}")
        self._changed()
        return entry.item_id

    # ------------------------------------------------------------------
    def use(self, item_id: str) -> bool:
        """Consume one potion and apply its effect to the real resources."""
        item = get_item(item_id)
        if item is None or not item.is_consumable:
            self._say("ITEM CANNOT BE USED")
            return False
        if self.count(item_id) <= 0:
            self._say("NONE LEFT")
            return False

        kind = item.effect_kind
        amount = item.effect_amount
        if kind == "heal":
            if self.player is None:
                return False
            if self.player.health >= self.player.health_max - 0.01:
                self._say("HP ALREADY FULL")
                return False
            before = self.player.health
            self.player.health = before + amount
            gained = self.player.health - before
            message = f"RESTORED {int(round(gained))} HP"
        elif kind == "void":
            energy = getattr(self.skills, "energy", None)
            if energy is None:
                return False
            if energy.full:
                self._say("VOID ALREADY FULL")
                return False
            gained = energy.gain(amount)
            if gained <= 0.0:
                return False
            message = f"RESTORED {int(round(gained))} VOID"
        else:
            self._say("NOTHING HAPPENS")
            return False

        self.remove(item_id, 1)
        self._say(message)
        return True

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "gold": int(self.gold),
            "capacity": int(self.capacity),
            "items": [
                {"id": entry.item_id, "qty": int(entry.quantity)}
                for entry in self.entries
            ],
        }

    def load(self, raw) -> None:
        """Validate a stored inventory, deduplicating and clamping stacks."""
        self.entries = []
        self.gold = 0
        if not isinstance(raw, dict):
            self.message = ""
            return
        self.capacity = max(12, min(28, int(raw.get("capacity", self.capacity))))

        gold = raw.get("gold", 0)
        try:
            self.gold = max(0, min(9_999_999, int(float(gold))))
        except (TypeError, ValueError):
            self.gold = 0

        seen: set[str] = set()
        items = raw.get("items")
        if not isinstance(items, list):
            self.message = ""
            return
        for record in items:
            if not isinstance(record, dict):
                continue
            item_id = record.get("id")
            item = get_item(item_id)
            if item is None:
                continue
            try:
                quantity = max(1, int(float(record.get("qty", 1))))
            except (TypeError, ValueError):
                quantity = 1
            if not item.stackable:
                if item_id in seen:
                    continue
                quantity = 1
            else:
                # Merge repeated records for the same stackable ID instead of
                # creating duplicate slots after a load.
                for entry in self.entries:
                    if entry.item_id != item_id:
                        continue
                    room = max(0, item.max_stack - entry.quantity)
                    take = min(room, quantity)
                    entry.quantity += take
                    quantity -= take
                    break
                if quantity <= 0:
                    continue
                quantity = min(quantity, item.max_stack)
            if len(self.entries) >= self.capacity:
                break
            self.entries.append(InventoryEntry(item.item_id, quantity))
            seen.add(item_id)
        self.message = ""
        self._changed()


__all__ = ["DEFAULT_CAPACITY", "InventoryEntry", "InventoryManager"]
