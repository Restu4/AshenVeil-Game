"""Enemy projectiles: small, capped, wall-aware void bolts.

The Ashen Cultist fires these; the manager owns one ``ProjectileSystem`` so the
dodge/i-frame and damage rules stay identical to melee.  Everything is a plain
Python list with circle rendering, which is cheap in the browser.
"""
from __future__ import annotations

import math

import pygame

from scripts.enemy_config import ENEMY_PROJECTILE_LIFETIME, ENEMY_PROJECTILE_MAX
from scripts.pixel_font import draw_text  # noqa: F401  (kept for debug parity)
from settings import SCREEN_H, SCREEN_W

PLAYER_HIT_RADIUS = 14.0


class Projectile:
    __slots__ = (
        "x", "y", "dx", "dy", "speed", "damage", "radius", "color",
        "range", "travelled", "life", "dead", "owner_id", "angle",
    )

    def __init__(self, x, y, dx, dy, speed, damage, radius, color, max_range,
                 life, owner_id) -> None:
        self.x = float(x)
        self.y = float(y)
        self.dx = float(dx)
        self.dy = float(dy)
        self.speed = float(speed)
        self.damage = float(damage)
        self.radius = float(radius)
        self.color = color
        self.range = float(max_range)
        self.travelled = 0.0
        self.life = float(life)
        self.dead = False
        self.owner_id = owner_id
        self.angle = math.atan2(self.dy, self.dx)


class ProjectileSystem:
    def __init__(self, assets, effects) -> None:
        self.assets = assets
        self.effects = effects
        self.projectiles: list[Projectile] = []

    # ------------------------------------------------------------------
    def clear(self) -> None:
        self.projectiles.clear()

    def spawn_from_enemy(self, enemy, origin, direction,
                         blocked: bool = False) -> Projectile | None:
        if len(self.projectiles) >= ENEMY_PROJECTILE_MAX:
            return None
        ox, oy = origin
        nx, ny = direction
        if blocked:
            # A wall between caster and target eats the cast: no free damage.
            self.effects.spawn_projectile_impact(ox, oy, enemy.archetype.projectile_color)
            return None
        projectile = Projectile(
            ox, oy, nx, ny,
            enemy.archetype.projectile_speed,
            enemy.archetype.projectile_damage,
            enemy.archetype.projectile_radius,
            enemy.archetype.projectile_color,
            enemy.archetype.projectile_range,
            ENEMY_PROJECTILE_LIFETIME,
            enemy.id,
        )
        self.projectiles.append(projectile)
        return projectile

    # ------------------------------------------------------------------
    def update(self, dt: float, player, collision) -> None:
        if not self.projectiles:
            return
        dt = max(0.0, min(dt, 0.05))
        if dt <= 0.0:
            return
        for projectile in self.projectiles:
            self._step(projectile, dt, player, collision)
        self.projectiles = [p for p in self.projectiles if not p.dead]

    def _step(self, p: Projectile, dt: float, player, collision) -> None:
        p.life -= dt
        if p.life <= 0.0:
            p.dead = True
            return
        distance = p.speed * dt
        if distance <= 0.0:
            return
        steps = max(1, int(distance / 8.0) + 1)
        step = distance / steps
        for _ in range(steps):
            p.x += p.dx * step
            p.y += p.dy * step
            p.travelled += step

            if p.travelled >= p.range:
                self._impact(p)
                return

            # Walls stop bolts; the shot never passes through a house.
            probe = pygame.Rect(
                int(round(p.x - p.radius)), int(round(p.y - p.radius)),
                max(2, int(round(p.radius * 2))),
                max(2, int(round(p.radius * 2))),
            )
            if not collision.rect_free(probe):
                self._impact(p)
                return

            if player.combat.dead:
                continue
            dx = player.x - p.x
            dy = (player.y - 18.0) - p.y
            if math.hypot(dx, dy) <= p.radius + PLAYER_HIT_RADIUS:
                if not player.combat.invulnerable:
                    player.take_damage(p.damage, p.x, p.y)
                    self._impact(p)
                    return

    def _impact(self, projectile: Projectile) -> None:
        projectile.dead = True
        self.effects.spawn_projectile_impact(
            projectile.x, projectile.y, projectile.color
        )

    # ------------------------------------------------------------------
    def draw(self, target: pygame.Surface, camera) -> None:
        for p in self.projectiles:
            sx, sy = camera.to_screen(p.x, p.y)
            if sx < -40 or sx > SCREEN_W + 40 or sy < -40 or sy > SCREEN_H + 40:
                continue
            glow = int(p.radius + 4)
            pygame.draw.circle(target, (46, 24, 70), (sx, sy), glow)
            pygame.draw.circle(target, (118, 66, 170), (sx, sy), glow - 2)
            pygame.draw.circle(target, p.color, (sx, sy), int(p.radius))
            pygame.draw.circle(target, (244, 226, 255), (sx, sy),
                               max(1, int(p.radius * 0.45)))
            # Short tail opposite the travel direction.
            tx = int(sx - p.dx * (p.radius + 4))
            ty = int(sy - p.dy * (p.radius + 4))
            pygame.draw.line(target, (152, 92, 208), (sx, sy), (tx, ty), 2)

    def debug_draw(self, target, camera) -> None:
        for p in self.projectiles:
            sx, sy = camera.to_screen(p.x, p.y)
            pygame.draw.circle(target, (255, 96, 220), (sx, sy),
                               int(p.radius + 4), 1)
