"""Void Energy: the dark-magic resource, independent of health.

The pool is deliberately tiny and explicit.  Every mutation is clamped so the
bar can never underflow or overflow, and regeneration is delta-time driven.
"""
from __future__ import annotations

from scripts.skill_config import (
    VOID_ENERGY_MAX,
    VOID_ENERGY_START,
    VOID_KILL_REWARD,
    VOID_REGEN_PER_SEC,
)


class VoidEnergy:
    def __init__(
        self,
        maximum: float = VOID_ENERGY_MAX,
        current: float = VOID_ENERGY_START,
        regen: float = VOID_REGEN_PER_SEC,
    ) -> None:
        self.maximum = float(maximum)
        self.current = float(current)
        self.regen = float(regen)
        self.clamp()

    # ------------------------------------------------------------------
    def clamp(self) -> None:
        self.current = max(0.0, min(self.maximum, self.current))

    def update(self, dt: float) -> None:
        if dt <= 0.0:
            return
        if self.current < self.maximum and self.regen > 0.0:
            self.current = min(self.maximum, self.current + self.regen * dt)

    # ------------------------------------------------------------------
    def can_afford(self, cost: float) -> bool:
        return cost <= 0.0 or self.current + 1e-6 >= cost

    def spend(self, cost: float) -> bool:
        cost = max(0.0, float(cost))
        if not self.can_afford(cost):
            return False
        self.current = max(0.0, self.current - cost)
        return True

    def gain(self, amount: float) -> float:
        amount = max(0.0, float(amount))
        if amount <= 0.0:
            return 0.0
        before = self.current
        self.current = min(self.maximum, self.current + amount)
        return self.current - before

    def reward_kill(self) -> float:
        return self.gain(VOID_KILL_REWARD)

    def reset(self) -> None:
        self.current = min(self.maximum, VOID_ENERGY_START)
        self.clamp()

    # ------------------------------------------------------------------
    @property
    def ratio(self) -> float:
        if self.maximum <= 0.0:
            return 0.0
        return max(0.0, min(1.0, self.current / self.maximum))

    @property
    def empty(self) -> bool:
        return self.current <= 0.0

    @property
    def full(self) -> bool:
        return self.current >= self.maximum - 1e-6
