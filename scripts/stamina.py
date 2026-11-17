"""Delta-time stamina pool with a regeneration delay."""
from __future__ import annotations

from settings import STAMINA_REGEN, STAMINA_REGEN_DELAY


class Stamina:
    def __init__(
        self,
        maximum: float,
        regen: float = STAMINA_REGEN,
        delay: float = STAMINA_REGEN_DELAY,
        exhaust_recover: float = 24.0,
    ) -> None:
        self.maximum = float(maximum)
        self.current = float(maximum)
        self.regen = float(regen)
        self.delay = float(delay)
        self.exhaust_recover = float(exhaust_recover)
        self.delay_left = 0.0
        self.exhausted = False

    # ------------------------------------------------------------------
    def can(self, amount: float) -> bool:
        return self.current >= amount

    def spend(self, amount: float) -> bool:
        """Spend stamina if available.  Never returns a negative pool."""
        amount = max(0.0, amount)
        if self.current < amount:
            return False
        self.current = max(0.0, self.current - amount)
        self.delay_left = self.delay
        if self.current <= 0.0:
            self.exhausted = True
        return True

    def drain(self, amount: float) -> None:
        """Continuous drain (running); clamps at zero."""
        amount = max(0.0, amount)
        if amount <= 0.0:
            return
        self.current = max(0.0, self.current - amount)
        self.delay_left = self.delay
        if self.current <= 0.0:
            self.exhausted = True

    def update(self, dt: float) -> None:
        if self.delay_left > 0.0:
            self.delay_left = max(0.0, self.delay_left - dt)
        elif self.current < self.maximum:
            self.current = min(self.maximum, self.current + self.regen * dt)
        if self.exhausted and self.current >= self.exhaust_recover:
            self.exhausted = False

    def reset(self) -> None:
        self.current = self.maximum
        self.delay_left = 0.0
        self.exhausted = False

    @property
    def ratio(self) -> float:
        return 0.0 if self.maximum <= 0.0 else max(0.0, min(1.0, self.current / self.maximum))
