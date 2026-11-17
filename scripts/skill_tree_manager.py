"""Controller for the Void skill tree.

The tree never owns progression state: points and purchased node IDs live in
``ExpManager`` so one save field is authoritative.  This class validates
unlocks, applies purchases and exposes the exact effect values to the existing
skills through ``SkillModifiers``.
"""
from __future__ import annotations

from scripts.skill_config import BURST_KEY, ECLIPSE_KEY, SHADOW_KEY, SLASH_KEY
from scripts.skill_modifiers import compute_modifiers
from scripts.skill_tree_config import NODES, NODES_BY_ID, VALID_NODE_IDS

LOCKED = "LOCKED"
AVAILABLE = "AVAILABLE"
OWNED = "OWNED"


class SkillTreeManager:
    def __init__(self, exp_manager) -> None:
        self.exp = exp_manager

    # ------------------------------------------------------------------
    @property
    def points(self) -> int:
        return max(0, int(self.exp.skill_points))

    @property
    def purchased(self) -> set[str]:
        return self.exp.purchased_nodes

    def node(self, node_id: str):
        return NODES_BY_ID.get(str(node_id))

    def state(self, node_id: str) -> str:
        node = NODES_BY_ID.get(str(node_id))
        if node is None:
            return LOCKED
        if node.node_id in self.purchased:
            return OWNED
        if self.exp.level < node.level_req:
            return LOCKED
        if any(required not in self.purchased for required in node.requires):
            return LOCKED
        return AVAILABLE

    def reason(self, node_id: str) -> str:
        """Short pixel-font-safe reason shown on unavailable cards."""
        node = NODES_BY_ID.get(str(node_id))
        if node is None:
            return "UNKNOWN NODE"
        if node.node_id in self.purchased:
            return "ALREADY OWNED"
        if self.exp.level < node.level_req:
            return f"LEVEL {node.level_req} REQUIRED"
        missing = [req for req in node.requires if req not in self.purchased]
        if missing:
            first = NODES_BY_ID.get(missing[0])
            name = first.name if first is not None else missing[0].upper()
            return f"REQUIRES {name}"
        if self.points <= 0:
            return "NO SKILL POINTS"
        return "CLICK TO UNLOCK"

    def can_purchase(self, node_id: str) -> tuple[bool, str]:
        node = NODES_BY_ID.get(str(node_id))
        if node is None:
            return False, "UNKNOWN NODE"
        if node.node_id in self.purchased:
            return False, "ALREADY OWNED"
        if self.exp.level < node.level_req:
            return False, f"LEVEL {node.level_req} REQUIRED"
        missing = [req for req in node.requires if req not in self.purchased]
        if missing:
            return False, "PREREQUISITE LOCKED"
        if self.points < node.cost:
            return False, "NO SKILL POINTS"
        return True, ""

    def purchase(self, node_id: str) -> tuple[bool, str]:
        ok, reason = self.can_purchase(node_id)
        if not ok:
            return False, reason
        node = NODES_BY_ID[str(node_id)]
        if not self.exp.spend_skill_point():
            return False, "NO SKILL POINTS"
        self.purchased.add(node.node_id)
        self.exp.notify_change()
        return True, f"{node.name} UNLOCKED"

    def has(self, node_id: str) -> bool:
        return str(node_id) in self.purchased

    # ------------------------------------------------------------------
    def modifiers(self):
        """Recompute the effective skill numbers from current progression."""
        return compute_modifiers(self.exp.attributes, self.purchased)

    def apply(self, skills=None, combat=None, player=None) -> None:
        """Push all derived values into the live systems (single authority)."""
        mods = self.modifiers()
        if skills is not None:
            skills.mods = mods
            energy = getattr(skills, "energy", None)
            if energy is not None:
                from scripts.skill_config import VOID_REGEN_PER_SEC
                energy.regen = VOID_REGEN_PER_SEC * mods.void_regen
        if combat is not None:
            stats = getattr(player, "stats", None) if player is not None else None
            base_crit = getattr(stats, "crit_damage", None)
            if base_crit is not None:
                combat.crit_multiplier = float(base_crit) * mods.crit_damage
            combat.elite_damage_mult = mods.elite_damage
        if player is not None:
            entity_combat = getattr(player, "combat", None)
            if entity_combat is not None:
                entity_combat.shadow_speed_mult = mods.shadow_distance
                entity_combat.dodge_duration_mult = mods.dodge_recovery
                entity_combat.shadow_duration_mult = 1.0
                entity_combat.speed_surge_mult = mods.dodge_surge
        return mods

    # ------------------------------------------------------------------
    @property
    def summary(self) -> list[tuple[str, str]]:
        """Key-to-skill hint used by the tree screen header."""
        return [
            (BURST_KEY, "BURST"),
            (SHADOW_KEY, "STEP"),
            (SLASH_KEY, "SLASH"),
            (ECLIPSE_KEY, "ECLIPSE"),
        ]


__all__ = [
    "AVAILABLE", "LOCKED", "OWNED", "SkillTreeManager",
]
