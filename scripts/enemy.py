"""Archetype-driven enemy entity.

One class serves the Fallen Knight, the Void Stalker and the Ashen Cultist.
The art source, stats, reach and ranged behaviour come from an
``EnemyArchetype``; the state machine lives in ``scripts.enemy_ai`` and the
damage authority is still ``CombatManager``.

``FallenKnight`` remains as an alias so older tooling keeps importing.
"""
from __future__ import annotations

import math
import random

import pygame

from scripts import enemy_ai
from scripts.animation import CharacterAnimator
from scripts.enemy_art import FOOT_LINE as ART_FOOT_LINE
from scripts.enemy_art import FRAME as ART_FRAME
from scripts.enemy_art import ProceduralAnimator
from scripts.enemy_config import EnemyArchetype
from scripts.health import Health
from settings import ENEMY_SCALE

FOOT_LINE = 52


class Enemy:
    def __init__(
        self,
        assets,
        enemy_id: int,
        archetype: EnemyArchetype,
        x: float,
        y: float,
        facing: str = "down",
        patrol_radius: float | None = None,
    ) -> None:
        self.assets = assets
        self.id = enemy_id
        self.archetype = archetype
        self.key = archetype.key
        self.name = archetype.name
        self.subtitle = archetype.subtitle
        self.NAME = archetype.name
        self.ranged = archetype.ranged
        self.damage = archetype.damage
        self.detection = archetype.detection
        self.attack_range = archetype.attack_range
        self.attack_cooldown_max = archetype.attack_cooldown
        self.windup = archetype.windup
        self.active = archetype.active
        self.recovery = archetype.recovery
        self.attack_total = archetype.total_time
        self.chase_speed = archetype.chase_speed
        self.patrol_speed = archetype.patrol_speed
        self.patrol_radius = (archetype.patrol_radius
                              if patrol_radius is None else float(patrol_radius))
        self.memory = archetype.memory
        self.leash = archetype.leash
        self.knockback_decay = archetype.knockback_decay
        self.hurt_time = archetype.hurt_time
        self.hit_flash_time = archetype.hit_flash
        self.death_time = archetype.death_time
        self.preferred_distance = archetype.preferred_distance
        self.retreat_distance = archetype.retreat_distance
        self.retreat_speed = archetype.retreat_speed
        self.retreat_time = archetype.retreat_time

        self.scale = ENEMY_SCALE
        if archetype.art == "fallen_knight":
            sheet, metadata = assets.enemy_art("fallen_knight")
            self.animator = CharacterAnimator(sheet, metadata)
            for name, animation in self.animator.animations.items():
                if name.startswith("attack"):
                    animation.fps = archetype.attack_fps
                elif name.startswith("hurt"):
                    animation.fps = 11.0
            self.frame_w = metadata["frame_size"][0]
            self.foot_line = int(round(FOOT_LINE * self.scale))
        else:
            self.animator = ProceduralAnimator(archetype.art, self.scale)
            self.frame_w = int(round(ART_FRAME * self.scale))
            self.foot_line = int(round(ART_FOOT_LINE * self.scale))

        self.x = float(x)
        self.y = float(y)
        self.home_x = float(x)
        self.home_y = float(y)
        self.facing = facing
        self.vx = 0.0
        self.vy = 0.0
        self.knockback_x = 0.0
        self.knockback_y = 0.0
        self.half_w = archetype.half_w
        self.half_h = archetype.half_h

        self.health = Health(archetype.max_health)
        self.state = enemy_ai.IDLE
        self.state_time = 0.0
        self.patrol_target: tuple[float, float] | None = None
        self.patrol_wait = 0.0
        self.aggro_timer = 0.0
        self.hurt_timer = 0.0
        self.flash_timer = 0.0
        self.death_timer = 0.0
        self.retreat_timer = 0.0
        self.attack_time = 0.0
        self.attack_hit_done = False
        self.attack_cooldown = 0.0
        self.avoid_timer = 0.0
        self.avoid_sign = 1.0
        self.removed = False
        self.alerted = False
        self.can_attack = False
        # One-shot signals consumed by CombatManager after the AI update.
        self.pending_swipe: tuple[float, float, str, bool] | None = None
        self.pending_projectile: tuple[float, float, float, float, bool] | None = None
        self.rng = random.Random(0xA5E + enemy_id * 977)

        self.animator.play("idle", facing, restart=True)

    # ------------------------------------------------------------------
    @property
    def alive(self) -> bool:
        return not self.health.dead and not self.removed

    @property
    def dying(self) -> bool:
        return self.health.dead and not self.removed

    @property
    def sort_y(self) -> float:
        return self.y

    @property
    def hit_rect(self) -> pygame.Rect:
        return pygame.Rect(
            int(round(self.x - self.half_w)),
            int(round(self.y - self.half_h)),
            int(round(self.half_w * 2)),
            int(round(self.half_h * 2)),
        )

    # ------------------------------------------------------------------
    def update(self, dt: float, player, collision) -> None:
        enemy_ai.update_enemy(self, min(dt, 0.05), player, collision)

    # ------------------------------------------------------------------
    def take_damage(
        self,
        amount: float,
        source_x: float,
        source_y: float,
        knockback: float,
        heavy: bool = False,
        knock_dir: tuple[float, float] | None = None,
    ) -> tuple[float, bool]:
        if self.health.dead:
            return 0.0, False
        lost = self.health.damage(amount)
        if lost <= 0.0:
            return 0.0, False

        self.flash_timer = self.hit_flash_time + (0.05 if heavy else 0.0)
        self.aggro_timer = self.memory
        self.alerted = True
        if knock_dir is not None:
            dx, dy = knock_dir
            length = math.hypot(dx, dy) or 1.0
        else:
            dx = self.x - source_x
            dy = self.y - source_y
            length = math.hypot(dx, dy) or 1.0
        self.knockback_x = dx / length * knockback
        self.knockback_y = dy / length * knockback

        if self.health.dead:
            self.state = enemy_ai.DEATH
            self.death_timer = self.death_time
            self.hurt_timer = 0.0
            self.attack_cooldown = 0.0
            self.pending_swipe = None
            self.pending_projectile = None
            self.knockback_x *= 0.45
            self.knockback_y *= 0.45
            self.animator.play("death", "down", restart=True)
            return lost, True

        # A hit always interrupts a wind-up; that is the dodge/punish loop.
        self.state = enemy_ai.HURT
        self.hurt_timer = self.hurt_time
        self.attack_time = 0.0
        self.pending_swipe = None
        self.pending_projectile = None
        self.animator.play("hurt", self.facing, restart=True)
        return lost, False

    # ------------------------------------------------------------------
    def draw(self, target: pygame.Surface, offset: tuple[int, int]) -> None:
        ox, oy = offset
        sx = int(round(self.x)) - ox
        sy = int(round(self.y)) - oy
        shadow = self.assets.soft_shadow(int(44 * self.scale),
                                         int(15 * self.scale))
        alpha = 255
        if self.state == enemy_ai.DEATH:
            progress = 1.0 - max(0.0, self.death_timer) / max(0.001, self.death_time)
            if progress > 0.42:
                alpha = int(255 * max(0.0, 1.0 - (progress - 0.42) / 0.58))
        if alpha < 255:
            shadow = shadow.copy()
            shadow.set_alpha(alpha)
        target.blit(shadow, (sx - shadow.get_width() // 2,
                             sy - shadow.get_height() // 2 - 1))

        image = self.animator.image
        if self.flash_timer > 0.0 and not self.health.dead:
            image = image.copy()
            if self.ranged:
                image.fill((126, 74, 176, 0), special_flags=pygame.BLEND_RGBA_ADD)
            else:
                image.fill((132, 92, 168, 0), special_flags=pygame.BLEND_RGBA_ADD)
        elif alpha < 255:
            image = image.copy()
            image.set_alpha(alpha)
        target.blit(image, (sx - self.frame_w // 2, sy - self.foot_line))

        if not self.health.dead:
            self._draw_telegraph(target, sx, sy)

    # ------------------------------------------------------------------
    def _draw_telegraph(self, target: pygame.Surface, sx: int, sy: int) -> None:
        """Readable wind-up: where/when the blow or bolt will arrive."""
        if self.state != enemy_ai.ATTACK_WINDUP:
            return
        k = min(1.0, self.attack_time / max(0.001, self.windup))
        fx, fy = enemy_ai.FACING_VECTORS[self.facing]
        if self.ranged:
            # A swelling purple orb over the staff, plus a faint aim bead.
            cx = int(sx + fx * 14.0)
            cy = int(sy - 30.0 + fy * 8.0)
            radius = int(3 + 9 * k)
            pygame.draw.circle(target, (58, 30, 88), (cx, cy), radius + 3)
            pygame.draw.circle(target, (198, 126, 255), (cx, cy), radius)
            pygame.draw.circle(target, (246, 228, 255), (cx, cy),
                               max(1, radius // 2))
            aim = int(10 + 18 * k)
            pygame.draw.circle(target, (168, 104, 228),
                               (int(sx + fx * aim),
                                int(sy - 24.0 + fy * aim * 0.6)), 2)
            return

        cx = int(sx + fx * (16.0 + 16.0 * k))
        cy = int(sy - 18.0 + fy * (14.0 + 12.0 * k))
        radius = int(8 + 10 * k)
        color = (128 + int(78 * k), 42 + int(22 * k), 56)
        pygame.draw.circle(target, color, (cx, cy), radius, 2)
        pygame.draw.line(target, self.archetype.swipe_color, (cx - 2, cy),
                         (cx + 3, cy), 1)

    # ------------------------------------------------------------------
    def debug_draw(self, target: pygame.Surface, offset: tuple[int, int]) -> None:
        ox, oy = offset
        pygame.draw.rect(target, (255, 92, 120),
                         self.hit_rect.move(-ox, -oy), 1)
        color = (255, 190, 92) if self.aggro_timer > 0 else (120, 130, 255)
        sx = int(round(self.x)) - ox
        sy = int(round(self.y)) - oy
        pygame.draw.circle(target, color, (sx, sy),
                           int(self.patrol_radius), 1)
        pygame.draw.circle(target, (128, 180, 255), (sx, sy),
                           int(self.detection), 1)


# Compatibility alias for tools/tests written before Phase 4.
FallenKnight = Enemy
