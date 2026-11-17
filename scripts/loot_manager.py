"""World loot: configurable tables, one-shot death rolls and G pickup.

Drops are plain world objects owned by ``Game`` but drawn inside the camera.
A death is rolled exactly once (guarded by enemy ID), drops are capped, and
pickup is refused when a wall lies between the player and the drop.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

import pygame

from scripts.item_database import get_item, loot_table
from scripts.ui.item_icons import icon, scaled_icon
from scripts.pixel_font import draw_text


@dataclass
class WorldDrop:
    x: float
    y: float
    item_id: str | None = None
    quantity: int = 1
    gold: int = 0
    age: float = 0.0
    phase: float = 0.0

    @property
    def label(self) -> str:
        if self.gold and not self.item_id:
            return f"{self.gold} GOLD"
        item = get_item(self.item_id) if self.item_id else None
        name = item.name if item is not None else str(self.item_id or "LOOT")
        if self.quantity > 1:
            return f"{name} X{self.quantity}"
        return name


class LootManager:
    def __init__(self, world, notify=None, rng: random.Random | None = None,
                 table: dict | None = None) -> None:
        self.world = world
        self.notify = notify
        self.rng = rng or random.Random(0xA5E_1007)
        self.table = table if table is not None else loot_table()
        settings = self.table.get("settings", {})
        self.max_drops = self._int(settings.get("max_drops", 24), 24, 4, 80)
        self.pickup_radius = max(
            20.0, self._float(settings.get("pickup_radius", 52.0), 52.0)
        )
        self.lifetime = max(
            0.0, self._float(settings.get("world_lifetime", 0.0), 0.0)
        )
        self.drops: list[WorldDrop] = []
        self._rolled: set[tuple[str, int]] = set()
        self.time = 0.0

    # ------------------------------------------------------------------
    @staticmethod
    def _int(value, fallback: int, low: int, high: int) -> int:
        try:
            return max(low, min(high, int(float(value))))
        except (TypeError, ValueError):
            return fallback

    @staticmethod
    def _float(value, fallback: float) -> float:
        try:
            result = float(value)
            return result if result == result else fallback
        except (TypeError, ValueError):
            return fallback

    def attach(self, notify=None) -> None:
        if notify is not None:
            self.notify = notify

    def _say(self, text: str) -> None:
        if callable(self.notify):
            self.notify(text)

    # ------------------------------------------------------------------
    def tier_for(self, enemy) -> str:
        if getattr(enemy, "is_boss", False):
            return "boss"
        key = str(getattr(enemy, "key", "")).lower()
        subtitle = str(getattr(enemy, "subtitle", "")).upper()
        if key == "corrupted_warden" or "ELITE" in subtitle:
            return "elite"
        return "regular"

    def on_enemy_killed(self, enemy) -> list[WorldDrop]:
        """Roll once per death and place the resulting drops in the world."""
        if enemy is None:
            return []
        tier = self.tier_for(enemy)
        enemy_id = int(getattr(enemy, "id", -1))
        marker = (tier, enemy_id)
        if marker in self._rolled:
            return []
        self._rolled.add(marker)

        config = self.table.get(tier, {})
        if not isinstance(config, dict):
            return []
        x = float(getattr(enemy, "x", 0.0))
        y = float(getattr(enemy, "y", 0.0))
        self._say("THE FOE FALLS")
        if tier == "boss":
            self._say("GUARDIAN REWARD REVEALED")

        made: list[WorldDrop] = []
        gold = config.get("gold")
        if isinstance(gold, dict) and self.rng.random() < self._float(
                gold.get("chance", 0.0), 0.0):
            amount = self.rng.randint(
                self._int(gold.get("min", 1), 1, 0, 100000),
                self._int(gold.get("max", 10), 10, 0, 100000),
            )
            if amount > 0:
                made.append(self.spawn(x, y, gold=amount))

        for record in config.get("guaranteed_items", []) or []:
            if not isinstance(record, dict):
                continue
            item_id = record.get("id")
            if get_item(item_id) is None:
                continue
            quantity = self._int(record.get("quantity", 1), 1, 1, 99)
            made.append(self.spawn(x, y, item_id=item_id, quantity=quantity))

        for category in ("equipment", "consumable", "material"):
            group = config.get(category)
            if not isinstance(group, dict):
                continue
            if self.rng.random() >= self._float(group.get("chance", 0.0), 0.0):
                continue
            pool = [value for value in group.get("pool", []) or []
                    if isinstance(value, str) and get_item(value) is not None]
            if not pool:
                continue
            item_id = self.rng.choice(pool)
            low = self._int(group.get("min_quantity", 1), 1, 1, 99)
            high = self._int(group.get("max_quantity", low), low, low, 99)
            made.append(self.spawn(x, y, item_id=item_id,
                                   quantity=self.rng.randint(low, high)))
        return made

    def spawn(self, x: float, y: float, item_id: str | None = None,
              quantity: int = 1, gold: int = 0) -> WorldDrop:
        """Create a drop at a walkable point near the given world position."""
        if len(self.drops) >= self.max_drops:
            self.drops.pop(0)
        px, py = x, y
        for dx, dy in ((0, 0), (18, 0), (-18, 0), (0, 18), (0, -18),
                       (28, 14), (-28, -14)):
            probe = pygame.Rect(int(px + dx) - 8, int(py + dy) - 8, 16, 16)
            if self.world.collision.rect_free(probe):
                px, py = x + dx, y + dy
                break
        drop = WorldDrop(px, py, item_id=item_id,
                         quantity=max(1, int(quantity)) if item_id else 1,
                         gold=max(0, int(gold)),
                         phase=self.rng.random() * math.tau)
        self.drops.append(drop)
        return drop

    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        self.time += max(0.0, dt)
        for drop in self.drops:
            drop.age += max(0.0, dt)
        if self.lifetime > 0.0:
            self.drops[:] = [drop for drop in self.drops
                             if drop.age < self.lifetime]

    def nearest(self, player) -> WorldDrop | None:
        if not self.drops:
            return None
        best = None
        best_distance = self.pickup_radius
        collision = self.world.collision
        for drop in self.drops:
            distance = math.hypot(player.x - drop.x, player.y - drop.y)
            if distance > best_distance:
                continue
            if collision.segment_blocked(player.x, player.y - 10.0,
                                         drop.x, drop.y - 10.0, 3.0):
                continue
            best = drop
            best_distance = distance
        return best

    def try_pickup(self, player, inventory) -> bool:
        """Collect the nearest reachable drop, or report why it cannot fit."""
        drop = self.nearest(player)
        if drop is None:
            return False
        if drop.gold:
            gained = inventory.add_gold(drop.gold)
            if gained > 0:
                self._say(f"PICKED UP {gained} GOLD")
            drop.gold = 0

        if drop.item_id:
            added = inventory.add(drop.item_id, drop.quantity)
            if added <= 0:
                self._say("INVENTORY FULL")
                return False
            if added < drop.quantity:
                drop.quantity -= added
                self._say("INVENTORY FULL")
                return True
            drop.item_id = None

        if not drop.item_id and drop.gold <= 0:
            self.drops.remove(drop)
        return True

    # ------------------------------------------------------------------
    def clear(self) -> None:
        self.drops.clear()
        self._rolled.clear()

    # ------------------------------------------------------------------
    def draw(self, target: pygame.Surface, camera) -> None:
        visible = camera.visible_rect(margin=80)
        for drop in self.drops:
            sx, sy = camera.to_screen(drop.x, drop.y)
            if not visible.collidepoint(drop.x, drop.y):
                continue
            bob = int(round(math.sin(self.time * 3.2 + drop.phase) * 3.0))
            base_y = sy - 12 + bob
            color = (232, 196, 104) if drop.gold else (
                get_item(drop.item_id).rarity_color
                if get_item(drop.item_id) else (190, 180, 210)
            )
            glow = pygame.Surface((40, 40), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*color, 26), (20, 20), 18)
            pygame.draw.circle(glow, (*color, 44), (20, 20), 12)
            target.blit(glow, (sx - 20, base_y - 20))
            pygame.draw.ellipse(target, (12, 9, 16),
                                (sx - 12, sy + 2, 24, 7))
            if drop.gold:
                target.blit(scaled_icon("gold", 1), (sx - 12, base_y - 12))
            elif drop.item_id:
                item = get_item(drop.item_id)
                name = item.icon if item is not None else "sword"
                target.blit(scaled_icon(name, 1), (sx - 12, base_y - 12))
                pygame.draw.rect(target, color,
                                 (sx - 13, base_y - 13, 26, 26), 1)

    def draw_prompt(self, target: pygame.Surface, player, camera) -> None:
        drop = self.nearest(player)
        if drop is None:
            return
        sx, sy = camera.to_screen(drop.x, drop.y)
        draw_text(target, "G PICKUP", sx, sy - 48, 1, (226, 210, 244),
                  spacing=1, center=True, shadow=(8, 6, 12))


__all__ = ["LootManager", "WorldDrop"]
