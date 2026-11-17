"""ECLIPSE (F): the Void Essence ultimate.

Casting locks the player into a short wind-up.  The detonation is owned by this
object so the ultimate can never fire twice while one is already gathering.
"""
from __future__ import annotations

from scripts.skill_config import (
    ECLIPSE_COST,
    ECLIPSE_DAMAGE,
    ECLIPSE_HIT_STOP,
    ECLIPSE_KNOCKBACK,
    ECLIPSE_RADIUS,
    ECLIPSE_SHAKE,
    ECLIPSE_WINDUP,
)
from scripts.skills.base import EclipseSkill


def eclipse_radius(manager) -> float:
    mods = getattr(manager, "mods", None)
    return ECLIPSE_RADIUS * (mods.eclipse_radius if mods is not None else 1.0)


def eclipse_damage(manager) -> float:
    mods = getattr(manager, "mods", None)
    if mods is None:
        return ECLIPSE_DAMAGE
    return ECLIPSE_DAMAGE * mods.eclipse_damage * mods.void_power


class Eclipse(EclipseSkill):
    def __init__(self) -> None:
        super().__init__()
        self.pending: dict | None = None
        self._mote_timer = 0.0

    # ------------------------------------------------------------------
    @property
    def charging(self) -> bool:
        return self.pending is not None

    @property
    def windup_ratio(self) -> float:
        if self.pending is None:
            return 0.0
        return max(0.0, min(1.0, 1.0 - self.pending["timer"] / ECLIPSE_WINDUP))

    # ------------------------------------------------------------------
    def cast(self, manager) -> bool:
        if self.pending is not None:
            return False
        if not self.can_use(manager):
            return False
        if not self.commit(manager):
            return False

        player = manager.player
        player.combat.begin_cast(ECLIPSE_WINDUP + 0.05)
        x, y = player.x, player.y
        self.pending = {"x": x, "y": y, "timer": ECLIPSE_WINDUP, "hit": set()}
        self._mote_timer = 0.0
        manager.skill_effects.begin_eclipse(
            x, y, ECLIPSE_WINDUP, eclipse_radius(manager)
        )
        manager.camera.shake(2.0, 0.12)
        return True

    # ------------------------------------------------------------------
    def update_cast(self, manager, dt: float) -> None:
        if self.pending is None or dt <= 0.0:
            return
        pending = self.pending
        pending["timer"] -= dt
        self._mote_timer -= dt
        if self._mote_timer <= 0.0:
            self._mote_timer = 0.045
            manager.skill_effects.spawn_eclipse_mote(
                pending["x"], pending["y"], eclipse_radius(manager)
            )
        if pending["timer"] > 0.0:
            return

        x, y = pending["x"], pending["y"]
        self.pending = None
        manager.combat.damage_area(
            x,
            y,
            eclipse_radius(manager),
            eclipse_damage(manager),
            ECLIPSE_KNOCKBACK,
            heavy=True,
        )
        manager.combat.add_hit_stop(ECLIPSE_HIT_STOP)
        manager.skill_effects.detonate_eclipse(x, y, eclipse_radius(manager))
        manager.camera.shake(ECLIPSE_SHAKE, 0.30)
        manager.combat.effects.spawn_flash((22, 12, 38), 0.18)

    # ------------------------------------------------------------------
    def reset(self) -> None:
        super().reset()
        self.pending = None
        self._mote_timer = 0.0
