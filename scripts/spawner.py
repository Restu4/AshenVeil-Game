"""Finite, validated enemy spawning.

The old build placed seven knights at fixed coordinates and never changed.  The
spawner instead starts with a small readable group and then trickles in a
capped number of reinforcements:

* every candidate point is rejected if it overlaps a solid, the player or
  another enemy;
* the active cap keeps the pack small enough to read;
* the total cap guarantees the village eventually runs dry - no infinite spawn.

All numbers come from ``scripts.enemy_config`` and ``village_layout``.
"""
from __future__ import annotations

import math
import random

import pygame

from scripts.enemy import Enemy
from scripts.enemy_config import (
    ENEMY_INITIAL_MIN_PLAYER_DISTANCE,
    ENEMY_MAX_ACTIVE,
    ENEMY_RESPAWN_ORDER,
    ENEMY_SPAWN_COOLDOWN,
    ENEMY_SPAWN_COOLDOWN_JITTER,
    ENEMY_SPAWN_INTERVAL,
    ENEMY_SPAWN_JITTER,
    ENEMY_SPAWN_MIN_ENEMY_DISTANCE,
    ENEMY_SPAWN_MIN_PLAYER_DISTANCE,
    ENEMY_SPAWN_TOTAL_CAP,
    ENEMY_START_GROUP,
    get_archetype,
)
from scripts.village_layout import ENEMY_SPAWN_POINTS
from settings import WORLD_H, WORLD_W

WORLD_MARGIN = 90.0


class Spawner:
    def __init__(self, assets, world, player, combat) -> None:
        self.assets = assets
        self.world = world
        self.player = player
        self.combat = combat
        self.rng = random.Random(0x5EA5)
        self.total_spawned = 0
        self.timer = ENEMY_SPAWN_INTERVAL
        self._respawn_index = 0
        self._next_id = 1
        self.spawn_log: list[tuple[str, float, float]] = []
        self.rejected_points = 0

    # ------------------------------------------------------------------
    def reset(self) -> None:
        self.combat.enemies.clear()
        self.total_spawned = 0
        self.timer = ENEMY_SPAWN_INTERVAL
        self._respawn_index = 0
        self._next_id = 1
        self.spawn_log.clear()
        self.rejected_points = 0
        for key in ENEMY_START_GROUP:
            self.spawn(key, initial=True)

    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        if dt <= 0.0:
            return
        if self.total_spawned >= ENEMY_SPAWN_TOTAL_CAP:
            return
        alive = sum(1 for enemy in self.combat.enemies if enemy.alive)
        if alive >= ENEMY_MAX_ACTIVE:
            return
        self.timer -= dt
        if self.timer > 0.0:
            return
        key = ENEMY_RESPAWN_ORDER[self._respawn_index % len(ENEMY_RESPAWN_ORDER)]
        spawned = self.spawn(key, initial=False)
        if spawned is not None:
            self._respawn_index += 1
        # Retry sooner when the world is too crowded to place a body.
        self.timer = ENEMY_SPAWN_INTERVAL * (0.85 if spawned is None else 1.0)

    # ------------------------------------------------------------------
    def spawn(self, key: str, initial: bool = False) -> Enemy | None:
        if self.total_spawned >= ENEMY_SPAWN_TOTAL_CAP:
            return None
        archetype = get_archetype(key)
        min_player = (ENEMY_INITIAL_MIN_PLAYER_DISTANCE if initial
                      else ENEMY_SPAWN_MIN_PLAYER_DISTANCE)
        position = self._choose_position(archetype, min_player)
        if position is None:
            return None
        x, y, facing = position
        enemy = Enemy(self.assets, self._next_id, archetype, x, y, facing)
        self._next_id += 1
        # Stagger permission windows so a fresh group never winds up in unison.
        enemy.attack_cooldown = (ENEMY_SPAWN_COOLDOWN
                                 + ENEMY_SPAWN_COOLDOWN_JITTER * (self._next_id % 4))
        self.combat.enemies.append(enemy)
        self.total_spawned += 1
        self.spawn_log.append((key, x, y))
        return enemy

    # ------------------------------------------------------------------
    def _choose_position(self, archetype, min_player_distance: float):
        candidates = []
        for order, (px, py, facing) in enumerate(ENEMY_SPAWN_POINTS):
            jitter_x = self.rng.uniform(-ENEMY_SPAWN_JITTER, ENEMY_SPAWN_JITTER)
            jitter_y = self.rng.uniform(-ENEMY_SPAWN_JITTER, ENEMY_SPAWN_JITTER)
            x, y = px + jitter_x, py + jitter_y
            distance = math.hypot(x - self.player.x, y - self.player.y)
            candidates.append((distance, order, x, y, facing))
        candidates.sort(key=lambda item: item[0])

        for distance, _order, x, y, facing in candidates:
            if distance < min_player_distance:
                continue
            if self._position_valid(x, y, archetype):
                return x, y, facing
            self.rejected_points += 1
        return None

    def _position_valid(self, x: float, y: float, archetype) -> bool:
        if not (WORLD_MARGIN <= x <= WORLD_W - WORLD_MARGIN
                and WORLD_MARGIN <= y <= WORLD_H - WORLD_MARGIN):
            return False
        half_w = archetype.half_w + 3.0
        half_h = archetype.half_h + 3.0
        box = pygame.Rect(
            int(round(x - half_w)), int(round(y - half_h)),
            int(round(half_w * 2)), int(round(half_h * 2)),
        )
        if not self.world.collision.rect_free(box):
            return False
        if math.hypot(x - self.player.x, y - self.player.y) < 28.0:
            return False
        for enemy in self.combat.enemies:
            if not enemy.alive:
                continue
            if math.hypot(x - enemy.x, y - enemy.y) < ENEMY_SPAWN_MIN_ENEMY_DISTANCE:
                return False
        return True

    # ------------------------------------------------------------------
    @property
    def alive_count(self) -> int:
        return sum(1 for enemy in self.combat.enemies if enemy.alive)

    @property
    def max_total(self) -> int:
        return ENEMY_SPAWN_TOTAL_CAP

    @property
    def max_active(self) -> int:
        return ENEMY_MAX_ACTIVE

    @property
    def exhausted(self) -> bool:
        return self.total_spawned >= ENEMY_SPAWN_TOTAL_CAP
