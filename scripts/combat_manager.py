"""Combat orchestration: swings, hits, enemies, engagement and feedback."""
from __future__ import annotations

import math

from scripts.combat_config import (
    ATTACK_SHAKE,
    SHAKE_PLAYER_HURT,
    SHAKE_PLAYER_HURT_TIME,
)
from scripts.enemy import FallenKnight
from scripts.player_combat import ATTACK_STATES
from scripts.village_layout import ENEMY_SPAWNS


class CombatManager:
    def __init__(self, assets, world, player, camera, effects) -> None:
        self.assets = assets
        self.world = world
        self.player = player
        self.camera = camera
        self.effects = effects
        self.enemies: list[FallenKnight] = []
        self.engaged: FallenKnight | None = None
        self.engaged_timer = 0.0
        self._seen_attack_id = -1
        self._swing_id = -1
        self._hit_enemies: set[int] = set()
        self.restart()

    # ------------------------------------------------------------------
    def restart(self) -> None:
        self.enemies = []
        for index, (x, y, radius, facing) in enumerate(ENEMY_SPAWNS, start=1):
            self.enemies.append(
                FallenKnight(self.assets, index, x, y, radius, facing)
            )
        self.engaged = None
        self.engaged_timer = 0.0
        self._seen_attack_id = -1
        self._swing_id = -1
        self._hit_enemies.clear()

    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        dt = min(dt, 0.05)
        player = self.player
        combat = player.combat
        collision = self.world.collision

        # Slash visual begins with the swing, not the damage frame.
        if combat.attack_id != self._seen_attack_id:
            self._seen_attack_id = combat.attack_id
            if combat.attack_stage:
                self.effects.spawn_slash(player.x, player.y, player.facing,
                                         combat.attack_stage)

        box = player.attack_hitbox
        if box is not None:
            if box.attack_id != self._swing_id:
                self._swing_id = box.attack_id
                self._hit_enemies.clear()
            for enemy in self.enemies:
                if not enemy.alive or enemy.id in self._hit_enemies:
                    continue
                if not box.collides(enemy.hit_rect):
                    continue
                # Do not cut through walls.
                if collision.segment_blocked(player.x, player.y - 16.0,
                                             enemy.x, enemy.y - 16.0, 2.5):
                    continue
                lost, killed = enemy.take_damage(
                    box.damage, player.x, player.y, box.knockback, box.heavy
                )
                if lost <= 0.0:
                    continue
                self._hit_enemies.add(enemy.id)
                self.engaged = enemy
                self.engaged_timer = 3.0
                self.effects.spawn_impact(enemy.x, enemy.y - 20.0, box.heavy)
                self.effects.spawn_damage_number(enemy.x, enemy.y - 26.0,
                                                 lost, box.heavy)
                if box.heavy:
                    self.camera.shake(ATTACK_SHAKE[2], 0.18)
                    self.effects.spawn_flash((18, 11, 30), 0.10)
                if killed:
                    self.effects.spawn_death(enemy.x, enemy.y)
                    self.effects.spawn_flash((26, 12, 40), 0.14)

        for enemy in self.enemies:
            enemy.update(dt, player, collision)
        self.enemies = [e for e in self.enemies if not e.removed]

        if combat.consume_hurt_signal():
            self.effects.spawn_player_hurt()
            self.effects.spawn_flash((20, 5, 12), 0.10)
            self.camera.shake(SHAKE_PLAYER_HURT, SHAKE_PLAYER_HURT_TIME)

        self._update_engagement(dt)

    # ------------------------------------------------------------------
    def _update_engagement(self, dt: float) -> None:
        player = self.player
        attacking = player.combat.state in ATTACK_STATES
        best = None
        best_distance = 1e9
        for enemy in self.enemies:
            if not enemy.alive:
                continue
            distance = math.hypot(enemy.x - player.x, enemy.y - player.y)
            if distance > 380.0:
                continue
            interested = (
                enemy.aggro_timer > 0.0
                or enemy.flash_timer > 0.0
                or enemy.hurt_timer > 0.0
                or distance < 130.0
                or (attacking and distance < 175.0)
            )
            if interested and distance < best_distance:
                best = enemy
                best_distance = distance

        if best is not None:
            self.engaged = best
            self.engaged_timer = 2.5
            return

        if self.engaged is not None:
            if not self.engaged.alive:
                self.engaged = None
                self.engaged_timer = 0.0
                return
            self.engaged_timer = max(0.0, self.engaged_timer - dt)
            distance = math.hypot(self.engaged.x - player.x,
                                  self.engaged.y - player.y)
            if self.engaged_timer <= 0.0 or distance > 440.0:
                self.engaged = None

    # ------------------------------------------------------------------
    def debug_draw(self, target, camera) -> None:
        for enemy in self.enemies:
            enemy.debug_draw(target, camera.offset)
