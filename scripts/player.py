"""Player character: eight-direction movement, stamina and animation."""
from __future__ import annotations

import json
import math

import pygame

from settings import (
    PLAYER_ACCEL,
    PLAYER_SCALE,
    PLAYER_FRICTION,
    PLAYER_RUN_SPEED,
    PLAYER_WALK_SPEED,
    STAMINA_DRAIN,
    STAMINA_MAX,
    STAMINA_REGEN,
    STAMINA_REGEN_DELAY,
)
from scripts.animation import CharacterAnimator
from scripts.collision import CollisionWorld

FRAME_W = 64
FOOT_LINE = 52          # y of the character's feet inside the 64x64 frame
HALF_W = 12.0
HALF_H = 9.0

FACING_VECTORS = {
    "down": (0.0, 1.0),
    "up": (0.0, -1.0),
    "left": (-1.0, 0.0),
    "right": (1.0, 0.0),
}


class Player:
    def __init__(self, assets, x: float, y: float, facing: str = "up") -> None:
        self.assets = assets
        metadata = json.loads(
            (assets.root / "characters" / "ashen_veil_player_spritesheet.json")
            .read_text(encoding="utf-8")
        )
        self.animator = CharacterAnimator(assets.character_sheet, metadata)
        self.scale = PLAYER_SCALE
        self.frame_w = int(round(FRAME_W * self.scale))
        self.foot_line = int(round(FOOT_LINE * self.scale))
        if self.scale != 1.0:
            for animation in self.animator.animations.values():
                animation.frames = [
                    pygame.transform.scale(
                        frame, (self.frame_w, self.frame_w)
                    )
                    for frame in animation.frames
                ]
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.facing = facing
        self.moving = False
        self.running = False
        self.speed = 0.0
        self.input_x = 0.0
        self.input_y = 0.0

        self.health = 100.0
        self.health_max = 100.0
        self.stamina = STAMINA_MAX
        self.stamina_max = STAMINA_MAX
        self.level = 7
        self.stamina_delay = 0.0
        self.exhausted = False
        self.footstep_timer = 0.0
        self.footstep_pulse = False
        self.step_side = 0

    # ------------------------------------------------------------------
    def update(self, dt: float, keys, collision: CollisionWorld) -> None:
        dt = min(dt, 0.05)
        ix = 0.0
        iy = 0.0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            ix -= 1.0
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            ix += 1.0
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            iy -= 1.0
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            iy += 1.0

        length = math.hypot(ix, iy)
        if length > 1.0:
            ix /= length
            iy /= length
        self.input_x, self.input_y = ix, iy
        self.moving = length > 0.0
        if self.moving:
            self._face(ix, iy)

        want_run = (
            (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT])
            and self.moving
            and not self.exhausted
            and self.stamina > 1.0
        )
        self.running = want_run

        speed = PLAYER_RUN_SPEED if want_run else PLAYER_WALK_SPEED
        target_vx = ix * speed
        target_vy = iy * speed

        if self.moving:
            self.vx = _approach(self.vx, target_vx, PLAYER_ACCEL * dt)
            self.vy = _approach(self.vy, target_vy, PLAYER_ACCEL * dt)
        else:
            self.vx = _approach(self.vx, 0.0, PLAYER_FRICTION * dt)
            self.vy = _approach(self.vy, 0.0, PLAYER_FRICTION * dt)

        dx = self.vx * dt
        dy = self.vy * dt
        if dx or dy:
            self.x, self.y, hit_x, hit_y = collision.move(
                self.x, self.y, dx, dy, HALF_W, HALF_H
            )
            if hit_x:
                self.vx = 0.0
            if hit_y:
                self.vy = 0.0

        self.speed = math.hypot(self.vx, self.vy)

        # stamina
        if want_run and self.speed > 45.0:
            self.stamina = max(0.0, self.stamina - STAMINA_DRAIN * dt)
            self.stamina_delay = STAMINA_REGEN_DELAY
            if self.stamina <= 0.0:
                self.exhausted = True
        else:
            if self.stamina_delay > 0.0:
                self.stamina_delay = max(0.0, self.stamina_delay - dt)
            elif self.stamina < self.stamina_max:
                self.stamina = min(self.stamina_max,
                                   self.stamina + STAMINA_REGEN * dt)
        if self.exhausted and self.stamina >= 24.0:
            self.exhausted = False

        # animation
        if self.moving:
            action = "run" if (want_run and self.speed > 95.0) else "walk"
        else:
            action = "idle"
        self.animator.play(action, self.facing)
        self.animator.update(dt)

        # Footsteps are timed to the animation; atmosphere turns them into dust.
        if self.speed > 26.0:
            self.footstep_timer -= dt
            if self.footstep_timer <= 0.0:
                self.step_side ^= 1
                self.footstep_timer = 0.30 if self.speed < 150 else 0.21
                self.footstep_pulse = True
            else:
                self.footstep_pulse = False
        else:
            self.footstep_timer = 0.0
            self.footstep_pulse = False

    def _face(self, ix: float, iy: float) -> None:
        # Diagonal movement keeps the current axis when it is close; this
        # avoids flickering between two animation rows while sliding.
        ax, ay = abs(ix), abs(iy)
        horizontal = self.facing in {"left", "right"}
        if abs(ax - ay) < 0.22:
            pass
        elif ax > ay:
            horizontal = True
        else:
            horizontal = False
        if horizontal:
            self.facing = "right" if ix > 0 else "left"
        else:
            self.facing = "down" if iy > 0 else "up"

    # ------------------------------------------------------------------
    @property
    def sort_y(self) -> float:
        return self.y

    @property
    def look(self) -> tuple[float, float]:
        vx, vy = FACING_VECTORS[self.facing]
        look_x = vx * 26.0 + max(-30.0, min(30.0, self.vx * 0.12))
        look_y = vy * 16.0 + max(-20.0, min(20.0, self.vy * 0.08))
        return look_x, look_y

    def draw(self, target: pygame.Surface, offset: tuple[int, int]) -> None:
        ox, oy = offset
        sx = int(round(self.x)) - ox
        sy = int(round(self.y)) - oy
        shadow = self.assets.soft_shadow(int(40 * self.scale),
                                         int(14 * self.scale))
        target.blit(shadow, (sx - shadow.get_width() // 2,
                             sy - shadow.get_height() // 2 - 1))
        target.blit(self.animator.image,
                    (sx - self.frame_w // 2, sy - self.foot_line))

    def debug_draw(self, target: pygame.Surface, offset: tuple[int, int]) -> None:
        ox, oy = offset
        rect = pygame.Rect(
            int(round(self.x - HALF_W)) - ox,
            int(round(self.y - HALF_H)) - oy,
            int(HALF_W * 2),
            int(HALF_H * 2),
        )
        pygame.draw.rect(target, (84, 255, 156), rect, 1)
        pygame.draw.line(target, (84, 255, 156),
                         (rect.centerx, rect.centery - 18),
                         (rect.centerx, rect.centery + 24), 1)


def _approach(value: float, target: float, delta: float) -> float:
    if value < target:
        return min(target, value + delta)
    if value > target:
        return max(target, value - delta)
    return target
