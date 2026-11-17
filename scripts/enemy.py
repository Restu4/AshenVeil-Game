"""The Fallen Knight: a rusted undead sentinel of Ashen Village."""
from __future__ import annotations

import math
import random

import pygame

from scripts import enemy_ai
from scripts.animation import CharacterAnimator
from scripts.combat_config import (
    ENEMY_ATTACK_WINDUP,
    ENEMY_DEATH_TIME,
    ENEMY_HALF_H,
    ENEMY_HALF_W,
    ENEMY_HEALTH_MAX,
    ENEMY_HIT_FLASH,
    ENEMY_HURT_TIME,
    ENEMY_MEMORY,
    ENEMY_PATROL_RADIUS,
)
from scripts.health import Health
from settings import ENEMY_SCALE

FOOT_LINE = 52


class FallenKnight:
    NAME = "FALLEN KNIGHT"

    def __init__(
        self,
        assets,
        enemy_id: int,
        x: float,
        y: float,
        patrol_radius: float = ENEMY_PATROL_RADIUS,
        facing: str = "down",
    ) -> None:
        sheet, metadata = assets.enemy_art("fallen_knight")
        self.animator = CharacterAnimator(sheet, metadata)
        # The sheet's attack is six frames; a slower playback reads as a
        # heavy, telegraphed swing rather than a twitch.
        for name, animation in self.animator.animations.items():
            if name.startswith("attack"):
                animation.fps = 8.5
            elif name.startswith("hurt"):
                animation.fps = 11.0

        self.assets = assets
        self.id = enemy_id
        self.x = float(x)
        self.y = float(y)
        self.home_x = float(x)
        self.home_y = float(y)
        self.facing = facing
        self.patrol_radius = float(patrol_radius)
        self.scale = ENEMY_SCALE
        self.frame_w = metadata["frame_size"][0]
        self.foot_line = int(round(FOOT_LINE * self.scale))

        self.health = Health(ENEMY_HEALTH_MAX)
        self.state = enemy_ai.IDLE
        self.state_time = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.knockback_x = 0.0
        self.knockback_y = 0.0
        self.half_w = ENEMY_HALF_W
        self.half_h = ENEMY_HALF_H

        self.patrol_target: tuple[float, float] | None = None
        self.patrol_wait = 0.0
        self.aggro_timer = 0.0
        self.hurt_timer = 0.0
        self.flash_timer = 0.0
        self.death_timer = 0.0
        self.attack_time = 0.0
        self.attack_hit_done = False
        self.attack_cooldown = 0.0
        self.avoid_timer = 0.0
        self.avoid_sign = 1.0
        self.removed = False
        self.alerted = False
        # The combat manager grants this token so only one knight may wind up
        # at a time; it keeps simultaneous unavoidable hits off the table.
        self.can_attack = False
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

        self.flash_timer = ENEMY_HIT_FLASH + (0.05 if heavy else 0.0)
        self.aggro_timer = ENEMY_MEMORY
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
            self.death_timer = ENEMY_DEATH_TIME
            self.hurt_timer = 0.0
            self.attack_cooldown = 0.0
            self.knockback_x *= 0.45
            self.knockback_y *= 0.45
            self.animator.play("death", "down", restart=True)
            return lost, True

        self.state = enemy_ai.HURT
        self.hurt_timer = ENEMY_HURT_TIME
        self.attack_time = 0.0
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
            progress = 1.0 - max(0.0, self.death_timer) / ENEMY_DEATH_TIME
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
            image.fill((132, 92, 168, 0), special_flags=pygame.BLEND_RGBA_ADD)
        elif alpha < 255:
            image = image.copy()
            image.set_alpha(alpha)
        target.blit(image, (sx - self.frame_w // 2, sy - self.foot_line))

        # Readable wind-up telegraph: a growing ring where the blow will land.
        if self.state == enemy_ai.ATTACK and not self.health.dead:
            if self.attack_time < ENEMY_ATTACK_WINDUP:
                k = min(1.0, self.attack_time / max(0.001, ENEMY_ATTACK_WINDUP))
                fx, fy = enemy_ai.FACING_VECTORS[self.facing]
                cx = int(sx + fx * (16.0 + 16.0 * k))
                cy = int(sy - 18.0 + fy * (14.0 + 12.0 * k))
                radius = int(8 + 10 * k)
                color = (128 + int(78 * k), 42 + int(22 * k), 56)
                pygame.draw.circle(target, color, (cx, cy), radius, 2)
                pygame.draw.line(target, (204, 94, 98), (cx - 2, cy),
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
