"""Lightweight pixel-art combat feedback.

Slash arcs are pre-rendered per stage/facing at load time and only alpha-blended
at runtime.  Particles and damage numbers are plain Python lists with small
cached surfaces, which keeps the browser frame cheap.  Nothing here allocates
a full-screen surface per frame.
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

SLASH_SIZE = 200
FACING_ANGLE = {"right": 0.0, "down": 90.0, "left": 180.0, "up": 270.0}

# radius, arc span, centre offset, stroke thickness, second arc, dash streak
SLASH_STYLES = {
    0: dict(radius=52, span=76, offset=0, thick=6, double=False, streak=True),
    1: dict(radius=46, span=112, offset=0, thick=5, double=False, streak=False),
    2: dict(radius=44, span=100, offset=-24, thick=5, double=False, streak=False),
    3: dict(radius=52, span=124, offset=40, thick=6, double=False, streak=False),
    4: dict(radius=72, span=360, offset=0, thick=7, double=False, streak=False),
    5: dict(radius=84, span=176, offset=0, thick=9, double=True, streak=False),
}

SLASH_DURATION = {0: 0.18, 1: 0.20, 2: 0.20, 3: 0.22, 4: 0.28, 5: 0.36}

PARTICLE_COLORS = ((176, 120, 255), (218, 190, 255), (128, 84, 190),
                   (238, 232, 255), (150, 96, 90))
CRIT_COLORS = ((255, 224, 160), (255, 246, 214), (214, 164, 255),
               (240, 200, 128))


class Effects:
    def __init__(self) -> None:
        self.rng = random.Random(0xC0FFEE)
        self._slash_cache: dict[tuple[int, str], pygame.Surface] = {}
        self._dot_cache: dict[tuple[tuple[int, int, int], int], pygame.Surface] = {}
        self._number_cache: dict[tuple[str, int, int], pygame.Surface] = {}
        self._vignette = self._build_hurt_vignette()

        self.slashes: list[dict] = []
        self.swipes: list[dict] = []
        self.particles: list[dict] = []
        self.numbers: list[dict] = []
        self.novas: list[dict] = []
        self.hurt_timer = 0.0
        self.flash_timer = 0.0
        self.flash_duration = 0.12
        self.flash_color = (24, 14, 36)

    # ------------------------------------------------------------------
    # Spawns
    # ------------------------------------------------------------------
    def spawn_slash(self, x: float, y: float, facing: str, stage: int) -> None:
        stage = max(0, min(5, int(stage)))
        self.slashes.append({
            "x": x,
            "y": y,
            "facing": facing,
            "stage": stage,
            "age": 0.0,
            "duration": SLASH_DURATION[stage],
        })
        self.slashes = self.slashes[-8:]

    def spawn_impact(self, x: float, y: float, heavy: bool = False,
                     crit: bool = False) -> None:
        if crit:
            count = 22
            colors = CRIT_COLORS
            top_speed = 190
        else:
            count = 20 if heavy else 9
            colors = PARTICLE_COLORS
            top_speed = 165 if heavy else 105
        for _ in range(count):
            angle = self.rng.uniform(-math.pi, math.pi)
            speed = self.rng.uniform(40, top_speed)
            self.particles.append({
                "x": x + self.rng.uniform(-5, 5),
                "y": y - self.rng.uniform(8, 26),
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed * 0.7 - 28,
                "gravity": 240.0,
                "life": self.rng.uniform(0.22, 0.50 if (heavy or crit) else 0.38),
                "max": 0.50,
                "size": self.rng.choice((2, 2, 3, 4) if (heavy or crit)
                                       else (1, 2, 2, 3)),
                "color": self.rng.choice(colors),
            })
        self.particles = self.particles[-200:]

    def spawn_enemy_swipe(self, x: float, y: float, facing: str,
                          color=(204, 94, 98), hit: bool = False) -> None:
        """Short, low-cost arc telling the player an enemy just struck."""
        self.swipes.append({
            "x": x,
            "y": y,
            "facing": facing,
            "color": color,
            "hit": hit,
            "age": 0.0,
            "duration": 0.20,
        })
        self.swipes = self.swipes[-10:]
        if hit:
            for _ in range(5):
                angle = self.rng.uniform(-math.pi, math.pi)
                speed = self.rng.uniform(25, 80)
                self.particles.append({
                    "x": x + self.rng.uniform(-4, 4),
                    "y": y - self.rng.uniform(14, 26),
                    "vx": math.cos(angle) * speed,
                    "vy": math.sin(angle) * speed * 0.6 - 14,
                    "gravity": 180.0,
                    "life": self.rng.uniform(0.14, 0.28),
                    "max": 0.28,
                    "size": self.rng.choice((1, 2, 2)),
                    "color": color,
                })
            self.particles = self.particles[-200:]

    def spawn_projectile_impact(self, x: float, y: float,
                                color=(198, 126, 255)) -> None:
        """Small purple pop when a bolt hits a wall or the player."""
        for _ in range(10):
            angle = self.rng.uniform(-math.pi, math.pi)
            speed = self.rng.uniform(35, 120)
            self.particles.append({
                "x": x + self.rng.uniform(-3, 3),
                "y": y + self.rng.uniform(-3, 3),
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed * 0.8 - 16,
                "gravity": 170.0,
                "life": self.rng.uniform(0.16, 0.34),
                "max": 0.34,
                "size": self.rng.choice((1, 2, 2, 3)),
                "color": self.rng.choice((color, (232, 206, 255),
                                          (120, 70, 168))),
            })
        self.particles = self.particles[-200:]

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
        self.particles = self.particles[-200:]

    def spawn_nova(self, x: float, y: float, radius: float = 112.0) -> None:
        """Expanding purple ring for the spin and the finisher."""
        self.novas.append({
            "x": x,
            "y": y - 8.0,
            "age": 0.0,
            "duration": 0.34,
            "radius": float(radius),
        })
        self.novas = self.novas[-3:]

    def spawn_damage_number(self, x: float, y: float, amount: float,
                            heavy: bool = False, crit: bool = False) -> None:
        text = f"{int(round(amount))}"
        if crit:
            text += "!"
        self.numbers.append({
            "x": x + self.rng.uniform(-8, 8),
            "y": y - 46,
            "vy": -34.0,
            "age": 0.0,
            "duration": DAMAGE_NUMBER_TIME,
            "surface": self._number_surface(text, heavy, crit),
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
        dt = max(0.0, min(dt, 0.05))
        for slash in self.slashes:
            slash["age"] += dt
        self.slashes = [s for s in self.slashes if s["age"] < s["duration"]]

        for swipe in self.swipes:
            swipe["age"] += dt
        self.swipes = [s for s in self.swipes if s["age"] < s["duration"]]

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

        for nova in self.novas:
            nova["age"] += dt
        self.novas = [n for n in self.novas if n["age"] < n["duration"]]

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

        for swipe in self.swipes:
            t = swipe["age"] / swipe["duration"]
            alpha = max(0.0, 1.0 - t)
            if swipe["facing"] == "left":
                base = 180.0
            elif swipe["facing"] == "up":
                base = 270.0
            elif swipe["facing"] == "down":
                base = 90.0
            else:
                base = 0.0
            sx, sy = camera.to_screen(swipe["x"], swipe["y"] - 18)
            color = tuple(int(c * (0.55 + 0.45 * alpha)) for c in swipe["color"])
            radius = 22 + int(8 * (1.0 - alpha))
            for offset in (-26, -8, 10, 28):
                angle = math.radians(base + offset)
                length = radius + (4 if offset in (-8, 10) else 0)
                x2 = int(sx + math.cos(angle) * length)
                y2 = int(sy + math.sin(angle) * length * 0.72)
                pygame.draw.line(target, color, (sx, sy), (x2, y2), 2)

        for nova in self.novas:
            t = min(1.0, nova["age"] / nova["duration"])
            radius = int(nova["radius"] * (0.28 + 0.72 * t))
            sx, sy = camera.to_screen(nova["x"], nova["y"])
            fade = max(0.0, 1.0 - t)
            outer = (int(120 + 100 * fade), int(70 + 90 * fade),
                     int(170 + 70 * fade))
            inner = (int(190 + 55 * fade), int(150 + 80 * fade), 255)
            if radius > 2:
                pygame.draw.circle(target, outer, (sx, sy), radius, 2)
            if radius > 9:
                pygame.draw.circle(target, inner, (sx, sy),
                                   int(radius * 0.72), 1)

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
        self.swipes.clear()
        self.particles.clear()
        self.numbers.clear()
        self.novas.clear()
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

        style = SLASH_STYLES[stage]
        radius = style["radius"]
        span = style["span"]
        center = FACING_ANGLE.get(facing, 90.0) + style["offset"]
        thick = style["thick"]
        surf = pygame.Surface((SLASH_SIZE, SLASH_SIZE), pygame.SRCALPHA)
        cx = cy = SLASH_SIZE / 2

        # Main arc (or full ring for the spin).
        steps = int(span * 1.7)
        for i in range(steps + 1):
            t = i / steps
            angle = math.radians(center - span / 2 + span * max(0.0, span and t))
            edge = math.sin(math.pi * t) ** 0.5 if span < 360 else 1.0
            for band in range(int(thick * 2) + 2):
                r = radius + band * 0.5 - thick * 0.5
                wobble = math.sin(angle * 5.0 + stage) * 1.2
                x = int(round(cx + math.cos(angle) * (r + wobble)))
                y = int(round(cy + math.sin(angle) * (r + wobble)))
                if not (0 <= x < SLASH_SIZE and 0 <= y < SLASH_SIZE):
                    continue
                if band <= 1:
                    color = (247, 240, 255)
                    alpha = int(130 + 125 * edge)
                elif band <= thick:
                    color = (198, 156, 255)
                    alpha = int(95 + 140 * edge)
                else:
                    color = (124, 76, 190)
                    alpha = int(40 + 100 * (1.0 - band / (thick * 2)))
                if stage == 0:
                    color = (236, 196, 255) if band <= 1 else color
                surf.set_at((x, y), (*color, max(0, min(255, alpha))))

        # Second, wider ghost arc on the finisher.
        if style["double"]:
            for i in range(steps + 1):
                t = i / steps
                angle = math.radians(center - span / 2 + span * t)
                edge = math.sin(math.pi * t) ** 0.5
                for band in range(3):
                    r = radius + 12 + band * 0.6
                    x = int(round(cx + math.cos(angle) * r))
                    y = int(round(cy + math.sin(angle) * r))
                    if 0 <= x < SLASH_SIZE and 0 <= y < SLASH_SIZE:
                        surf.set_at((x, y), (158, 104, 238,
                                             int(40 + 70 * edge)))

        # A dash attack leaves a bright forward streak.
        if style["streak"]:
            angle = math.radians(center)
            for i in range(-radius, radius + 1, 2):
                x = int(round(cx + math.cos(angle) * i))
                y = int(round(cy + math.sin(angle) * i))
                if not (0 <= x < SLASH_SIZE and 0 <= y < SLASH_SIZE):
                    continue
                fade = 1.0 - abs(i) / radius
                if fade <= 0.0:
                    continue
                surf.set_at((x, y), (224, 186, 255, int(40 + 150 * fade)))

        # A few pixel sparks trailing the arc.
        spark_count = 5 if stage < 4 else 9
        for spark in range(spark_count):
            t = (spark + 0.5) / spark_count
            angle = math.radians(center - span * 0.32 + span * 0.64 * t)
            r = radius + 5.0 + (spark % 3) * 3.0
            x = int(round(cx + math.cos(angle) * r))
            y = int(round(cy + math.sin(angle) * r))
            if 0 <= x < SLASH_SIZE and 0 <= y < SLASH_SIZE:
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

    def _number_surface(self, text: str, heavy: bool, crit: bool) -> pygame.Surface:
        # Readable at a glance: light hits are 2x the pixel font, heavy/crit 3x.
        scale = 3 if (crit or heavy) else 2
        key = (text, scale, 1 if crit else 0)
        surface = self._number_cache.get(key)
        if surface is not None:
            return surface
        width = text_width(text, scale, 1) + 2
        height = 7 * scale + 2
        surface = pygame.Surface((width, height), pygame.SRCALPHA)
        if crit:
            color = (255, 224, 160)
        elif heavy:
            color = (238, 186, 255)
        else:
            color = (224, 212, 240)
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
