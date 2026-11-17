"""World-space attack volumes and hit-resolution helpers."""
from __future__ import annotations

import pygame

from scripts.combat_config import ATTACK_REACH, ATTACK_WIDTH

FACING_VECTORS = {
    "down": (0.0, 1.0),
    "up": (0.0, -1.0),
    "left": (-1.0, 0.0),
    "right": (1.0, 0.0),
}


class AttackHitbox:
    """A single sweeping AABB ahead of an actor."""

    __slots__ = ("rect", "damage", "knockback", "heavy", "attack_id", "owner")

    def __init__(
        self,
        x: float,
        y: float,
        facing: str,
        damage: float,
        knockback: float,
        heavy: bool,
        attack_id: int,
        owner,
        reach: float = ATTACK_REACH,
        width: float = ATTACK_WIDTH,
    ) -> None:
        vx, vy = FACING_VECTORS.get(facing, (0.0, 1.0))
        cx = x + vx * (reach * 0.5 + 8.0)
        cy = y + vy * (reach * 0.5 + 2.0) - 8.0
        w = reach if abs(vx) else width
        h = reach if abs(vy) else width
        self.rect = pygame.Rect(
            int(round(cx - w / 2)), int(round(cy - h / 2)),
            int(round(w)), int(round(h)),
        )
        self.damage = float(damage)
        self.knockback = float(knockback)
        self.heavy = bool(heavy)
        self.attack_id = int(attack_id)
        self.owner = owner

    def collides(self, other: pygame.Rect) -> bool:
        return self.rect.colliderect(other)
