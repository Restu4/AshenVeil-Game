"""Merchant trade: validated buys, limited stock and eligible sales."""
from __future__ import annotations

import math
from dataclasses import dataclass

from scripts.item_database import get_item
from scripts.village_data import MAX_SAVE_ENTRIES, shop_stock


@dataclass(frozen=True)
class StockEntry:
    item_id: str
    category: str
    price: int
    stock: int  # -1 means unlimited

    @property
    def limited(self) -> bool:
        return self.stock >= 0


class ShopManager:
    """Uses the real InventoryManager; it never mutates a parallel satchel."""

    def __init__(self, inventory, notify=None, is_equipped=None,
                 upgrades=None, on_change=None) -> None:
        self.inventory = inventory
        self.notify = notify
        self.is_equipped = is_equipped
        self.upgrades = upgrades
        self.on_change = on_change
        raw = shop_stock()
        settings = raw.get("settings", {}) if isinstance(raw.get("settings"), dict) else {}
        self.sell_rate = max(0.0, min(1.0, float(settings.get("sell_rate", 0.5))))
        self.max_quantity = max(1, min(20, int(settings.get("max_quantity", 10))))
        categories = raw.get("categories")
        self.categories = [
            (str(entry.get("id", "")), str(entry.get("label", "")))
            for entry in categories
            if isinstance(entry, dict) and entry.get("id")
        ] if isinstance(categories, list) else []
        self.entries: list[StockEntry] = []
        records = raw.get("items")
        if isinstance(records, list):
            for record in records:
                if not isinstance(record, dict):
                    continue
                item_id = str(record.get("item_id", ""))
                if get_item(item_id) is None:
                    continue
                try:
                    price = max(1, int(record.get("price", 0)))
                except (TypeError, ValueError):
                    continue
                try:
                    stock = int(record.get("stock", -1))
                except (TypeError, ValueError):
                    stock = -1
                self.entries.append(StockEntry(
                    item_id, str(record.get("category", "consumables")),
                    price, -1 if stock < 0 else max(0, stock),
                ))
        self.purchases: dict[str, int] = {}
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
        self.purchases = {}
        if not isinstance(raw, dict):
            return
        records = raw.get("purchases")
        if not isinstance(records, dict):
            return
        for item_id, count in records.items():
            if get_item(item_id) is None or len(self.purchases) >= MAX_SAVE_ENTRIES:
                continue
            try:
                amount = max(0, min(9999, int(count)))
            except (TypeError, ValueError):
                continue
            if amount:
                self.purchases[str(item_id)] = amount

    def to_state(self) -> dict:
        return {"purchases": dict(self.purchases)}

    def entry(self, item_id: str) -> StockEntry | None:
        return next((entry for entry in self.entries
                     if entry.item_id == item_id), None)

    def entries_for(self, category: str) -> list[StockEntry]:
        return [entry for entry in self.entries if entry.category == category]

    def bought(self, item_id: str) -> int:
        return int(self.purchases.get(item_id, 0))

    def remaining(self, item_id: str) -> int:
        entry = self.entry(item_id)
        if entry is None:
            return 0
        if not entry.limited:
            return self.max_quantity
        return max(0, entry.stock - self.bought(item_id))

    # ------------------------------------------------------------------
    def _can_hold(self, item_id: str, quantity: int) -> bool:
        item = get_item(item_id)
        if item is None or quantity <= 0:
            return False
        if not item.stackable:
            return self.inventory.free >= quantity
        needed = quantity
        for entry in self.inventory.entries:
            if entry.item_id != item_id:
                continue
            needed -= max(0, item.max_stack - entry.quantity)
        if needed <= 0:
            return True
        free = self.inventory.free
        stacks = math.ceil(needed / max(1, item.max_stack))
        return free >= stacks

    def buy_price(self, item_id: str) -> int:
        entry = self.entry(item_id)
        return entry.price if entry is not None else 0

    def buy(self, item_id: str, quantity: int = 1) -> bool:
        entry = self.entry(item_id)
        quantity = max(0, int(quantity))
        if entry is None or quantity < 1:
            self._say("INVALID PURCHASE")
            return False
        item = get_item(item_id)
        if item is None:
            self._say("UNKNOWN ITEM")
            return False
        if quantity > self.max_quantity:
            self._say("LIMIT REACHED")
            return False
        if entry.limited and quantity > self.remaining(item_id):
            self._say("SOLD OUT")
            return False
        player = getattr(self.inventory, "player", None)
        level = int(getattr(player, "level", 1) or 1)
        if item.level_requirement > level:
            self._say(f"LEVEL {item.level_requirement} REQUIRED")
            return False
        total = entry.price * quantity
        if total <= 0 or self.inventory.gold < total:
            self._say("NOT ENOUGH GOLD")
            return False
        if not self._can_hold(item_id, quantity):
            self._say("INVENTORY FULL")
            return False

        # Every validation passed: spend first, then add.  The fallback refund
        # guards against a future inventory rule changing underneath us.
        before = self.inventory.gold
        if not self.inventory.spend_gold(total):
            self._say("NOT ENOUGH GOLD")
            return False
        added = self.inventory.add(item_id, quantity)
        if added < quantity:
            self.inventory.gold = before - entry.price * added
            self._say("INVENTORY FULL")
            return False
        if entry.limited:
            self.purchases[item_id] = self.bought(item_id) + added
        self._say(f"BOUGHT {item.name}" + (f" X{added}" if added > 1 else ""))
        self._changed()
        return True

    # ------------------------------------------------------------------
    def sell_price(self, item_id: str, quantity: int = 1) -> int:
        item = get_item(item_id)
        if item is None:
            return 0
        unit = max(1, math.floor(int(item.value) * self.sell_rate))
        if self.upgrades is not None:
            unit += self.upgrades.resale_bonus(item_id)
        return unit * max(1, int(quantity))

    def can_sell(self, item_id: str) -> bool:
        item = get_item(item_id)
        if item is None or item.value <= 0:
            return False
        if callable(self.is_equipped) and self.is_equipped(item_id):
            return False
        return True

    def sell(self, index: int, quantity: int = 1) -> bool:
        entry = self.inventory.entry_at(index)
        if entry is None:
            self._say("NOTHING TO SELL")
            return False
        if not self.can_sell(entry.item_id):
            self._say("EQUIPPED ITEMS CANNOT BE SOLD")
            return False
        quantity = max(1, min(int(quantity), int(entry.quantity)))
        item = get_item(entry.item_id)
        assert item is not None
        total = self.sell_price(entry.item_id, quantity)
        if total <= 0:
            self._say("ITEM HAS NO VALUE")
            return False
        removed = self.inventory.remove(entry.item_id, quantity)
        if removed <= 0:
            self._say("NOTHING TO SELL")
            return False
        self.inventory.add_gold(total)
        if self.upgrades is not None and self.inventory.count(entry.item_id) <= 0:
            self.upgrades.clear(entry.item_id)
        self._say(f"SOLD {item.name}" + (f" X{removed}" if removed > 1 else ""))
        self._changed()
        return True


__all__ = ["ShopManager", "StockEntry"]
