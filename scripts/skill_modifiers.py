"""Computed multipliers applied to the existing Void skills and movement.

The items in this object are the *only* bridge between progression and the
four abilities.  Skills keep their own state machines; they simply read the
effective numbers here instead of importing fixed constants.
"""
from __future__ import annotations

from dataclasses import dataclass

from scripts.progression_config import INT_VOID_POWER_PER_POINT
from scripts.skill_config import SHADOW_KEY
from scripts.skill_tree_config import NODES_BY_ID


@dataclass
class SkillModifiers:
    burst_damage: float = 1.0
    slash_damage: float = 1.0
    crit_damage: float = 1.0
    elite_damage: float = 1.0
    shadow_cooldown: float = 1.0
    shadow_distance: float = 1.0
    dodge_recovery: float = 1.0
    dodge_surge: float = 0.0
    eclipse_damage: float = 1.0
    eclipse_radius: float = 1.0
    void_regen: float = 1.0
    skill_cost: float = 1.0
    void_power: float = 1.0

    def cooldown_mult(self, key: str) -> float:
        if str(key).upper() == SHADOW_KEY:
            return max(0.1, self.shadow_cooldown)
        return 1.0

    def cost_mult(self) -> float:
        return max(0.1, self.skill_cost)


def compute_modifiers(attributes: dict | None = None,
                      purchased: set[str] | frozenset[str] | None = None
                      ) -> SkillModifiers:
    """Fold attributes and purchased nodes into one immutable snapshot."""
    mods = SkillModifiers()
    intel = 0
    if isinstance(attributes, dict):
        try:
            intel = max(0, int(attributes.get("int", 0)))
        except (TypeError, ValueError, OverflowError):
            intel = 0
    mods.void_power = 1.0 + intel * INT_VOID_POWER_PER_POINT

    if purchased:
        for node_id in purchased:
            node = NODES_BY_ID.get(str(node_id))
            if node is None:
                continue
            current = getattr(mods, node.modifier)
            if node.modifier == "dodge_surge":
                setattr(mods, node.modifier, current + float(node.value))
            else:
                setattr(mods, node.modifier, current * float(node.value))
    return mods


__all__ = ["SkillModifiers", "compute_modifiers"]
