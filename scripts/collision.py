"""Static collision footprints for the village and axis-separated movement."""
from __future__ import annotations

from collections import defaultdict

import pygame

from settings import WORLD_H, WORLD_W
from scripts.village_layout import (
    EXTRA_SOLIDS,
    NON_SOLID,
    Prop,
)

BORDER = 56


def _rect(cx: float, base_y: float, w: float, h: float, y_shift: float = 0.0) -> pygame.Rect:
    return pygame.Rect(
        int(round(cx - w / 2)),
        int(round(base_y - h + y_shift)),
        max(2, int(round(w))),
        max(2, int(round(h))),
    )


def prop_collider(prop: Prop, dims: tuple[int, int]) -> pygame.Rect | None:
    """Return the walk-blocking footprint for a prop, or None."""
    name = prop.name
    w, h = dims[0] * prop.scale, dims[1] * prop.scale
    x, y = prop.x, prop.y

    if name in NON_SOLID:
        return None
    if name.startswith("house") or name in {"church", "tower_purple"}:
        return _rect(x, y, w * 0.84, min(104, max(46, h * 0.22)), 4)
    if name == "stone_tower":
        return _rect(x, y, w * 0.68, min(72, h * 0.24), 3)
    if name in {"stone_gate", "stone_arch"}:
        return None  # explicit solid piers, see EXTRA_SOLIDS
    if name == "stone_wall_gate":
        return _rect(x, y, w * 0.92, 34, 4)
    if name == "stone_wall":
        return _rect(x, y, w * 0.92, 28, 4)
    if name.startswith("stone_pillar_tall"):
        return _rect(x, y, min(44, w * 0.45), 24, 3)
    if name.startswith("stone_pillar"):
        return _rect(x, y, max(14, w * 0.85), 16, 2)
    if name == "well":
        return _rect(x, y, w * 0.72, 42, 3)
    if name == "well_small":
        return _rect(x, y, w * 0.70, 22, 2)
    if name == "cart":
        return _rect(x, y, w * 0.82, 34, 4)
    if name.startswith(("barrel", "crate")):
        return _rect(x, y, w * 0.72, 18, 2)
    if name in {"woodpile", "logs"}:
        return _rect(x, y, w * 0.86, 20, 2)
    if name.startswith("rock"):
        return _rect(x, y, w * 0.68, max(12, h * 0.32), 2)
    if name.startswith("rubble"):
        return _rect(x, y, w * 0.76, max(10, h * 0.24), 2)
    if name.startswith("tree_dead"):
        return _rect(x, y, max(16, w * 0.22), 18, 2)
    if name.startswith("bush"):
        return None
    if name.startswith("grave"):
        return _rect(x, y, w * 0.62, 13, 2)
    if name in {"skull", "skull_b", "bones"}:
        return None
    if name == "portal":
        return _rect(x, y, 44, 20, 2)
    if name in {"statue", "statue_great"}:
        return _rect(x, y, w * 0.52, 24, 2)
    if name == "signpost":
        return _rect(x, y, 18, 15, 2)
    if name == "shrine":
        return _rect(x, y, w * 0.62, 16, 2)
    if name in {"lantern_tall", "lamp_post"}:
        return _rect(x, y, 12, 12, 2)
    if name.startswith("fence"):
        return _rect(x, y, w * 0.96, 14, 1)
    if name.startswith("plant"):
        return None
    return _rect(x, y, w * 0.5, 14, 0)


class CollisionWorld:
    """A small spatial hash of static rectangles plus foot-circle movement."""

    CELL = 192

    def __init__(self, props: list[Prop], dims_for) -> None:
        self.rects: list[pygame.Rect] = [
            pygame.Rect(0, 0, WORLD_W, BORDER),
            pygame.Rect(0, WORLD_H - BORDER, WORLD_W, BORDER),
            pygame.Rect(0, 0, BORDER, WORLD_H),
            pygame.Rect(WORLD_W - BORDER, 0, BORDER, WORLD_H),
        ]
        for prop in props:
            rect = prop_collider(prop, dims_for(prop.name))
            if rect is not None:
                self.rects.append(rect)
        for cx, cy, w, h in EXTRA_SOLIDS:
            self.rects.append(_rect(cx, cy + h / 2, w, h, 0))

        self.grid: dict[tuple[int, int], list[int]] = defaultdict(list)
        for index, rect in enumerate(self.rects):
            x0 = rect.left // self.CELL
            x1 = rect.right // self.CELL
            y0 = rect.top // self.CELL
            y1 = rect.bottom // self.CELL
            for gy in range(y0, y1 + 1):
                for gx in range(x0, x1 + 1):
                    self.grid[(gx, gy)].append(index)

    # ------------------------------------------------------------------
    def add_rect(self, rect: pygame.Rect) -> None:
        """Register a late-bound solid (NPC footprint) in the spatial hash."""
        index = len(self.rects)
        self.rects.append(rect)
        for gy in range(rect.top // self.CELL, rect.bottom // self.CELL + 1):
            for gx in range(rect.left // self.CELL, rect.right // self.CELL + 1):
                self.grid[(gx, gy)].append(index)

    # ------------------------------------------------------------------
    def nearby(self, rect: pygame.Rect) -> list[pygame.Rect]:
        found: set[int] = set()
        x0 = rect.left // self.CELL
        x1 = rect.right // self.CELL
        y0 = rect.top // self.CELL
        y1 = rect.bottom // self.CELL
        for gy in range(y0, y1 + 1):
            for gx in range(x0, x1 + 1):
                found.update(self.grid.get((gx, gy), ()))
        return [self.rects[i] for i in found]

    def move(
        self,
        x: float,
        y: float,
        dx: float,
        dy: float,
        half_w: float = 12.0,
        half_h: float = 9.0,
    ) -> tuple[float, float, bool, bool]:
        """Move a foot box, sliding along static geometry.

        Returns (x, y, hit_x, hit_y).  ``hit_*`` can be used for small dust
        puffs or to stop a footstep timer.
        """
        hit_x = hit_y = False
        w, h = int(round(half_w * 2)), int(round(half_h * 2))

        if dx:
            x += dx
            box = pygame.Rect(int(round(x - half_w)), int(round(y - half_h)), w, h)
            for solid in self.nearby(box):
                if box.colliderect(solid):
                    hit_x = True
                    if dx > 0:
                        x = solid.left - half_w - 0.01
                    else:
                        x = solid.right + half_w + 0.01
                    box.centerx = int(round(x))
        if dy:
            y += dy
            box = pygame.Rect(int(round(x - half_w)), int(round(y - half_h)), w, h)
            for solid in self.nearby(box):
                if box.colliderect(solid):
                    hit_y = True
                    if dy > 0:
                        y = solid.top - half_h - 0.01
                    else:
                        y = solid.bottom + half_h + 0.01
                    box.centery = int(round(y))
        return x, y, hit_x, hit_y

    # ------------------------------------------------------------------
    def segment_blocked(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        thickness: float = 2.0,
    ) -> bool:
        """Sample a world-space segment against solids (wall obstruction)."""
        dx = x2 - x1
        dy = y2 - y1
        distance = (dx * dx + dy * dy) ** 0.5
        if distance < 1.0:
            return False
        steps = max(1, int(distance / 7.0))
        for i in range(1, steps + 1):
            t = i / steps
            px = x1 + dx * t
            py = y1 + dy * t
            probe = pygame.Rect(
                int(round(px - thickness)), int(round(py - thickness)),
                max(2, int(round(thickness * 2))),
                max(2, int(round(thickness * 2))),
            )
            if any(probe.colliderect(solid) for solid in self.nearby(probe)):
                return True
        return False

    def rect_free(self, rect: pygame.Rect) -> bool:
        return not any(rect.colliderect(solid) for solid in self.nearby(rect))

    # ------------------------------------------------------------------
    def debug_draw(self, surface: pygame.Surface, offset: tuple[int, int]) -> None:
        ox, oy = offset
        for rect in self.rects:
            r = pygame.Rect(rect.x - ox, rect.y - oy, rect.w, rect.h)
            if r.right < -40 or r.left > surface.get_width() + 40:
                continue
            if r.bottom < -40 or r.top > surface.get_height() + 40:
                continue
            pygame.draw.rect(surface, (255, 62, 104), r, 1)
