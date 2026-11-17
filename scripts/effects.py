"""Lightweight pixel-art combat feedback.

Slashes are pre-rendered at load time (three stages x four facings) and only
alpha-blended at runtime.  Particles and damage numbers are plain Python lists
with small cached surfaces, which keeps the browser frame cheap.
"""
from __future__ import annotations

import math
import random

import pygame

from scripts.combat_config import (
    DAMAGE_NUMBER_TIME,
    HURT_VIGNETTE_TIME,
)
from scripts.pixel_font import draw_text, text_width
from settings import SCREEN_H, SCREEN_W

SLASH_SIZE = 144
FACING_ANGLE = {"right": 0.0, "down": 90.0, "left": 180.0, "up": 270.0}

PARTICLE_COLORS = ((176, 120, 255), (218, 190, 255), (128, 84, 190),
                   (238, 232, 255), (150, 96, 90))


class Effects:
    def __init__(self) -> None:
        self.rng = random.Random(0xC0FFEE)
        self._slash_cache: dict[tuple[int, str], pygame.Surface] = {}
        self._dot_cache: dict[tuple[tuple[int, int, int], int], pygame.Surface] = {}
        self._number_cache: dict[tuple[str, int], pygame.Surface] = {}
        self._vignette = self._build_hurt_vignette()

        self.slashes: list[dict] = []
        self.particles: list[dict] = []
        self.numbers: list[dict] = []
        self.hurt_timer = 0.0
        self.flash_timer = 0.0
        self.flash_duration = 0.12
        self.flash_color = (24, 14, 36)

    # ------------------------------------------------------------------
    # Spawns
    # ------------------------------------------------------------------
    def spawn_slash(self, x: float, y: float, facing: str, stage: int) -> None:
        self.slashes.append({
            "x": x,
            "y": y,
            "facing": facing,
            "stage": max(1, min(3, stage)),
            "age": 0.0,
            "duration": 0.20 if stage < 3 else 0.30,
        })
        self.slashes = self.slashes[-6:]

    def spawn_impact(self, x: float, y: float, heavy: bool = False) -> None:
        count = 18 if heavy else 9
        for _ in range(count):
            angle = self.rng.uniform(-math.pi, math.pi)
            speed = self.rng.uniform(40, 150 if heavy else 105)
            self.particles.append({
                "x": x + self.rng.uniform(-5, 5),
                "y": y - self.rng.uniform(8, 26),
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed * 0.7 - 28,
                "gravity": 240.0,
                "life": self.rng.uniform(0.22, 0.48 if heavy else 0.38),
                "max": 0.48,
                "size": self.rng.choice((2, 2, 3, 4) if heavy else (1, 2, 2, 3)),
                "color": self.rng.choice(PARTICLE_COLORS),
            })
        self.particles = self.particles[-160:]

    def spawn_death(self, x: float, y: float) -> None:
        for _ in range(26):
            angle = self.rng.uniform(-math.pi, math.pi)
            speed = self.rng.uniform(12, 75)
            self.particles.append({
                "x": x + self.rng.uniform(-14, 14),
                "y": y - self.rng.uniform(2, 38),
                "vx": math.cos(angle) * speed * 0.5,
                "vy": -self.rng.uniform(16, 62),
                "gravity": -18.0,
                "life": self.rng.uniform(0.5, 1.1),
                "max": 1.1,
                "size": self.rng.choice((1, 2, 2, 3)),
                "color": self.rng.choice(((158, 104, 238), (206, 166, 255),
                                          (92, 58, 138))),
            })
        self.particles = self.particles[-180:]

    def spawn_damage_number(self, x: float, y: float, amount: float,
                            heavy: bool = False) -> None:
        self.numbers.append({
            "x": x + self.rng.uniform(-8, 8),
            "y": y - 46,
            "vy": -34.0,
            "age": 0.0,
            "duration": DAMAGE_NUMBER_TIME,
            "surface": self._number_surface(f"{int(round(amount))}", heavy),
        })
        self.numbers = self.numbers[-16:]

    def spawn_player_hurt(self) -> None:
        self.hurt_timer = HURT_VIGNETTE_TIME

    def spawn_flash(self, color=(24, 14, 36), duration: float = 0.12) -> None:
        self.flash_color = color
        self.flash_timer = duration
        self.flash_duration = duration

    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        dt = min(dt, 0.05)
        for slash in self.slashes:
            slash["age"] += dt
        self.slashes = [s for s in self.slashes if s["age"] < s["duration"]]

        for particle in self.particles:
            particle["x"] += particle["vx"] * dt
            particle["y"] += particle["vy"] * dt
            particle["vy"] += particle["gravity"] * dt
            particle["vx"] *= 0.97
            particle["life"] -= dt
        self.particles = [p for p in self.particles if p["life"] > 0.0]

        for number in self.numbers:
            number["age"] += dt
            number["y"] += number["vy"] * dt
            number["vy"] *= 0.9
        self.numbers = [n for n in self.numbers if n["age"] < n["duration"]]

        self.hurt_timer = max(0.0, self.hurt_timer - dt)
        self.flash_timer = max(0.0, self.flash_timer - dt)

    # ------------------------------------------------------------------
    def draw_world(self, target: pygame.Surface, camera) -> None:
        for slash in self.slashes:
            surface = self._slash(slash["stage"], slash["facing"])
            t = slash["age"] / slash["duration"]
            alpha = int(235 * max(0.0, 1.0 - t) ** 0.65)
            if alpha <= 2:
                continue
            surface.set_alpha(alpha)
            sx, sy = camera.to_screen(slash["x"], slash["y"] - 16)
            target.blit(surface, (sx - SLASH_SIZE // 2, sy - SLASH_SIZE // 2))

        for particle in self.particles:
            sx, sy = camera.to_screen(particle["x"], particle["y"])
            if sx < -20 or sx > SCREEN_W + 20 or sy < -20 or sy > SCREEN_H + 20:
                continue
            life = max(0.0, particle["life"] / particle["max"])
            dot = self._dot(particle["color"], int(particle["size"]))
            dot.set_alpha(int(235 * min(1.0, life * 1.6)))
            target.blit(dot, (sx - dot.get_width() // 2,
                              sy - dot.get_height() // 2))

    def draw_overlay(self, target: pygame.Surface, camera) -> None:
        for number in self.numbers:
            sx, sy = camera.to_screen(number["x"], number["y"])
            t = number["age"] / number["duration"]
            alpha = 255
            if t > 0.45:
                alpha = int(255 * max(0.0, 1.0 - (t - 0.45) / 0.55))
            number["surface"].set_alpha(alpha)
            target.blit(number["surface"],
                        (sx - number["surface"].get_width() // 2, sy))

        if self.flash_timer > 0.0 and self.flash_duration > 0.0:
            k = self.flash_timer / self.flash_duration
            add = tuple(int(c * k) for c in self.flash_color)
            if any(add):
                target.fill(add, special_flags=pygame.BLEND_RGB_ADD)

        if self.hurt_timer > 0.0:
            k = min(1.0, self.hurt_timer / HURT_VIGNETTE_TIME)
            self._vignette.set_alpha(int(210 * k))
            target.blit(self._vignette, (0, 0))

    def clear(self) -> None:
        self.slashes.clear()
        self.particles.clear()
        self.numbers.clear()
        self.hurt_timer = 0.0
        self.flash_timer = 0.0

    # ------------------------------------------------------------------
    # Cached art
    # ------------------------------------------------------------------
    def _slash(self, stage: int, facing: str) -> pygame.Surface:
        key = (stage, facing)
        cached = self._slash_cache.get(key)
        if cached is not None:
            return cached

        radius = (44.0, 49.0, 58.0)[stage - 1]
        span = (108.0, 120.0, 152.0)[stage - 1]
        center = FACING_ANGLE.get(facing, 90.0)
        surf = pygame.Surface((SLASH_SIZE, SLASH_SIZE), pygame.SRCALPHA)
        cx = cy = SLASH_SIZE / 2
        thick = (5.0, 6.0, 8.0)[stage - 1]

        steps = int(span * 1.6)
        for i in range(steps + 1):
            t = i / steps
            angle = math.radians(center - span / 2 + span * t)
            edge = math.sin(math.pi * t) ** 0.5
            for band in range(int(thick * 2) + 2):
                r = radius + band * 0.5 - thick * 0.5
                wobble = math.sin(angle * 5.0 + stage) * 1.2
                x = int(round(cx + math.cos(angle) * (r + wobble)))
                y = int(round(cy + math.sin(angle) * (r + wobble)))
                if not (0 <= x < SLASH_SIZE and 0 <= y < SLASH_SIZE):
                    continue
                if band <= 1:
                    color = (247, 240, 255)
                    alpha = int(120 + 130 * edge)
                elif band <= thick:
                    color = (198, 156, 255)
                    alpha = int(90 + 140 * edge)
                else:
                    color = (124, 76, 190)
                    alpha = int(40 + 100 * (1.0 - band / (thick * 2)))
                surf.set_at((x, y), (*color, max(0, min(255, alpha))))

        # A few pixel sparks trailing the arc.
        for spark in range(5 if stage < 3 else 9):
            t = (spark + 0.5) / (5 if stage < 3 else 9)
            angle = math.radians(center - span * 0.32 + span * 0.64 * t)
            r = radius + 5.0 + (spark % 3) * 3.0
            x = int(round(cx + math.cos(angle) * r))
            y = int(round(cy + math.sin(angle) * r))
            surf.set_at((x, y), (236, 214, 255, 210))

        self._slash_cache[key] = surf
        return surf

    def _dot(self, color: tuple[int, int, int], size: int) -> pygame.Surface:
        key = (color, max(1, size))
        dot = self._dot_cache.get(key)
        if dot is None:
            dot = pygame.Surface((key[1], key[1]), pygame.SRCALPHA)
            dot.fill((*color, 255))
            self._dot_cache[key] = dot
        return dot

    def _number_surface(self, text: str, heavy: bool) -> pygame.Surface:
        scale = 2 if heavy else 1
        key = (text, scale)
        surface = self._number_cache.get(key)
        if surface is not None:
            return surface
        width = text_width(text, scale, 1) + 2
        height = 7 * scale + 2
        surface = pygame.Surface((width, height), pygame.SRCALPHA)
        color = (238, 186, 255) if heavy else (224, 212, 240)
        draw_text(surface, text, 0, 0, scale, color, spacing=1,
                  shadow=(6, 4, 10), center=False)
        self._number_cache[key] = surface
        return surface

    def _build_hurt_vignette(self) -> pygame.Surface:
        surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        layers = 22
        for i in range(layers):
            inset = i * 5
            alpha = int(70 * (1.0 - i / layers) ** 1.7)
            if alpha <= 0:
                continue
            pygame.draw.rect(
                surf, (122, 26, 40, alpha),
                (inset, inset, SCREEN_W - inset * 2, SCREEN_H - inset * 2),
                5,
            )
        return surf
