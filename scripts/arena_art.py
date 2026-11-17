"""Procedural pixel-art floor for the Hollow Guardian arena.

The village ground is one baked PNG, but the shrine needs its own read: cold
flagstones, a circular seal, purple runes and old blood.  Drawing it once into
an alpha surface keeps the per-frame cost to a single blit when the arena is on
screen.  Everything is chunky primitive art, matching the existing props.
"""
from __future__ import annotations

import math
import random

import pygame


def build_arena_floor(width: int, height: int) -> pygame.Surface:
    rng = random.Random(0xA5E77)
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    surf.fill((21, 17, 27, 232))

    tile = 62
    for ty in range(-1, height // tile + 2):
        for tx in range(-1, width // tile + 2):
            x = tx * tile + (rng.randint(-3, 3) if ty % 2 else 0)
            y = ty * tile
            shade = rng.randint(-5, 7)
            base = (30 + shade, 26 + shade, 38 + shade, 236)
            pygame.draw.rect(surf, base, (x + 1, y + 1, tile - 3, tile - 3))
            pygame.draw.line(surf, (17, 14, 22, 240),
                             (x, y), (x + tile - 2, y), 2)
            pygame.draw.line(surf, (17, 14, 22, 240),
                             (x, y), (x, y + tile - 2), 2)
            if rng.random() < 0.26:
                pygame.draw.line(surf, (46, 39, 58, 190),
                                 (x + 5, y + tile - 9),
                                 (x + tile - 8, y + tile - 9), 1)

    # Purple corruption bleeding in from the sealed edges.
    for _ in range(58):
        cx = rng.randint(-20, width + 20)
        cy = rng.randint(-20, height + 20)
        edge = min(cx, width - cx, cy, height - cy)
        if edge > 150 and rng.random() < 0.55:
            continue
        rx = rng.randint(16, 54)
        ry = rng.randint(9, 30)
        pygame.draw.ellipse(surf, (54, 30, 72, 150),
                            (cx - rx, cy - ry, rx * 2, ry * 2))
        pygame.draw.ellipse(surf, (82, 46, 108, 90),
                            (cx - rx // 2, cy - ry // 2, rx, ry))

    # The seal: a wide ritual circle with a broken inner ring.
    cx, cy = width // 2, height // 2 + 18
    for radius, thick, color in (
        (188, 3, (78, 44, 110, 210)),
        (176, 1, (126, 72, 176, 190)),
        (128, 2, (96, 56, 136, 150)),
        (66, 1, (140, 86, 196, 130)),
    ):
        pygame.draw.circle(surf, color, (cx, cy), radius, thick)
    for i in range(12):
        angle = i * math.tau / 12 + 0.08
        x1 = cx + math.cos(angle) * 176
        y1 = cy + math.sin(angle) * 176
        x2 = cx + math.cos(angle) * 196
        y2 = cy + math.sin(angle) * 196
        pygame.draw.line(surf, (104, 60, 146, 170), (x1, y1), (x2, y2), 2)
    # Rune spokes, intentionally uneven.
    for i in range(6):
        angle = i * math.tau / 6 + 0.33
        mid = 96 + rng.randint(-9, 9)
        x1 = cx + math.cos(angle) * 66
        y1 = cy + math.sin(angle) * 66
        x2 = cx + math.cos(angle) * mid
        y2 = cy + math.sin(angle) * mid
        pygame.draw.line(surf, (58, 32, 86, 210), (x1, y1), (x2, y2), 3)
        pygame.draw.circle(surf, (150, 96, 212, 170),
                           (int(x2), int(y2)), 2)

    # Glowing cracks crawl out from the seal.
    for _ in range(11):
        angle = rng.uniform(0, math.tau)
        x = cx + math.cos(angle) * rng.randint(70, 170)
        y = cy + math.sin(angle) * rng.randint(50, 150)
        points = [(x, y)]
        for _step in range(rng.randint(3, 7)):
            angle += rng.uniform(-0.7, 0.7)
            x += math.cos(angle) * rng.randint(10, 26)
            y += math.sin(angle) * rng.randint(7, 19)
            points.append((x, y))
        pygame.draw.lines(surf, (62, 34, 88, 220), False, points, 3)
        pygame.draw.lines(surf, (134, 78, 188, 150), False, points, 1)

    # Chipped debris and old blood near the dais.
    for _ in range(90):
        x = rng.randint(8, width - 8)
        y = rng.randint(8, height - 8)
        size = rng.randint(1, 4)
        color = rng.choice(((42, 36, 50, 220), (54, 44, 64, 210),
                            (35, 28, 44, 220)))
        pygame.draw.rect(surf, color, (x, y, size, max(1, size - 1)))
    for _ in range(9):
        x = rng.randint(60, width - 60)
        y = rng.randint(90, height - 60)
        pygame.draw.ellipse(surf, (44, 15, 26, 130),
                            (x, y, rng.randint(18, 46), rng.randint(7, 18)))

    # Soft dark frame so the floor meets the wall bases without a hard seam.
    frame = pygame.Surface((width, height), pygame.SRCALPHA)
    for i in range(26):
        alpha = int(150 * (1.0 - i / 26.0))
        pygame.draw.rect(frame, (9, 7, 12, alpha),
                         (i, i, width - i * 2, height - i * 2), 1)
    surf.blit(frame, (0, 0))
    return surf


__all__ = ["build_arena_floor"]
