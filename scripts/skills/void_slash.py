"""VOID SLASH (R): a travelling crescent of purple sword energy.

Each wave carries its own per-cast hit set, so an enemy is damaged at most once
even though the projectile overlaps it for several frames.  The wave expires
after ``SLASH_RANGE`` pixels.
"""
from __future__ import annotations

import math

from scripts.hitbox import FACING_VECTORS
from scripts.skill_config import (
    SLASH_CAST_LOCK,
    SLASH_DAMAGE,
    SLASH_HIT_RADIUS,
    SLASH_KNOCKBACK,
    SLASH_RANGE,
    SLASH_SHAKE,
    SLASH_SPEED,
    SLASH_TRAIL_INTERVAL,
)
from scripts.skills.base import VoidSlashSkill


class VoidSlash(VoidSlashSkill):
    def __init__(self) -> None:
        super().__init__()
        self.waves: list[dict] = []

    # ------------------------------------------------------------------
    def cast(self, manager) -> bool:
        if not self.can_use(manager):
            return False
        if not self.commit(manager):
            return False

        player = manager.player
        player.combat.begin_cast(SLASH_CAST_LOCK)
        dx, dy = FACING_VECTORS.get(player.facing, (1.0, 0.0))
        self.waves.append({
            "x": player.x + dx * 26.0,
            "y": player.y + dy * 26.0,
            "dx": dx,
            "dy": dy,
            "travel": 0.0,
            "trail": 0.0,
            "hit": set(),
        })
        manager.skill_effects.spawn_wave_trail(player.x, player.y, dx, dy)
        manager.camera.shake(SLASH_SHAKE, 0.12)
        return True

    # ------------------------------------------------------------------
    def update_waves(self, manager, dt: float) -> None:
        if dt <= 0.0 or not self.waves:
            return
        step = SLASH_SPEED * dt
        survivors: list[dict] = []
        for wave in self.waves:
            wave["x"] += wave["dx"] * step
            wave["y"] += wave["dy"] * step
            wave["travel"] += step

            wave["trail"] -= dt
            if wave["trail"] <= 0.0:
                wave["trail"] = SLASH_TRAIL_INTERVAL
                manager.skill_effects.spawn_wave_trail(
                    wave["x"], wave["y"], wave["dx"], wave["dy"]
                )

            hit_radius = SLASH_HIT_RADIUS
            for enemy in manager.combat.enemies:
                if not enemy.alive or enemy.id in wave["hit"]:
                    continue
                dx = enemy.x - wave["x"]
                dy = enemy.y - wave["y"]
                if math.hypot(dx, dy) > hit_radius + enemy.half_w:
                    continue
                lost, _killed = manager.combat.damage_enemy(
                    enemy,
                    SLASH_DAMAGE,
                    wave["x"],
                    wave["y"],
                    SLASH_KNOCKBACK,
                    heavy=True,
                    knock_dir=(wave["dx"], wave["dy"]),
                )
                if lost <= 0.0:
                    continue
                wave["hit"].add(enemy.id)
                manager.skill_effects.spawn_slash_flash(
                    enemy.x, enemy.y, wave["dx"], wave["dy"]
                )
                manager.camera.shake(SLASH_SHAKE * 0.55, 0.10)

            if wave["travel"] < SLASH_RANGE:
                survivors.append(wave)
        self.waves = survivors

    # ------------------------------------------------------------------
    def reset(self) -> None:
        super().reset()
        self.waves.clear()
