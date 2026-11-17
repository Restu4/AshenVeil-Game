"""Smooth, world-clamped camera."""
from __future__ import annotations

import math

import pygame

from settings import CAMERA_SMOOTH, SCREEN_H, SCREEN_W, WORLD_H, WORLD_W


class Camera:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.shake_strength = 0.0
        self.shake_time = 0.0
        self.shake_total = 0.0
        self._shake_clock = 0.0
        self._clamp()

    def _clamp(self) -> None:
        half_w = SCREEN_W / 2
        half_h = SCREEN_H / 2
        self.x = max(half_w, min(WORLD_W - half_w, self.x))
        self.y = max(half_h, min(WORLD_H - half_h, self.y))

    def shake(self, strength: float, duration: float = 0.16) -> None:
        """Short, restrained impact shake; never stacks into chaos."""
        if strength <= 0.0 or duration <= 0.0:
            return
        self.shake_strength = max(self.shake_strength * 0.4, strength)
        self.shake_total = max(duration, 0.01)
        self.shake_time = max(self.shake_time, duration)

    def snap(self, target_x: float, target_y: float) -> None:
        self.x = target_x
        self.y = target_y
        self._clamp()

    def update(
        self,
        dt: float,
        target_x: float,
        target_y: float,
        look_x: float = 0.0,
        look_y: float = 0.0,
    ) -> None:
        tx = target_x + look_x
        ty = target_y + look_y
        half_w = SCREEN_W / 2
        half_h = SCREEN_H / 2
        tx = max(half_w, min(WORLD_W - half_w, tx))
        ty = max(half_h, min(WORLD_H - half_h, ty))
        # Frame-rate independent exponential smoothing.
        t = 1.0 - math.exp(-CAMERA_SMOOTH * dt)
        self.x += (tx - self.x) * t
        self.y += (ty - self.y) * t
        self._clamp()

        if self.shake_time > 0.0:
            self.shake_time = max(0.0, self.shake_time - dt)
            self._shake_clock += dt
            if self.shake_time <= 0.0:
                self.shake_strength = 0.0

    @property
    def offset(self) -> tuple[int, int]:
        """Integer world-to-screen offset (keeps pixel art stable)."""
        ox = int(round(self.x - SCREEN_W / 2))
        oy = int(round(self.y - SCREEN_H / 2))
        if self.shake_time > 0.0 and self.shake_total > 0.0:
            k = self.shake_time / self.shake_total
            amp = self.shake_strength * k
            ox += int(round(math.sin(self._shake_clock * 72.0) * amp))
            oy += int(round(math.cos(self._shake_clock * 53.0) * amp * 0.65))
        ox = max(0, min(WORLD_W - SCREEN_W, ox))
        oy = max(0, min(WORLD_H - SCREEN_H, oy))
        return ox, oy

    def to_screen(self, x: float, y: float) -> tuple[int, int]:
        ox, oy = self.offset
        return int(round(x)) - ox, int(round(y)) - oy

    def visible_rect(self, margin: int = 0) -> pygame.Rect:
        ox, oy = self.offset
        return pygame.Rect(ox - margin, oy - margin,
                           SCREEN_W + margin * 2, SCREEN_H + margin * 2)
