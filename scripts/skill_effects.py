"""Procedural pixel effects for the four VOID ESSENCE skills.

Nothing in here allocates a full-screen surface per frame: the one full-screen
dark overlay is built once and reused with ``set_alpha``.  Particles, rings,
afterimages and waves are capped plain-Python lists that are pruned every frame.
"""
from __future__ import annotations

import math
import random

import pygame

from scripts.skill_config import (
    SKILL_MAX_AFTERIMAGES,
    SKILL_MAX_PARTICLES,
    SKILL_MAX_RINGS,
)
from settings import SCREEN_H, SCREEN_W

BURST_COLORS = ((196, 148, 255), (144, 96, 210), (232, 214, 255),
                (98, 60, 154), (255, 240, 255))
SHADOW_COLORS = ((126, 82, 196), (88, 56, 148), (186, 150, 244),
                 (58, 36, 96))
SLASH_COLORS = ((214, 176, 255), (152, 98, 224), (246, 236, 255),
                (104, 62, 168))
ECLIPSE_COLORS = ((74, 44, 116), (128, 74, 196), (34, 22, 54),
                  (206, 158, 255), (14, 10, 22))


class SkillEffects:
    def __init__(self) -> None:
        self.rng = random.Random(0x501D)
        self.rings: list[dict] = []
        self.particles: list[dict] = []
        self.afterimages: list[dict] = []

        self.eclipse: dict | None = None
        self.dark_timer = 0.0
        self.dark_duration = 0.55

        self._dot_cache: dict[tuple[tuple[int, int, int], int], pygame.Surface] = {}
        self._dark = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        self._dark.fill((3, 1, 7, 255))

    # ------------------------------------------------------------------
    # Spawns
    # ------------------------------------------------------------------
    def _dot(self, color: tuple[int, int, int], size: int) -> pygame.Surface:
        key = (color, max(1, int(size)))
        dot = self._dot_cache.get(key)
        if dot is None:
            dot = pygame.Surface((key[1], key[1]), pygame.SRCALPHA)
            dot.fill((*color, 255))
            self._dot_cache[key] = dot
        return dot

    def _emit(self, x: float, y: float, count: int, colors, speed_lo: float,
              speed_hi: float, life_lo: float, life_hi: float,
              size_choices, gravity: float = 0.0, spread: float = 6.0,
              direction: tuple[float, float] | None = None,
              arc: float = math.pi) -> None:
        for _ in range(count):
            if direction is None:
                angle = self.rng.uniform(-math.pi, math.pi)
            else:
                base = math.atan2(direction[1], direction[0])
                angle = base + self.rng.uniform(-arc, arc)
            speed = self.rng.uniform(speed_lo, speed_hi)
            life = self.rng.uniform(life_lo, life_hi)
            self.particles.append({
                "x": x + self.rng.uniform(-spread, spread),
                "y": y + self.rng.uniform(-spread, spread),
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed,
                "gravity": gravity,
                "life": life,
                "max": life,
                "size": self.rng.choice(size_choices),
                "color": self.rng.choice(colors),
            })
        if len(self.particles) > SKILL_MAX_PARTICLES:
            del self.particles[:-SKILL_MAX_PARTICLES]

    def spawn_burst(self, x: float, y: float, radius: float) -> None:
        self._ring(x, y, radius, 0.42, "burst")
        self._emit(x, y - 6.0, 30, BURST_COLORS, 55.0, 210.0,
                   0.24, 0.52, (1, 2, 2, 3), gravity=60.0, spread=10.0)
        self._emit(x, y - 10.0, 10, BURST_COLORS, 18.0, 70.0,
                   0.34, 0.70, (2, 3, 4), gravity=-12.0, spread=18.0)

    def spawn_burst_ring(self, x: float, y: float, radius: float) -> None:
        self._ring(x, y, radius, 0.34, "burst")

    def spawn_afterimage(self, player) -> None:
        image = player.animator.image.copy()
        image.fill((46, 20, 78, 0), special_flags=pygame.BLEND_RGBA_ADD)
        self.afterimages.append({
            "x": player.x,
            "y": player.y,
            "age": 0.0,
            "duration": 0.30,
            "foot_line": player.foot_line,
            "surface": image,
        })
        if len(self.afterimages) > SKILL_MAX_AFTERIMAGES:
            del self.afterimages[:-SKILL_MAX_AFTERIMAGES]

    def spawn_shadow_puff(self, x: float, y: float, dx: float, dy: float) -> None:
        self._emit(x, y - 8.0, 12, SHADOW_COLORS, 20.0, 110.0,
                   0.18, 0.40, (1, 2, 2, 3), gravity=0.0, spread=5.0,
                   direction=(dx, dy), arc=0.9)

    def spawn_wave_trail(self, x: float, y: float, dx: float, dy: float) -> None:
        self._emit(x, y, 2, SLASH_COLORS, 10.0, 60.0, 0.14, 0.32,
                   (1, 2, 2), gravity=0.0, spread=4.0,
                   direction=(-dx, -dy), arc=0.7)

    def spawn_slash_flash(self, x: float, y: float, dx: float, dy: float) -> None:
        self._ring(x, y, 48.0, 0.22, "slash")
        self._emit(x + dx * 18.0, y - 8.0 + dy * 12.0, 10, SLASH_COLORS,
                   40.0, 150.0, 0.16, 0.34, (1, 2, 3), gravity=0.0,
                   spread=5.0, direction=(dx, dy), arc=1.1)

    def spawn_soul(self, x: float, y: float) -> None:
        self._emit(x, y - 22.0, 7, BURST_COLORS, 10.0, 48.0,
                   0.32, 0.70, (1, 2, 2), gravity=-60.0, spread=8.0)

    # ------------------------------------------------------------------
    # Eclipse
    # ------------------------------------------------------------------
    def begin_eclipse(self, x: float, y: float, windup: float,
                      radius: float) -> None:
        self.eclipse = {
            "x": x,
            "y": y,
            "age": 0.0,
            "duration": max(0.05, windup),
            "radius": float(radius),
        }
        # Essence is drawn inward while the circle is gathering.
        for _ in range(26):
            angle = self.rng.uniform(-math.pi, math.pi)
            dist = self.rng.uniform(radius * 0.35, radius * 0.95)
            px = x + math.cos(angle) * dist
            py = y + math.sin(angle) * dist
            travel = max(0.05, windup)
            self.particles.append({
                "x": px,
                "y": py,
                "vx": (x - px) / travel,
                "vy": (y - py) / travel,
                "gravity": 0.0,
                "life": travel,
                "max": travel,
                "size": self.rng.choice((1, 2, 2, 3)),
                "color": self.rng.choice(ECLIPSE_COLORS),
            })
        if len(self.particles) > SKILL_MAX_PARTICLES:
            del self.particles[:-SKILL_MAX_PARTICLES]

    def spawn_eclipse_mote(self, x: float, y: float, radius: float) -> None:
        angle = self.rng.uniform(-math.pi, math.pi)
        dist = self.rng.uniform(radius * 0.55, radius)
        px = x + math.cos(angle) * dist
        py = y + math.sin(angle) * dist
        self.particles.append({
            "x": px,
            "y": py,
            "vx": (x - px) * 2.2,
            "vy": (y - py) * 2.2,
            "gravity": 0.0,
            "life": 0.40,
            "max": 0.40,
            "size": self.rng.choice((1, 2, 2)),
            "color": self.rng.choice(ECLIPSE_COLORS),
        })
        if len(self.particles) > SKILL_MAX_PARTICLES:
            del self.particles[:-SKILL_MAX_PARTICLES]

    def detonate_eclipse(self, x: float, y: float, radius: float) -> None:
        self.eclipse = None
        self._ring(x, y, radius, 0.55, "eclipse")
        self._ring(x, y, radius * 0.72, 0.42, "burst")
        self._emit(x, y - 8.0, 72, ECLIPSE_COLORS, 80.0, 330.0,
                   0.32, 0.90, (1, 2, 3, 4, 5), gravity=80.0, spread=18.0)
        self._emit(x, y - 12.0, 24, ECLIPSE_COLORS, 20.0, 90.0,
                   0.50, 1.10, (2, 3, 4, 5), gravity=-30.0, spread=30.0)
        self.dark_timer = self.dark_duration

    def cancel_eclipse(self) -> None:
        self.eclipse = None

    # ------------------------------------------------------------------
    def _ring(self, x: float, y: float, radius: float, duration: float,
              style: str) -> None:
        self.rings.append({
            "x": x,
            "y": y - 6.0,
            "age": 0.0,
            "duration": duration,
            "radius": float(radius),
            "style": style,
        })
        if len(self.rings) > SKILL_MAX_RINGS:
            del self.rings[:-SKILL_MAX_RINGS]

    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        dt = max(0.0, min(dt, 0.05))
        for ring in self.rings:
            ring["age"] += dt
        self.rings = [r for r in self.rings if r["age"] < r["duration"]]

        for after in self.afterimages:
            after["age"] += dt
        self.afterimages = [a for a in self.afterimages
                            if a["age"] < a["duration"]]

        for particle in self.particles:
            particle["x"] += particle["vx"] * dt
            particle["y"] += particle["vy"] * dt
            particle["vy"] += particle["gravity"] * dt
            particle["vx"] *= 0.965
            particle["life"] -= dt
        self.particles = [p for p in self.particles if p["life"] > 0.0]

        if self.eclipse is not None:
            self.eclipse["age"] += dt
        self.dark_timer = max(0.0, self.dark_timer - dt)

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def draw_wave(self, target: pygame.Surface, camera, x: float, y: float,
                  dx: float, dy: float, travel: float) -> None:
        """A crescent of void energy travelling along (dx, dy)."""
        sx, sy = camera.to_screen(x, y)
        if sx < -80 or sx > SCREEN_W + 80 or sy < -80 or sy > SCREEN_H + 80:
            return
        angle = math.atan2(dy, dx)
        pulse = 1.0 + 0.10 * math.sin(travel * 0.09)
        outer = int(34 * pulse)
        inner = int(24 * pulse)
        rect = pygame.Rect(sx - outer, sy - outer, outer * 2, outer * 2)
        # pygame arcs use screen-space angles; spreading across the direction
        # of travel produces the crescent's open side.
        start = angle + math.pi * 0.55
        end = angle - math.pi * 0.55
        pygame.draw.arc(target, (84, 46, 140), rect, start, end, 6)
        rect = pygame.Rect(sx - inner, sy - inner, inner * 2, inner * 2)
        pygame.draw.arc(target, (188, 146, 255), rect, start, end, 3)
        pygame.draw.arc(target, (246, 238, 255), (sx - inner + 3, sy - inner + 3,
                                                  inner * 2 - 6, inner * 2 - 6),
                        start, end, 1)
        # A bright pixel core sells the impact without a blur pass.
        target.fill((232, 214, 255), (sx - 1, sy - 1, 3, 3))

    def draw_world(self, target: pygame.Surface, camera) -> None:
        # Eclipse wind-up: a gathering sigil that grows as the cast completes.
        if self.eclipse is not None:
            x = self.eclipse["x"]
            y = self.eclipse["y"]
            duration = max(0.001, self.eclipse["duration"])
            t = min(1.0, self.eclipse["age"] / duration)
            radius = int(self.eclipse["radius"] * (0.16 + 0.84 * t))
            sx, sy = camera.to_screen(x, y)
            if radius > 2:
                pygame.draw.circle(target, (72, 40, 116), (sx, sy), radius, 2)
                pygame.draw.circle(target, (150, 100, 220), (sx, sy),
                                   int(radius * 0.72), 1)
                for step in range(6):
                    angle = step * math.pi / 3.0 + t * 2.4
                    x1 = int(sx + math.cos(angle) * radius * 0.42)
                    y1 = int(sy + math.sin(angle) * radius * 0.42)
                    x2 = int(sx + math.cos(angle) * radius * 0.92)
                    y2 = int(sy + math.sin(angle) * radius * 0.92)
                    pygame.draw.line(target, (176, 126, 244), (x1, y1),
                                     (x2, y2), 1)

        for after in self.afterimages:
            t = min(1.0, after["age"] / after["duration"])
            alpha = int(120 * (1.0 - t) ** 1.2)
            if alpha <= 2:
                continue
            surface = after["surface"]
            surface.set_alpha(alpha)
            sx, sy = camera.to_screen(after["x"], after["y"])
            target.blit(surface, (sx - surface.get_width() // 2,
                                  sy - after.get("foot_line", 104)))

        for ring in self.rings:
            t = min(1.0, ring["age"] / ring["duration"])
            radius = int(ring["radius"] * (0.16 + 0.84 * t))
            if radius < 2:
                continue
            sx, sy = camera.to_screen(ring["x"], ring["y"])
            fade = max(0.0, 1.0 - t)
            if ring["style"] == "eclipse":
                outer = (int(96 + 78 * fade), int(48 + 48 * fade),
                         int(150 + 80 * fade))
                inner = (int(28 + 40 * fade), int(16 + 26 * fade),
                         int(52 + 48 * fade))
                pygame.draw.circle(target, outer, (sx, sy), radius, 4)
                pygame.draw.circle(target, inner, (sx, sy),
                                   max(1, radius - 8), 2)
                for step in range(8):
                    angle = step * math.pi / 4.0 + t * 1.4
                    x1 = int(sx + math.cos(angle) * radius * 0.62)
                    y1 = int(sy + math.sin(angle) * radius * 0.62)
                    x2 = int(sx + math.cos(angle) * radius)
                    y2 = int(sy + math.sin(angle) * radius)
                    pygame.draw.line(target, outer, (x1, y1), (x2, y2), 1)
            elif ring["style"] == "slash":
                color = (int(150 + 80 * fade), int(104 + 80 * fade),
                         int(220 + 35 * fade))
                pygame.draw.circle(target, color, (sx, sy), radius, 2)
            else:
                outer = (int(132 + 92 * fade), int(82 + 96 * fade),
                         int(196 + 59 * fade))
                inner = (int(220 + 35 * fade), int(180 + 60 * fade), 255)
                pygame.draw.circle(target, outer, (sx, sy), radius, 3)
                if radius > 8:
                    pygame.draw.circle(target, inner, (sx, sy),
                                       int(radius * 0.70), 1)

        for particle in self.particles:
            sx, sy = camera.to_screen(particle["x"], particle["y"])
            if sx < -24 or sx > SCREEN_W + 24 or sy < -24 or sy > SCREEN_H + 24:
                continue
            life = max(0.0, particle["life"] / particle["max"])
            dot = self._dot(particle["color"], particle["size"])
            dot.set_alpha(int(238 * min(1.0, life * 1.7)))
            target.blit(dot, (sx - dot.get_width() // 2,
                              sy - dot.get_height() // 2))

    # ------------------------------------------------------------------
    def draw_overlay(self, target: pygame.Surface) -> None:
        alpha = 0.0
        if self.eclipse is not None:
            t = min(1.0, self.eclipse["age"] / self.eclipse["duration"])
            alpha = 118.0 * min(1.0, t / 0.75)
            if t > 0.82:
                alpha += 26.0 * ((t - 0.82) / 0.18)
        if self.dark_timer > 0.0:
            k = self.dark_timer / max(0.001, self.dark_duration)
            alpha = max(alpha, 200.0 * (k ** 1.35))
        if alpha < 1.0:
            return
        self._dark.set_alpha(int(max(0.0, min(255.0, alpha))))
        target.blit(self._dark, (0, 0))

    # ------------------------------------------------------------------
    def clear(self) -> None:
        self.rings.clear()
        self.particles.clear()
        self.afterimages.clear()
        self.eclipse = None
        self.dark_timer = 0.0
