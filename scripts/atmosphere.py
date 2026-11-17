"""Atmosphere: darkness, lantern glow, fog, ash, motes and footstep dust."""

from __future__ import annotations

import math
import random

import pygame

from settings import SCREEN_H, SCREEN_W
from scripts.village_layout import PLAYER_LIGHT_RADIUS


def _small_radial(size: int, power: float = 2.0) -> pygame.Surface:
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size / 2
    for r in range(int(c) - 1, 0, -1):
        a = int(255 * (1.0 - r / c) ** power)
        pygame.draw.circle(surf, (255, 255, 255, a), (int(c), int(c)), r)
    return surf


def _tint_glow(color: tuple[int, int, int], radius: int) -> pygame.Surface:
    base = _small_radial(64, 2.4)
    tinted = base.copy()
    tinted.fill((*color, 255), special_flags=pygame.BLEND_RGBA_MULT)
    return pygame.transform.smoothscale(tinted, (radius * 2, radius * 2))


def _particle_sprite(color: tuple[int, int, int], size: int = 10) -> pygame.Surface:
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size // 2
    for r in range(c, 0, -1):
        a = int(210 * (1.0 - r / (c + 1)) ** 1.4)
        pygame.draw.circle(surf, (*color, a), (c, c), r)
    pygame.draw.circle(surf, (245, 238, 255, 235), (c, c), max(1, c // 4))
    return surf


def _fog_sprite(color: tuple[int, int, int], w: int, h: int) -> pygame.Surface:
    small = pygame.Surface((40, 20), pygame.SRCALPHA)
    for y in range(20):
        for x in range(40):
            dx = (x - 19.5) / 20.0
            dy = (y - 9.5) / 10.0
            d = math.sqrt(dx * dx + dy * dy)
            a = int(120 * max(0.0, 1.0 - d) ** 2.1)
            if a:
                small.set_at((x, y), (*color, a))
    return pygame.transform.smoothscale(small, (w, h))


class Atmosphere:
    def __init__(self, lights, player_light_radius: float = PLAYER_LIGHT_RADIUS) -> None:
        self.lights = lights
        self.player_radius = int(player_light_radius)
        self.t = 0.0
        self.rng = random.Random(0x51C7)

        # Darkness and the moon haze are static, so they are composited once
        # into a single full-screen layer.
        self.base = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        self.base.fill((8, 7, 15, 29))
        self.base.blit(self._build_moon(), (0, 0))
        self.vignette = self._build_vignette()

        self._glow_cache: dict[tuple[tuple[int, int, int], int], pygame.Surface] = {}
        self._particle_cache: dict[tuple[int, int, int], pygame.Surface] = {}
        self._dust_cache: dict[int, pygame.Surface] = {}
        self._ash_cache: dict[int, pygame.Surface] = {}
        self._dust = self._make_dust()
        self.player_glow = _tint_glow((140, 138, 190), self.player_radius)
        # Constant alphas are set once; the surfaces are reused as-is.
        self.player_glow.set_alpha(46)
        self.player_core = _particle_sprite((212, 208, 238), 18)
        self.player_core.set_alpha(70)

        # Runtime bloom only needs to cover the immediate flame; the wide
        # light pools are baked into the ground texture.
        self.bloom: list[tuple[int, int]] = []
        for light in self.lights:
            self.bloom.append((int(min(light.radius * 0.55, 155)),
                               light.intensity))

        self.fog: list[dict] = []
        fog_sprites = [
            _fog_sprite((132, 136, 164), 620, 224),
            _fog_sprite((111, 118, 152), 470, 186),
            _fog_sprite((150, 140, 176), 740, 258),
        ]
        for i in range(6):
            sprite = fog_sprites[i % len(fog_sprites)]
            self.fog.append({
                "x": self.rng.uniform(-300, SCREEN_W),
                "y": self.rng.uniform(60, SCREEN_H - 80),
                "sprite": sprite,
                "speed": self.rng.uniform(4.0, 13.0),
                "alpha": self.rng.randint(16, 30),
                "phase": self.rng.uniform(0, math.tau),
            })

        self.ash: list[dict] = []
        for _ in range(64):
            self.ash.append({
                "x": self.rng.uniform(0, SCREEN_W),
                "y": self.rng.uniform(0, SCREEN_H),
                "vx": self.rng.uniform(-8, 9),
                "vy": self.rng.uniform(9, 25),
                "size": self.rng.choice((1, 1, 1, 2)),
                "alpha": self.rng.randint(45, 125),
                "phase": self.rng.uniform(0, math.tau),
            })

        self.motes: list[dict] = []
        for _ in range(76):
            light = self.rng.choice(lights)
            self.motes.append({
                "light": light,
                "angle": self.rng.uniform(0, math.tau),
                "dist": self.rng.uniform(14, 105),
                "height": self.rng.uniform(2, 118),
                "rise": self.rng.uniform(4.0, 15.0),
                "spin": self.rng.uniform(-0.5, 0.5),
                "size": self.rng.choice((7, 8, 10, 12)),
                "phase": self.rng.uniform(0, math.tau),
            })

        self.dust: list[dict] = []

    # ------------------------------------------------------------------
    def _build_vignette(self) -> pygame.Surface:
        small = pygame.Surface((160, 90), pygame.SRCALPHA)
        for y in range(90):
            for x in range(160):
                nx = (x - 79.5) / 80.0
                ny = (y - 44.5) / 45.0
                d = math.sqrt(nx * nx + ny * ny)
                a = int(145 * max(0.0, (d - 0.52) / 0.58) ** 1.8)
                if a:
                    small.set_at((x, y), (3, 2, 7, min(210, a)))
        return pygame.transform.smoothscale(small, (SCREEN_W, SCREEN_H))

    def _build_moon(self) -> pygame.Surface:
        surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        glow = _tint_glow((96, 108, 158), 520)
        glow.set_alpha(24)
        surf.blit(glow, (40, -170))
        return surf

    def _make_dust(self) -> pygame.Surface:
        surf = pygame.Surface((22, 22), pygame.SRCALPHA)
        for r in range(10, 0, -1):
            a = int(42 * (1.0 - r / 11) ** 1.5)
            pygame.draw.circle(surf, (118, 110, 94, a), (11, 11), r)
        return surf

    def glow(self, color: tuple[int, int, int], radius: int) -> pygame.Surface:
        key = (color, radius)
        surf = self._glow_cache.get(key)
        if surf is None:
            surf = _tint_glow(color, radius)
            self._glow_cache[key] = surf
        return surf

    def particle(self, color: tuple[int, int, int]) -> pygame.Surface:
        surf = self._particle_cache.get(color)
        if surf is None:
            surf = _particle_sprite(color, 10)
            self._particle_cache[color] = surf
        return surf

    def dust_sprite(self, size: int) -> pygame.Surface:
        # Quantise to even sizes so scaling happens once per size bucket.
        size = max(4, size - (size % 2))
        surf = self._dust_cache.get(size)
        if surf is None:
            surf = pygame.transform.scale(self._dust, (size, size))
            self._dust_cache[size] = surf
        return surf

    def ash_sprite(self, size: int) -> pygame.Surface:
        surf = self._ash_cache.get(size)
        if surf is None:
            surf = pygame.Surface((size, size), pygame.SRCALPHA)
            surf.fill((188, 184, 198, 255))
            self._ash_cache[size] = surf
        return surf

    # ------------------------------------------------------------------
    def update(self, dt: float, player, camera) -> None:
        dt = min(dt, 0.05)
        self.t += dt

        for blob in self.fog:
            blob["x"] += blob["speed"] * dt
            blob["y"] += math.sin(self.t * 0.35 + blob["phase"]) * 2.0 * dt
            if blob["x"] > SCREEN_W + 380:
                blob["x"] = -blob["sprite"].get_width() - self.rng.uniform(0, 300)
                blob["y"] = self.rng.uniform(40, SCREEN_H - 100)
                blob["alpha"] = self.rng.randint(16, 30)

        for flake in self.ash:
            flake["x"] += (flake["vx"] + math.sin(self.t * 1.3 + flake["phase"]) * 5.0) * dt
            flake["y"] += flake["vy"] * dt
            if flake["y"] > SCREEN_H + 4:
                flake["y"] = -4
                flake["x"] = self.rng.uniform(0, SCREEN_W)
            if flake["x"] < -4:
                flake["x"] = SCREEN_W + 4
            elif flake["x"] > SCREEN_W + 4:
                flake["x"] = -4

        for mote in self.motes:
            mote["height"] += mote["rise"] * dt
            mote["angle"] += mote["spin"] * dt
            if mote["height"] > 130:
                mote["height"] = 0.0
                mote["dist"] = self.rng.uniform(10, 100)
                mote["angle"] = self.rng.uniform(0, math.tau)

        if player.footstep_pulse:
            side = -1 if player.step_side else 1
            for i in range(3 if player.speed > 150 else 2):
                self.dust.append({
                    "x": player.x + side * (4 + self.rng.uniform(-5, 5)),
                    "y": player.y - 2 + self.rng.uniform(-4, 4),
                    "vx": -player.vx * 0.08 + self.rng.uniform(-9, 9),
                    "vy": -player.vy * 0.06 - self.rng.uniform(2, 8),
                    "life": self.rng.uniform(0.30, 0.62),
                    "max": 0.62,
                    "size": self.rng.uniform(0.7, 1.25),
                })
        for puff in self.dust:
            puff["x"] += puff["vx"] * dt
            puff["y"] += puff["vy"] * dt
            puff["vx"] *= 0.94
            puff["vy"] *= 0.96
            puff["life"] -= dt
        self.dust = [d for d in self.dust if d["life"] > 0.0][-90:]

    # ------------------------------------------------------------------
    def draw(self, target: pygame.Surface, camera, player) -> None:
        target.blit(self.base, (0, 0))

        for light, (radius, intensity) in zip(self.lights, self.bloom):
            sx, sy = camera.to_screen(light.x, light.y)
            if sx < -radius or sx > SCREEN_W + radius or sy < -radius or sy > SCREEN_H + radius:
                continue
            flick = 1.0 + light.flicker * (
                math.sin(self.t * 4.1 + light.phase) * 0.6
                + math.sin(self.t * 9.7 + light.phase * 2.3) * 0.4
            )
            surf = self.glow(light.color, radius)
            surf.set_alpha(int(170 * intensity * flick))
            target.blit(surf, (sx - radius, sy - radius))

        # The player carries a faint cold aura, enough to read the silhouette.
        px, py = camera.to_screen(player.x, player.y - 24)
        target.blit(self.player_glow, (px - self.player_radius,
                                       py - self.player_radius))
        target.blit(self.player_core, (px - 9, py - 9))

        for blob in self.fog:
            sprite = blob["sprite"]
            sprite.set_alpha(blob["alpha"])
            target.blit(sprite, (int(blob["x"]), int(blob["y"])))

        # Motes drift around the nearest lanterns.
        for mote in self.motes:
            light = mote["light"]
            lx, ly = camera.to_screen(light.x, light.y)
            if lx < -150 or lx > SCREEN_W + 150 or ly < -150 or ly > SCREEN_H + 150:
                continue
            bob = math.sin(self.t * 0.9 + mote["phase"]) * 12.0
            wx = light.x + math.cos(mote["angle"]) * mote["dist"] + bob
            wy = light.y + math.sin(mote["angle"]) * mote["dist"] * 0.42 - mote["height"]
            sx, sy = camera.to_screen(wx, wy)
            sprite = self.particle(light.color)
            alpha = int(150 + math.sin(self.t * 2.4 + mote["phase"]) * 65)
            sprite.set_alpha(max(40, alpha))
            target.blit(sprite, (sx - 5, sy - 5))

        # Footstep dust sits in the world.
        for puff in self.dust:
            sx, sy = camera.to_screen(puff["x"], puff["y"])
            if sx < -40 or sx > SCREEN_W + 40 or sy < -40 or sy > SCREEN_H + 40:
                continue
            life = puff["life"] / puff["max"]
            alpha = int(120 * life)
            size = int(18 * puff["size"] * (1.4 - life * 0.4))
            if size < 4:
                continue
            sprite = self.dust_sprite(size)
            sprite.set_alpha(max(0, alpha))
            target.blit(sprite, (sx - sprite.get_width() // 2,
                                 sy - sprite.get_height() // 2))

        for flake in self.ash:
            a = flake["alpha"] + int(math.sin(self.t * 2.0 + flake["phase"]) * 22)
            sprite = self.ash_sprite(flake["size"])
            sprite.set_alpha(max(20, a))
            target.blit(sprite, (int(flake["x"]), int(flake["y"])))

        target.blit(self.vignette, (0, 0))
