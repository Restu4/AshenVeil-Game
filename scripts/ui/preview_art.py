"""Baked atmospheric preview art for the level select.

Each preview is composed from the *existing* environment atlas (no placeholder
rectangles): the same village props, trees, masonry and portal the game uses are
laid out as a small diorama, then graded with fog, moonlight and grain.  The
surfaces are built once and cached, which keeps Pygbag's frame cost flat.
"""
from __future__ import annotations

import random

import pygame

from scripts.ui.ui_common import accent_glow

PREVIEW_W, PREVIEW_H = 288, 178
_CACHE: dict[tuple[str, int, int], pygame.Surface] = {}


def _fit(image: pygame.Surface, height: int) -> pygame.Surface:
    scale = height / max(1, image.get_height())
    size = (max(1, int(image.get_width() * scale)), max(1, int(height)))
    return pygame.transform.scale(image, size)


def _moon(surf: pygame.Surface, x: int, y: int, r: int,
          color=(196, 186, 216), halo=(74, 58, 104)) -> None:
    for i in range(7, 0, -1):
        pygame.draw.circle(surf, (*halo, 12 + i * 2), (x, y), r + i * 7)
    pygame.draw.circle(surf, color, (x, y), r)
    pygame.draw.circle(surf, (150, 138, 170), (x - r // 3, y - r // 4),
                       max(2, r // 5))
    pygame.draw.circle(surf, (160, 148, 182), (x + r // 4, y + r // 3),
                       max(2, r // 6))


def _vignette(surf: pygame.Surface, strength: int = 150) -> None:
    w, h = surf.get_size()
    layer = pygame.Surface((w, h), pygame.SRCALPHA)
    for i in range(26):
        alpha = int(strength * (1.0 - i / 26.0))
        pygame.draw.rect(layer, (5, 4, 8, alpha),
                         (i, i, w - i * 2, h - i * 2), 1)
    surf.blit(layer, (0, 0))


def _grain(surf: pygame.Surface, rng: random.Random, count: int = 90) -> None:
    w, h = surf.get_size()
    for _ in range(count):
        x = rng.randint(0, w - 1)
        y = rng.randint(0, h - 1)
        c = rng.choice(((148, 140, 160, 60), (94, 82, 116, 70),
                        (202, 190, 214, 40)))
        surf.fill(c, (x, y, 1, 1))


def _ground(surf: pygame.Surface, assets, name: str,
            color=(18, 16, 23)) -> None:
    try:
        tile = assets.image(name)
    except KeyError:
        surf.fill(color)
        return
    tile = pygame.transform.scale(tile, (96, 72))
    for y in range(96, PREVIEW_H, 68):
        for x in range(-24, PREVIEW_W, 92):
            surf.blit(tile, (x, y))
    surf.fill((*color, 90), special_flags=pygame.BLEND_RGBA_MULT)


def _village(assets, rng: random.Random) -> pygame.Surface:
    surf = pygame.Surface((PREVIEW_W, PREVIEW_H), pygame.SRCALPHA)
    surf.fill((17, 15, 24))
    for i in range(PREVIEW_H):
        k = i / PREVIEW_H
        pygame.draw.line(surf, (int(14 + 6 * k), int(12 + 4 * k),
                                int(20 + 8 * k)), (0, i), (PREVIEW_W, i))
    _moon(surf, 232, 34, 20)
    _ground(surf, assets, "dirt")

    # Back row silhouettes: church, longhouse, dead trees.
    church = _fit(assets.image("church"), 96)
    surf.blit(church, (104, 58))
    house = _fit(assets.image("house_timber"), 70)
    surf.blit(house, (10, 84))
    house2 = _fit(assets.image("house_long"), 64)
    surf.blit(pygame.transform.flip(house2, True, False), (196, 88))
    for name, x, h in (("tree_dead_tall", 56, 92), ("tree_dead_big", 258, 86)):
        tree = _fit(assets.image(name), h)
        surf.blit(pygame.transform.flip(tree, x > 128, False),
                  (x - tree.get_width() // 2, 104 - h + 22))
    # Foreground graves and the well.
    for name, x, y, h in (("gravestone_a", 28, 160, 28),
                          ("gravestone_c", 246, 162, 30),
                          ("grave_cross", 70, 158, 34),
                          ("well_small", 148, 164, 34),
                          ("lantern_tall", 204, 158, 42)):
        img = _fit(assets.image(name), h)
        surf.blit(img, (x - img.get_width() // 2, y - img.get_height()))
    mushroom = _fit(assets.image("moss_purple"), 64)
    mushroom.set_alpha(90)
    surf.blit(mushroom, (206, 132))

    accent_glow(surf, (232, 34), 54, (154, 120, 210), 34)
    fog = pygame.Surface((PREVIEW_W, 60), pygame.SRCALPHA)
    for i in range(60):
        fog.fill((70, 52, 96, 2), (0, i, PREVIEW_W, 1))
    surf.blit(fog, (0, 118))
    _vignette(surf, 168)
    _grain(surf, rng, 110)
    return surf


def _forest(assets, rng: random.Random) -> pygame.Surface:
    surf = pygame.Surface((PREVIEW_W, PREVIEW_H), pygame.SRCALPHA)
    surf.fill((12, 20, 16))
    for i in range(PREVIEW_H):
        k = i / PREVIEW_H
        pygame.draw.line(surf, (int(9 + 8 * k), int(18 + 14 * k),
                                int(13 + 6 * k)), (0, i), (PREVIEW_W, i))
    _moon(surf, 150, 26, 13, (168, 198, 170), (44, 74, 54))
    _ground(surf, assets, "moss_purple", (16, 22, 17))

    # Dense trunk wall, alternating depth.
    for x, h, name in ((16, 168, "tree_dead_big"), (62, 140, "tree_dead_tall"),
                       (116, 176, "tree_dead_big"), (176, 132, "tree_dead_tall"),
                       (224, 170, "tree_dead_big"), (276, 146, "tree_dead_tall")):
        tree = _fit(assets.image(name), h)
        if x > 140:
            tree = pygame.transform.flip(tree, True, False)
        surf.blit(tree, (x - tree.get_width() // 2, PREVIEW_H - h + 10))
    for name, x, y, h in (("bush_g", 94, 150, 22), ("bush_f", 202, 156, 24),
                          ("plant_c", 130, 142, 14), ("plant_b", 244, 146, 12),
                          ("rock_c", 164, 162, 16), ("signpost", 46, 148, 30)):
        img = _fit(assets.image(name), h)
        surf.blit(img, (x - img.get_width() // 2, y - img.get_height()))
    root = _fit(assets.image("tower_purple"), 90)
    root.set_alpha(120)
    surf.blit(root, (106, 40))
    accent_glow(surf, (150, 26), 44, (94, 170, 116), 30)
    _vignette(surf, 180)
    _grain(surf, rng, 120)
    return surf


def _dungeon(assets, rng: random.Random) -> pygame.Surface:
    surf = pygame.Surface((PREVIEW_W, PREVIEW_H), pygame.SRCALPHA)
    surf.fill((14, 14, 20))
    for i in range(PREVIEW_H):
        k = i / PREVIEW_H
        pygame.draw.line(surf, (int(11 + 5 * k), int(12 + 4 * k),
                                int(18 + 6 * k)), (0, i), (PREVIEW_W, i))
    _ground(surf, assets, "stone")
    # Receding arch corridor.
    for scale, x, y, alpha in ((1.0, 144, 52, 255), (0.7, 74, 70, 150),
                               (0.7, 214, 70, 150)):
        arch = _fit(assets.image("stone_arch"), int(96 * scale))
        arch.set_alpha(alpha)
        surf.blit(arch, (x - arch.get_width() // 2, y))
    for x in (30, 88, 202, 258):
        img = _fit(assets.image("stone_pillar_tall"), 112)
        surf.blit(img, (x - img.get_width() // 2, 42))
    for name, x, y, h in (("stone_wall", 144, 160, 28),
                          ("rubble_b", 48, 160, 16),
                          ("rubble_c", 240, 162, 18),
                          ("bones", 104, 164, 14),
                          ("skull", 184, 162, 12),
                          ("lantern_tall", 144, 132, 30)):
        img = _fit(assets.image(name), h)
        surf.blit(img, (x - img.get_width() // 2, y - img.get_height()))
    accent_glow(surf, (144, 96), 52, (150, 156, 196), 26)
    for i in range(6):
        y = 74 + i * 12
        pygame.draw.line(surf, (172, 168, 196, 40), (108 + i * 3, y),
                         (180 - i * 3, y + 6), 1)
    _vignette(surf, 196)
    _grain(surf, rng, 130)
    return surf


def _castle(assets, rng: random.Random) -> pygame.Surface:
    surf = pygame.Surface((PREVIEW_W, PREVIEW_H), pygame.SRCALPHA)
    surf.fill((20, 12, 17))
    for i in range(PREVIEW_H):
        k = i / PREVIEW_H
        pygame.draw.line(surf, (int(20 + 6 * k), int(11 + 4 * k),
                                int(15 + 6 * k)), (0, i), (PREVIEW_W, i))
    _moon(surf, 64, 36, 17, (196, 146, 156), (82, 34, 48))
    _ground(surf, assets, "dark_soil", (20, 13, 17))
    for name, x, h in (("stone_tower", 236, 128), ("tower_purple", 74, 136)):
        img = _fit(assets.image(name), h)
        surf.blit(img, (x - img.get_width() // 2, PREVIEW_H - h + 6))
    wall = _fit(assets.image("stone_wall"), 52)
    for x in range(-10, PREVIEW_W, 112):
        surf.blit(wall, (x, 108))
    gate = _fit(assets.image("stone_gate"), 84)
    surf.blit(gate, (144 - gate.get_width() // 2, 92))
    for name, x, y, h in (("stone_wall_gate", 70, 156, 34),
                          ("stone_wall_gate", 218, 156, 34),
                          ("grave_cross", 38, 160, 28),
                          ("skull_b", 248, 160, 12),
                          ("bones", 110, 164, 12)):
        img = _fit(assets.image(name), h)
        surf.blit(img, (x - img.get_width() // 2, y - img.get_height()))
    # Thorn silhouette crawling over the gate.
    for i in range(7):
        x = 112 + i * 12
        pygame.draw.line(surf, (18, 8, 12), (x, 92), (x + 8, 58 + i % 3 * 9), 2)
        pygame.draw.line(surf, (18, 8, 12), (x + 8, 58 + i % 3 * 9),
                         (x + 2, 44 + i % 4 * 6), 1)
    accent_glow(surf, (144, 86), 46, (200, 82, 104), 30)
    _vignette(surf, 190)
    _grain(surf, rng, 120)
    return surf


_BUILDERS = {
    "village": _village,
    "forest": _forest,
    "dungeon": _dungeon,
    "castle": _castle,
}


def preview_surface(assets, key: str, width: int = PREVIEW_W,
                    height: int = PREVIEW_H) -> pygame.Surface:
    cache_key = (key, width, height)
    cached = _CACHE.get(cache_key)
    if cached is not None:
        return cached
    rng = random.Random(0x5EED + sum(ord(c) for c in key))
    builder = _BUILDERS.get(key, _village)
    base = builder(assets, rng)
    if (width, height) != base.get_size():
        base = pygame.transform.smoothscale(base, (width, height))
    _CACHE[cache_key] = base
    return base


__all__ = ["PREVIEW_H", "PREVIEW_W", "preview_surface"]
