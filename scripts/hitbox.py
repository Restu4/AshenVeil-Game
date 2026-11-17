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
    """A single sweeping AABB ahead of an actor (or a spin around it).

    ``shape="arc"`` sweeps forward from the actor; ``shape="spin"`` covers a
    square area centred on the actor, which is how the heavy combo links hit
    several enemies at once.  Collision stays rectangle-based so the hot path
    stays cheap in the browser.
    """

    __slots__ = ("rect", "damage", "knockback", "heavy", "attack_id", "owner",
                 "stage", "shape", "knock_x", "knock_y")

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
        shape: str = "arc",
        stage: int = 1,
    ) -> None:
        vx, vy = FACING_VECTORS.get(facing, (0.0, 1.0))
        if shape == "spin":
            size = int(round(reach * 2))
            self.rect = pygame.Rect(
                int(round(x - size / 2)),
                int(round(y - size / 2 - 8)),
                size,
                size,
            )
        else:
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
        self.stage = int(stage)
        self.shape = shape
        self.knock_x = vx
        self.knock_y = vy

    def collides(self, other: pygame.Rect) -> bool:
        return self.rect.colliderect(other)
