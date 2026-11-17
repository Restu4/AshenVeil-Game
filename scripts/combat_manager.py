"""Combat orchestration: swings, hits, enemies, spawning and feedback.

The manager is the single authority where a player swing or a void skill meets
an enemy.  It owns per-swing hit bookkeeping, critical rolls, hit stop,
attack-direction knockback, the enemy attack token, light separation, the
projectile system and the finite spawner.

Enemy AI still applies its own melee/projectile damage to the player, but all
feedback (shake, vignette, damage numbers) flows through this one place so the
three archetypes feel consistent.
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
    ENEMY_ATTACK_TOKEN_RANGE,
    ENEMY_SEPARATION,
    HIT_STOP_FINISHER,
    HIT_STOP_HEAVY,
    HIT_STOP_NORMAL,
    SHAKE_PLAYER_HURT,
    SHAKE_PLAYER_HURT_TIME,
)
from scripts.enemy import Enemy
from scripts.projectile import ProjectileSystem
from scripts.spawner import Spawner


class CombatManager:
    def __init__(self, assets, world, player, camera, effects) -> None:
        self.assets = assets
        self.world = world
        self.player = player
        self.camera = camera
        self.effects = effects
        self.enemies: list[Enemy] = []
        self.engaged: Enemy | None = None
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
        self._attack_token: Enemy | None = None
        self._separation_pairs = 0
        # Set by the skill manager so sword and magic kills both reward energy.
        self.on_kill = None

        self.spawner = Spawner(assets, world, player, self)
        self.projectiles = ProjectileSystem(assets, effects)
        self.restart()

    # ------------------------------------------------------------------
    def restart(self, spawn: bool = True) -> None:
        self.projectiles.clear()
        self.spawner.reset(spawn)
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
        self._separation_pairs = 0

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
        self._consume_enemy_signals()

        self.enemies[:] = [e for e in self.enemies if not e.removed]
        self.projectiles.update(dt, player, collision)
        self._separate_enemies(collision)
        self.spawner.update(dt)

        if combat.consume_hurt_signal():
            self.effects.spawn_player_hurt()
            self.effects.spawn_flash((20, 5, 12), 0.10)
            self.camera.shake(SHAKE_PLAYER_HURT, SHAKE_PLAYER_HURT_TIME)

        self._update_engagement(dt)

    # ------------------------------------------------------------------
    def _consume_enemy_signals(self) -> None:
        """Turn one-shot AI signals into projectiles and swipe feedback."""
        for enemy in self.enemies:
            projectile = enemy.pending_projectile
            if projectile is not None:
                ox, oy, nx, ny, blocked = projectile
                self.projectiles.spawn_from_enemy(enemy, (ox, oy), (nx, ny),
                                                  blocked)
                enemy.pending_projectile = None

            swipe = enemy.pending_swipe
            if swipe is not None:
                x, y, facing, hit = swipe
                self.effects.spawn_enemy_swipe(
                    x, y, facing, enemy.archetype.swipe_color, hit
                )
                if hit:
                    self.camera.shake(2.2, 0.10)
                enemy.pending_swipe = None

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
                self._handle_kill(enemy)

        if landed_now and not self._swing_landed:
            self._swing_landed = True
            combat.register_hit(self._swing_crit)

    # ------------------------------------------------------------------
    # Skill-facing damage API.  Every magic hit funnels through here so
    # numbers, knockback, engagement, death effects and kill rewards stay
    # identical to a sword hit.
    # ------------------------------------------------------------------
    def damage_enemy(
        self,
        enemy,
        damage: float,
        source_x: float,
        source_y: float,
        knockback: float,
        heavy: bool = False,
        crit: bool = False,
        knock_dir: tuple[float, float] | None = None,
        hit_stop: bool = True,
    ) -> tuple[float, bool]:
        if enemy is None or not enemy.alive:
            return 0.0, False
        lost, killed = enemy.take_damage(
            damage, source_x, source_y, knockback, heavy, knock_dir=knock_dir
        )
        if lost <= 0.0:
            return 0.0, False

        self.engaged = enemy
        self.engaged_timer = 3.0
        self.effects.spawn_impact(enemy.x, enemy.y - 20.0, heavy, crit)
        self.effects.spawn_damage_number(enemy.x, enemy.y - 26.0, lost,
                                         heavy, crit)
        if hit_stop:
            self.add_hit_stop(HIT_STOP_HEAVY if heavy else HIT_STOP_NORMAL)
        if crit:
            self.effects.spawn_flash((44, 32, 18), 0.09)
        if killed:
            self._handle_kill(enemy)
        return lost, killed

    def damage_area(
        self,
        x: float,
        y: float,
        radius: float,
        damage: float,
        knockback: float,
        heavy: bool = False,
        crit: bool = False,
        hit_set: set[int] | None = None,
    ) -> list[tuple[object, float, bool]]:
        """Damage every living enemy inside ``radius`` exactly once."""
        results: list[tuple[object, float, bool]] = []
        for enemy in self.enemies:
            if not enemy.alive:
                continue
            if hit_set is not None and enemy.id in hit_set:
                continue
            dx = enemy.x - x
            dy = enemy.y - y
            distance = math.hypot(dx, dy)
            if distance > radius + enemy.half_w:
                continue
            if distance < 0.001:
                knock_dir = (0.0, -1.0)
            else:
                knock_dir = (dx / distance, dy / distance)
            if hit_set is not None:
                hit_set.add(enemy.id)
            lost, killed = self.damage_enemy(
                enemy, damage, x, y, knockback, heavy=heavy, crit=crit,
                knock_dir=knock_dir,
            )
            if lost > 0.0:
                results.append((enemy, lost, killed))
        return results

    def _handle_kill(self, enemy) -> None:
        """Shared death feedback + reward hook (sword and magic)."""
        self.effects.spawn_death(enemy.x, enemy.y)
        self.effects.spawn_flash((26, 12, 40), 0.14)
        self.camera.shake(3.0, 0.12)
        if self.on_kill is not None:
            self.on_kill(enemy)

    # ------------------------------------------------------------------
    def _refresh_attack_token(self) -> None:
        """Only one enemy may own a wind-up at a time (fair timing)."""
        current = self._attack_token
        if current is not None and (not current.alive
                                    or current.state not in enemy_ai.ATTACK_STATES):
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
                if distance > enemy.attack_range * ENEMY_ATTACK_TOKEN_RANGE:
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
                separation = max(
                    ENEMY_SEPARATION,
                    first.half_w + second.half_w + 6.0,
                )
                if distance >= separation:
                    continue
                if distance < 0.001:
                    nx, ny = (1.0, 0.0)
                else:
                    nx, ny = dx / distance, dy / distance
                push = (separation - distance) * 0.5
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
    @property
    def alive_count(self) -> int:
        return sum(1 for enemy in self.enemies if enemy.alive)

    def draw_projectiles(self, target, camera) -> None:
        self.projectiles.draw(target, camera)

    def debug_draw(self, target, camera) -> None:
        for enemy in self.enemies:
            enemy.debug_draw(target, camera.offset)
        self.projectiles.debug_draw(target, camera)
        if self._attack_token is not None and self._attack_token.alive:
            enemy = self._attack_token
            sx, sy = camera.to_screen(enemy.x, enemy.y - 74)
            target.fill((255, 210, 92), (sx - 2, sy, 4, 4))
