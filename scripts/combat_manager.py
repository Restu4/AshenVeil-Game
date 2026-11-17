"""Combat orchestration: swings, hits, enemies, engagement and feedback.

The manager is the single place where a player swing meets a knight.  It owns
per-swing hit bookkeeping (one hit per enemy per swing), critical rolls, hit
stop, attack-direction knockback, the enemy attack token and a light separation
pass so a pack never stacks into one silhouette.
"""
from __future__ import annotations

import math

from scripts import enemy_ai
from scripts.combat_config import (
    ATTACK_SHAKE,
    CRIT_CHANCE,
    CRIT_KNOCKBACK_MULT,
    CRIT_MULTIPLIER,
    DASH_SHAKE,
    ENEMY_ATTACK_RANGE,
    ENEMY_ATTACK_TOKEN_RANGE,
    ENEMY_SEPARATION,
    ENEMY_SPAWN_COOLDOWN,
    ENEMY_SPAWN_JITTER,
    HIT_STOP_FINISHER,
    HIT_STOP_HEAVY,
    HIT_STOP_NORMAL,
    SHAKE_PLAYER_HURT,
    SHAKE_PLAYER_HURT_TIME,
)
from scripts.enemy import FallenKnight
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

        # Critical hits are rolled once per enemy per swing.  Tests pin this.
        self.crit_chance = CRIT_CHANCE

        # Hit stop freezes the simulation for a few frames after a connect.
        self.hit_stop = 0.0
        self.hit_stop_scale = 1.0

        self._seen_attack_id = -1
        self._swing_id = -1
        self._hit_enemies: set[int] = set()
        self._swing_landed = False
        self._swing_crit = False
        self._last_stage = 0
        self._attack_token: FallenKnight | None = None
        self._separation_pairs = 0
        self.restart()

    # ------------------------------------------------------------------
    def restart(self) -> None:
        self.enemies = []
        for index, (x, y, radius, facing) in enumerate(ENEMY_SPAWNS, start=1):
            knight = FallenKnight(self.assets, index, x, y, radius, facing)
            # Stagger the first permission window so the pack does not all
            # wind up on the same frame after a fresh spawn.
            knight.attack_cooldown = (
                ENEMY_SPAWN_COOLDOWN + ENEMY_SPAWN_JITTER * (index - 1)
            )
            self.enemies.append(knight)
        self.engaged = None
        self.engaged_timer = 0.0
        self.hit_stop = 0.0
        self._seen_attack_id = -1
        self._swing_id = -1
        self._hit_enemies.clear()
        self._swing_landed = False
        self._swing_crit = False
        self._last_stage = 0
        self._attack_token = None

    # ------------------------------------------------------------------
    # Hit stop
    # ------------------------------------------------------------------
    def consume_hit_stop(self, dt: float) -> float:
        """Return the simulation dt, eating frozen frames after a hit."""
        if self.hit_stop <= 0.0:
            return dt
        self.hit_stop = max(0.0, self.hit_stop - dt)
        return 0.0

    def add_hit_stop(self, seconds: float) -> None:
        seconds *= max(0.0, self.hit_stop_scale)
        if seconds > 0.0:
            self.hit_stop = max(self.hit_stop, seconds)

    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        dt = max(0.0, min(dt, 0.05))
        if dt <= 0.0:
            return
        player = self.player
        combat = player.combat
        collision = self.world.collision

        # The slash visual begins with the swing, not the damage frame.
        if combat.attack_id != self._seen_attack_id:
            self._seen_attack_id = combat.attack_id
            self._spawn_swing_visual()

        self._refresh_attack_token()
        self._resolve_swing(collision)

        for enemy in self.enemies:
            enemy.update(dt, player, collision)
        self.enemies = [e for e in self.enemies if not e.removed]

        self._separate_enemies(collision)

        if combat.consume_hurt_signal():
            self.effects.spawn_player_hurt()
            self.effects.spawn_flash((20, 5, 12), 0.10)
            self.camera.shake(SHAKE_PLAYER_HURT, SHAKE_PLAYER_HURT_TIME)

        self._update_engagement(dt)

    # ------------------------------------------------------------------
    def _spawn_swing_visual(self) -> None:
        combat = self.player.combat
        if combat.dashing:
            stage = 0
        elif combat.attack_stage:
            stage = combat.attack_stage
        else:
            return
        self._last_stage = stage
        self.effects.spawn_slash(self.player.x, self.player.y,
                                 self.player.facing, stage)
        if stage == 4:
            self.effects.spawn_nova(self.player.x, self.player.y, 92.0)
        elif stage == 5:
            self.effects.spawn_nova(self.player.x, self.player.y, 132.0)
            self.effects.spawn_flash((30, 16, 46), 0.14)
        elif stage == 0:
            self.effects.spawn_flash((20, 12, 34), 0.08)

    # ------------------------------------------------------------------
    def _resolve_swing(self, collision) -> None:
        player = self.player
        combat = player.combat
        box = player.attack_hitbox
        if box is None:
            return

        if box.attack_id != self._swing_id:
            self._swing_id = box.attack_id
            self._hit_enemies.clear()
            self._swing_landed = False
            self._swing_crit = False

        stage = box.stage
        landed_now = False
        for enemy in self.enemies:
            if not enemy.alive or enemy.id in self._hit_enemies:
                continue
            if not box.collides(enemy.hit_rect):
                continue
            # Do not cut through walls.
            if collision.segment_blocked(player.x, player.y - 16.0,
                                         enemy.x, enemy.y - 16.0, 2.5):
                continue

            crit = self.effects.rng.random() < self.crit_chance
            damage = box.damage * (CRIT_MULTIPLIER if crit else 1.0)
            knock = box.knockback * (CRIT_KNOCKBACK_MULT if crit else 1.0)
            if box.shape == "spin":
                # Radial heavy links push outward from the player.
                dx = enemy.x - player.x
                dy = enemy.y - player.y
                length = math.hypot(dx, dy) or 1.0
                knock_dir = (dx / length, dy / length)
            else:
                # Arcs always shove along the sword's travel direction.
                knock_dir = (box.knock_x, box.knock_y)

            lost, killed = enemy.take_damage(
                damage, player.x, player.y, knock, box.heavy,
                knock_dir=knock_dir,
            )
            if lost <= 0.0:
                continue
            self._hit_enemies.add(enemy.id)
            landed_now = True
            self._swing_crit = self._swing_crit or crit
            self.engaged = enemy
            self.engaged_timer = 3.0

            self.effects.spawn_impact(enemy.x, enemy.y - 20.0, box.heavy, crit)
            self.effects.spawn_damage_number(enemy.x, enemy.y - 26.0,
                                             lost, box.heavy, crit)

            if stage == 5:
                self.add_hit_stop(HIT_STOP_FINISHER)
            elif box.heavy:
                self.add_hit_stop(HIT_STOP_HEAVY)
            else:
                self.add_hit_stop(HIT_STOP_NORMAL)

            if stage == 0:
                self.camera.shake(DASH_SHAKE, 0.14)
            elif 1 <= stage <= 5:
                self.camera.shake(ATTACK_SHAKE[stage - 1], 0.12)

            if crit:
                self.effects.spawn_flash((44, 32, 18), 0.09)
            elif box.heavy:
                self.effects.spawn_flash((18, 11, 30), 0.08)

            if killed:
                self.effects.spawn_death(enemy.x, enemy.y)
                self.effects.spawn_flash((26, 12, 40), 0.14)
                self.camera.shake(3.0, 0.12)

        if landed_now and not self._swing_landed:
            self._swing_landed = True
            combat.register_hit(self._swing_crit)

    # ------------------------------------------------------------------
    def _refresh_attack_token(self) -> None:
        """Only one knight may own a wind-up at a time."""
        current = self._attack_token
        if current is not None and (not current.alive
                                    or current.state != enemy_ai.ATTACK):
            current = None

        if current is None:
            player = self.player
            best = None
            best_distance = 1e9
            for enemy in self.enemies:
                if not enemy.alive or enemy.attack_cooldown > 0.0:
                    continue
                distance = math.hypot(enemy.x - player.x,
                                      enemy.y - player.y)
                if distance > ENEMY_ATTACK_RANGE * ENEMY_ATTACK_TOKEN_RANGE:
                    continue
                if distance < best_distance:
                    best = enemy
                    best_distance = distance
            current = best

        self._attack_token = current
        for enemy in self.enemies:
            enemy.can_attack = enemy is current

    # ------------------------------------------------------------------
    def _separate_enemies(self, collision) -> None:
        alive = [e for e in self.enemies if e.alive]
        self._separation_pairs = 0
        for index, first in enumerate(alive):
            for second in alive[index + 1:]:
                dx = second.x - first.x
                dy = second.y - first.y
                distance = math.hypot(dx, dy)
                if distance >= ENEMY_SEPARATION:
                    continue
                if distance < 0.001:
                    nx, ny = (1.0, 0.0)
                else:
                    nx, ny = dx / distance, dy / distance
                push = (ENEMY_SEPARATION - distance) * 0.5
                self._push(first, -nx * push, -ny * push, collision)
                self._push(second, nx * push, ny * push, collision)
                self._separation_pairs += 1

    @staticmethod
    def _push(enemy, dx: float, dy: float, collision) -> None:
        if not dx and not dy:
            return
        enemy.x, enemy.y, hit_x, hit_y = collision.move(
            enemy.x, enemy.y, dx, dy, enemy.half_w, enemy.half_h
        )
        if hit_x:
            enemy.x -= dx * 0.35
        if hit_y:
            enemy.y -= dy * 0.35

    # ------------------------------------------------------------------
    def _update_engagement(self, dt: float) -> None:
        player = self.player
        attacking = player.combat.attack_stage > 0 or player.combat.dashing
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
        if self._attack_token is not None and self._attack_token.alive:
            enemy = self._attack_token
            sx, sy = camera.to_screen(enemy.x, enemy.y - 74)
            target.fill((255, 210, 92), (sx - 2, sy, 4, 4))
