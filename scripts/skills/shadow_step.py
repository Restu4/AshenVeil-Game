"""SHADOW STEP (E): a short collision-respecting dash through the Void.

Movement reuses the player's existing collision sweep through the new
``SHADOW_STEP`` combat state; this module only triggers it and lays down the
purple afterimage trail while the state is active.
"""
from __future__ import annotations

from scripts.skill_config import (
    SHADOW_TRAIL_INTERVAL,
)
from scripts.player_combat import SHADOW_STEP
from scripts.skills.base import ShadowStepSkill


class ShadowStep(ShadowStepSkill):
    def cast(self, manager) -> bool:
        if manager.player.combat.casting:
            return False
        if not self.can_use(manager):
            return False
        if not manager.player.combat.begin_shadow_step():
            return False
        if not self.commit(manager):
            return False

        player = manager.player
        combat = player.combat
        manager.skill_effects.spawn_afterimage(player)
        manager.skill_effects.spawn_shadow_puff(
            player.x, player.y, -combat.shadow_x, -combat.shadow_y
        )
        manager.camera.shake(1.2, 0.10)
        manager.shadow_trail = 0.0
        return True

    # ------------------------------------------------------------------
    def update_trail(self, manager, dt: float) -> None:
        player = manager.player
        if player.combat.state != SHADOW_STEP:
            manager.shadow_trail = 0.0
            return
        manager.shadow_trail -= dt
        if manager.shadow_trail > 0.0:
            return
        manager.shadow_trail = SHADOW_TRAIL_INTERVAL
        combat = player.combat
        manager.skill_effects.spawn_afterimage(player)
        manager.skill_effects.spawn_shadow_puff(
            player.x, player.y, -combat.shadow_x, -combat.shadow_y
        )
