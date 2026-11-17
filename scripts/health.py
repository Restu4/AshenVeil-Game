"""Reusable health pool with clamping and death detection."""
from __future__ import annotations


class Health:
    def __init__(self, maximum: float, current: float | None = None) -> None:
        self.maximum = float(maximum)
        self.current = float(maximum if current is None else current)
        self.clamp()

    def clamp(self) -> None:
        self.current = max(0.0, min(self.maximum, self.current))

    def damage(self, amount: float) -> float:
        """Apply damage and return the amount actually lost."""
        if amount <= 0.0 or self.dead:
            return 0.0
        before = self.current
        self.current -= amount
        self.clamp()
        return before - self.current

    def heal(self, amount: float) -> float:
        if amount <= 0.0 or self.dead:
            return 0.0
        before = self.current
        self.current = min(self.maximum, self.current + amount)
        return self.current - before

    def reset(self) -> None:
        self.current = self.maximum

    @property
    def ratio(self) -> float:
        return 0.0 if self.maximum <= 0.0 else max(0.0, min(1.0, self.current / self.maximum))

    @property
    def dead(self) -> bool:
        return self.current <= 0.0
