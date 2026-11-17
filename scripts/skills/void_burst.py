"""VOID BURST (Q): a radial dark-purple detonation around the player.

The skill is instant.  ``CombatManager.damage_area`` resolves exactly one hit
per enemy for this cast; the visuals live in ``SkillEffects``.
"""
from __future__ import annotations

from scripts.skill_config import (
    BURST_CAST_LOCK,
    BURST_DAMAGE,
    BURST_HIT_STOP,
    BURST_KNOCKBACK,
    BURST_RADIUS,
    BURST_SHAKE,
)
from scripts.skills.base import VoidBurstSkill


def burst_damage(manager) -> float:
    mods = getattr(manager, "mods", None)
    if mods is None:
        return BURST_DAMAGE
    return BURST_DAMAGE * mods.burst_damage * mods.void_power


class VoidBurst(VoidBurstSkill):
    def cast(self, manager) -> bool:
        if not self.can_use(manager):
            return False
        if not self.commit(manager):
            return False

        player = manager.player
        player.combat.begin_cast(BURST_CAST_LOCK)

        x, y = player.x, player.y
        manager.combat.damage_area(
            x,
            y,
            BURST_RADIUS,
            burst_damage(manager),
            BURST_KNOCKBACK,
            heavy=False,
        )
        manager.combat.add_hit_stop(BURST_HIT_STOP)
        manager.skill_effects.spawn_burst(x, y, BURST_RADIUS)
        manager.camera.shake(BURST_SHAKE, 0.12)
        manager.combat.effects.spawn_flash((28, 14, 46), 0.08)
        return True
