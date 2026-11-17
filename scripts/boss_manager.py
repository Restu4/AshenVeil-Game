"""Owns the Hollow Guardian encounter inside the sealed shrine arena.

The manager is deliberately thin: the boss itself owns its AI, telegraphs and
phases; ``CombatManager`` stays the damage authority; this class only handles
the *encounter* - spawning, arena containment, the victory beat and the data the
boss HUD needs.

Nothing here teleports the player.  The level script triggers the entrance
transition and asks this manager to start the fight.
"""
from __future__ import annotations

import pygame

from scripts.bosses.hollow_guardian import DEATH, HollowGuardian
from scripts.village_layout import (
    ARENA_BOSS_BOUNDS,
    ARENA_BOSS_SPAWN,
    ARENA_PLAYER_BOUNDS,
)

# How long the corpse stays down before the victory screen may open.
VICTORY_DELAY = 2.9


class BossManager:
    def __init__(self, assets, world, player, combat, camera, effects) -> None:
        self.assets = assets
        self.world = world
        self.player = player
        self.combat = combat
        self.camera = camera
        self.effects = effects

        self.boss: HollowGuardian | None = None
        self.active = False
        self.defeated = False
        self.victory_ready = False
        self._death_clock = 0.0
        self.entrance_shake = False

    # ------------------------------------------------------------------
    @property
    def in_fight(self) -> bool:
        return self.active and not self.defeated

    @property
    def phase(self) -> int:
        return self.boss.phase if self.boss is not None else 0

    @property
    def phase_name(self) -> str:
        return self.boss.phase_name if self.boss is not None else ""

    @property
    def health_ratio(self) -> float:
        return self.boss.health_ratio if self.boss is not None else 0.0

    # ------------------------------------------------------------------
    def start(self, entrance_shake: bool = True) -> HollowGuardian:
        """Spawn the guardian and seal the arena."""
        self.stop()
        self.boss = HollowGuardian(
            self.assets,
            ARENA_BOSS_SPAWN[0],
            ARENA_BOSS_SPAWN[1],
            facing="down",
            effects=self.effects,
            camera=self.camera,
        )
        self.combat.enemies.append(self.boss)
        self.combat.engaged = None
        self.combat.engaged_timer = 0.0
        self.combat.spawner.enabled = False
        self.active = True
        self.defeated = False
        self.victory_ready = False
        self._death_clock = 0.0
        if entrance_shake and self.camera is not None:
            self.camera.shake(7.0, 0.45)
        if self.effects is not None:
            self.effects.spawn_flash((24, 10, 36), 0.28)
            self.effects.spawn_nova(ARENA_BOSS_SPAWN[0],
                                    ARENA_BOSS_SPAWN[1], 220.0)
        return self.boss

    def stop(self) -> None:
        """Remove the boss cleanly (restart, level change, menu)."""
        if self.boss is not None:
            try:
                self.combat.enemies.remove(self.boss)
            except ValueError:
                pass
            if self.combat.engaged is self.boss:
                self.combat.engaged = None
                self.combat.engaged_timer = 0.0
        self.boss = None
        self.active = False
        self.defeated = False
        self.victory_ready = False
        self._death_clock = 0.0

    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        if not self.active:
            return
        self._clamp_player()

        boss = self.boss
        if boss is None:
            return
        if boss.state == DEATH or boss.health.dead:
            self._death_clock += dt
            if self._death_clock >= VICTORY_DELAY and not self.defeated:
                self.defeated = True
                self.victory_ready = True
                # The corpse is already fading; make sure nothing can be hit.
                boss.hazards.clear()
                if self.combat.engaged is boss:
                    self.combat.engaged = None
                    self.combat.engaged_timer = 0.0

    # ------------------------------------------------------------------
    def _clamp_player(self) -> None:
        x0, y0, x1, y1 = ARENA_PLAYER_BOUNDS
        self.player.x = max(x0, min(x1, self.player.x))
        self.player.y = max(y0, min(y1, self.player.y))

    def clamp_boss(self) -> None:
        if self.boss is None:
            return
        x0, y0, x1, y1 = ARENA_BOSS_BOUNDS
        self.boss.x = max(x0, min(x1, self.boss.x))
        self.boss.y = max(y0, min(y1, self.boss.y))

    # ------------------------------------------------------------------
    def draw_world(self, target: pygame.Surface, camera) -> None:
        """Arena-only world cues (currently nothing extra beyond the boss)."""
        pass

    def debug_draw(self, target, camera) -> None:
        if self.boss is not None:
            self.boss.debug_draw(target, camera.offset)


__all__ = ["BossManager", "VICTORY_DELAY"]
