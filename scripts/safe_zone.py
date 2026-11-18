"""Geometry helpers for the survivors' safe corner of Ashen Village.

The zone is authored in ``village_layout`` and reused by the spawner, the
combat manager and the interaction system.  Keeping the rule in one small
module means a fixed coordinate typo cannot make enemies appear inside the
hub after a later balance pass.
"""
from __future__ import annotations

import pygame

from scripts.village_layout import (
    SAFE_ZONE_X0,
    SAFE_ZONE_X1,
    SAFE_ZONE_Y0,
    SAFE_ZONE_Y1,
)


def contains(x: float, y: float, pad: float = 0.0) -> bool:
    """True when a point lies in the hub, optionally with a safety margin."""
    return (SAFE_ZONE_X0 - pad <= x <= SAFE_ZONE_X1 + pad
            and SAFE_ZONE_Y0 - pad <= y <= SAFE_ZONE_Y1 + pad)


def rect(x0: float, y0: float, x1: float, y1: float) -> pygame.Rect:
    return pygame.Rect(int(x0), int(y0), int(x1 - x0), int(y1 - y0))


def push_out(x: float, y: float, pad: float = 24.0) -> tuple[float, float]:
    """Return the nearest point just outside the padded safe zone."""
    if not contains(x, y, pad * 0.5):
        return x, y
    left = x - (SAFE_ZONE_X0 - pad)
    right = (SAFE_ZONE_X1 + pad) - x
    top = y - (SAFE_ZONE_Y0 - pad)
    bottom = (SAFE_ZONE_Y1 + pad) - y
    shortest = min(left, right, top, bottom)
    if shortest == left:
        return SAFE_ZONE_X0 - pad, y
    if shortest == right:
        return SAFE_ZONE_X1 + pad, y
    if shortest == top:
        return x, SAFE_ZONE_Y0 - pad
    return x, SAFE_ZONE_Y1 + pad


__all__ = ["contains", "push_out", "rect"]
