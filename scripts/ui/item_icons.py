"""Small hand-drawn pixel icons for inventory, drops and notifications.

Icons are generated once into 24x24 alpha surfaces and blitted at integer
scale.  No image files and no smooth scaling, so they stay crisp in the browser.
"""
from __future__ import annotations

import pygame

from scripts.item_database import ItemDef

SIZE = 24
_cache: dict[str, pygame.Surface] = {}


def _surface() -> pygame.Surface:
    return pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)


def _blade(surf, color, wide: bool = False) -> None:
    offset = 3 if wide else 5
    pygame.draw.line(surf, color, (5, 19), (18, 4), 5 if wide else 3)
    pygame.draw.line(surf, (236, 230, 246), (18, 4), (19, 3), 1)
    pygame.draw.line(surf, color, (10 - offset // 2, 14),
                     (16 - offset // 2, 8), 2)
    pygame.draw.line(surf, (172, 140, 96), (4, 15), (11, 20), 2)
    pygame.draw.rect(surf, (206, 184, 132), (10, 18, 3, 3))


def _build(name: str) -> pygame.Surface:
    surf = _surface()
    steel = (170, 176, 194)
    dark = (72, 68, 84)
    bone = (206, 196, 180)
    purple = (176, 126, 240)
    if name == "sword":
        _blade(surf, steel)
    elif name == "greatsword":
        _blade(surf, (196, 198, 216), wide=True)
    elif name == "helmet":
        pygame.draw.ellipse(surf, steel, (4, 5, 16, 14))
        pygame.draw.rect(surf, dark, (4, 11, 16, 5))
        pygame.draw.line(surf, bone, (7, 13), (17, 13), 1)
        pygame.draw.rect(surf, (120, 126, 146), (10, 2, 4, 4))
    elif name in ("armor", "robe"):
        color = steel if name == "armor" else (118, 86, 154)
        pygame.draw.polygon(surf, color, [(7, 4), (17, 4), (20, 12),
                                          (17, 21), (7, 21), (4, 12)])
        pygame.draw.line(surf, dark, (12, 5), (12, 20), 1)
        pygame.draw.line(surf, bone, (7, 9), (17, 9), 1)
    elif name == "gloves":
        pygame.draw.rect(surf, (146, 140, 154), (4, 6, 7, 11))
        pygame.draw.rect(surf, (146, 140, 154), (13, 6, 7, 11))
        pygame.draw.line(surf, dark, (5, 10), (10, 10), 1)
        pygame.draw.line(surf, dark, (14, 10), (19, 10), 1)
    elif name == "boots":
        pygame.draw.rect(surf, (122, 98, 76), (5, 4, 6, 11))
        pygame.draw.rect(surf, (122, 98, 76), (13, 4, 6, 11))
        pygame.draw.rect(surf, dark, (3, 14, 9, 5))
        pygame.draw.rect(surf, dark, (12, 14, 9, 5))
    elif name == "ring":
        pygame.draw.circle(surf, (206, 184, 118), (12, 15), 6, 2)
        pygame.draw.polygon(surf, purple, [(12, 3), (16, 8), (12, 11), (8, 8)])
    elif name == "necklace":
        pygame.draw.arc(surf, (206, 184, 118), (3, 3, 18, 18), 0.35, 2.75, 2)
        pygame.draw.polygon(surf, (132, 200, 236), [(12, 14), (16, 19),
                                                    (12, 23), (8, 19)])
    elif name in ("potion_hp", "potion_void"):
        color = (186, 58, 68) if name == "potion_hp" else (140, 84, 214)
        pygame.draw.rect(surf, bone, (10, 2, 4, 5))
        pygame.draw.polygon(surf, (154, 156, 172),
                            [(8, 7), (16, 7), (19, 12), (17, 21),
                             (7, 21), (5, 12)])
        pygame.draw.rect(surf, color, (7, 12, 10, 8))
        pygame.draw.line(surf, (240, 236, 250), (8, 10), (11, 10), 1)
    elif name == "shard":
        pygame.draw.polygon(surf, (148, 138, 152),
                            [(11, 2), (19, 12), (12, 22), (5, 13)])
        pygame.draw.line(surf, (214, 206, 224), (11, 3), (12, 21), 1)
    elif name == "ember":
        pygame.draw.polygon(surf, (236, 148, 72),
                            [(12, 2), (19, 11), (12, 22), (5, 11)])
        pygame.draw.polygon(surf, (250, 220, 150),
                            [(12, 7), (16, 12), (12, 18), (9, 12)])
    elif name == "gold":
        pygame.draw.circle(surf, (206, 158, 62), (12, 12), 9)
        pygame.draw.circle(surf, (246, 206, 106), (12, 12), 6)
        pygame.draw.line(surf, (128, 88, 34), (9, 10), (15, 14), 2)
    else:
        pygame.draw.rect(surf, (132, 122, 148), (5, 5, 14, 14), 2)
        pygame.draw.line(surf, (206, 198, 220), (7, 17), (17, 7), 2)
    return surf


def icon(name: str) -> pygame.Surface:
    key = str(name or "").strip().lower()
    surf = _cache.get(key)
    if surf is None:
        surf = _build(key)
        _cache[key] = surf
    return surf


def scaled_icon(name: str, scale: int = 2) -> pygame.Surface:
    scale = max(1, int(scale))
    if scale == 1:
        return icon(name)
    return pygame.transform.scale(icon(name), (SIZE * scale, SIZE * scale))


def draw_item_icon(target: pygame.Surface, item: ItemDef | str,
                   x: int, y: int, scale: int = 2) -> pygame.Rect:
    name = item.icon if isinstance(item, ItemDef) else str(item)
    surf = scaled_icon(name, scale)
    target.blit(surf, (x, y))
    return pygame.Rect(x, y, surf.get_width(), surf.get_height())


__all__ = ["SIZE", "draw_item_icon", "icon", "scaled_icon"]
