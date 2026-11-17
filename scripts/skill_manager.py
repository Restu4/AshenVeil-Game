"""VOID ESSENCE orchestration: energy, cooldowns, waves and kill rewards.

``main.py`` owns one ``SkillManager``.  It is also the bridge between the four
skills and the existing combat manager: all damage still resolves through
``CombatManager`` so damage numbers, knockback, enemy bars, deaths and rewards
behave exactly like sword hits.
"""
from __future__ import annotations

import pygame

from scripts.skill_config import (
    ECLIPSE_KEY,
    SHADOW_KEY,
    SLASH_KEY,
    BURST_KEY,
)
from scripts.skill_effects import SkillEffects
from scripts.skills import Eclipse, ShadowStep, VoidBurst, VoidSlash
from scripts.void_energy import VoidEnergy


class SkillManager:
    def __init__(self, player, combat, camera) -> None:
        self.player = player
        self.combat = combat
        self.camera = camera
        self.energy = VoidEnergy()
        self.skill_effects = SkillEffects()

        self.burst = VoidBurst()
        self.shadow = ShadowStep()
        self.slash = VoidSlash()
        self.eclipse = Eclipse()
        self.skills = (self.burst, self.shadow, self.slash, self.eclipse)
        self._by_key = {
            BURST_KEY: self.burst,
            SHADOW_KEY: self.shadow,
            SLASH_KEY: self.slash,
            ECLIPSE_KEY: self.eclipse,
        }

        self.shadow_trail = 0.0
        # Any enemy death - sword or magic - feeds the Void pool.
        self.combat.on_kill = self.on_enemy_killed

    # ------------------------------------------------------------------
    # Casting
    # ------------------------------------------------------------------
    def try_cast(self, key: str) -> bool:
        skill = self._by_key.get(key.upper())
        if skill is None:
            return False
        return skill.cast(self)

    def cast_burst(self) -> bool:
        return self.burst.cast(self)

    def cast_shadow(self) -> bool:
        return self.shadow.cast(self)

    def cast_slash(self) -> bool:
        return self.slash.cast(self)

    def cast_eclipse(self) -> bool:
        return self.eclipse.cast(self)

    # ------------------------------------------------------------------
    def on_enemy_killed(self, _enemy=None) -> None:
        self.energy.reward_kill()

    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        dt = max(0.0, dt)
        self.energy.update(dt)
        for skill in self.skills:
            skill.update(dt)
        self.shadow.update_trail(self, dt)
        self.slash.update_waves(self, dt)
        self.eclipse.update_cast(self, dt)
        self.skill_effects.update(dt)

    # ------------------------------------------------------------------
    def draw_world(self, target: pygame.Surface, camera) -> None:
        for wave in self.slash.waves:
            self.skill_effects.draw_wave(
                target,
                camera,
                wave["x"],
                wave["y"],
                wave["dx"],
                wave["dy"],
                wave["travel"],
            )
        self.skill_effects.draw_world(target, camera)

    def draw_overlay(self, target: pygame.Surface) -> None:
        self.skill_effects.draw_overlay(target)

    # ------------------------------------------------------------------
    def reset(self) -> None:
        self.energy.reset()
        for skill in self.skills:
            skill.reset()
        self.shadow_trail = 0.0
        self.skill_effects.clear()

    def clear_effects(self) -> None:
        self.skill_effects.clear()
        self.slash.waves.clear()
        self.shadow_trail = 0.0
