"""Shared plumbing for VOID ESSENCE skills.

A skill owns only its cooldown timer.  Energy, damage resolution, effects and
camera feedback are delegated to the ``SkillManager`` / ``CombatManager`` so the
four skills stay small and independently tunable.
"""
from __future__ import annotations

from scripts.skill_config import (
    BURST_COST,
    BURST_COOLDOWN,
    BURST_KEY,
    BURST_NAME,
    ECLIPSE_COST,
    ECLIPSE_COOLDOWN,
    ECLIPSE_KEY,
    ECLIPSE_NAME,
    SHADOW_COST,
    SHADOW_COOLDOWN,
    SHADOW_KEY,
    SHADOW_NAME,
    SLASH_COST,
    SLASH_COOLDOWN,
    SLASH_KEY,
    SLASH_NAME,
)


class Skill:
    """Base class: identity, cost, cooldown and availability."""

    name = "SKILL"
    key = "?"
    cost = 0.0
    cooldown = 0.0
    icon = "burst"

    def __init__(self) -> None:
        self.timer = 0.0

    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        if dt > 0.0 and self.timer > 0.0:
            self.timer = max(0.0, self.timer - dt)

    @property
    def ready(self) -> bool:
        return self.timer <= 0.0

    @property
    def cooldown_ratio(self) -> float:
        """1.0 when ready, falling to 0.0 as the cooldown expires."""
        if self.cooldown <= 0.0:
            return 1.0
        return max(0.0, min(1.0, 1.0 - self.timer / self.cooldown))

    @property
    def cooldown_left(self) -> float:
        return max(0.0, self.timer)

    # ------------------------------------------------------------------
    def can_use(self, manager) -> bool:
        return (
            self.ready
            and manager.player.combat.can_cast_skill
            and manager.energy.can_afford(self.cost)
        )

    def commit(self, manager) -> bool:
        if not manager.energy.spend(self.cost):
            return False
        self.timer = self.cooldown
        return True

    def cast(self, manager) -> bool:      # pragma: no cover - abstract
        raise NotImplementedError

    def reset(self) -> None:
        self.timer = 0.0


class VoidBurstSkill(Skill):
    name = BURST_NAME
    key = BURST_KEY
    cost = BURST_COST
    cooldown = BURST_COOLDOWN
    icon = "burst"


class ShadowStepSkill(Skill):
    name = SHADOW_NAME
    key = SHADOW_KEY
    cost = SHADOW_COST
    cooldown = SHADOW_COOLDOWN
    icon = "shadow"


class VoidSlashSkill(Skill):
    name = SLASH_NAME
    key = SLASH_KEY
    cost = SLASH_COST
    cooldown = SLASH_COOLDOWN
    icon = "slash"


class EclipseSkill(Skill):
    name = ECLIPSE_NAME
    key = ECLIPSE_KEY
    cost = ECLIPSE_COST
    cooldown = ECLIPSE_COOLDOWN
    icon = "eclipse"
