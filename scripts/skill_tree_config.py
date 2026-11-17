"""Small, balanced Void skill tree: three branches, four nodes each.

Nodes never create new active abilities.  Each one only changes a value used by
the existing Q/E/R/F skills, by movement or by the Void resource.  All effect
text is uppercase and limited to glyphs in the project bitmap font.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SkillNode:
    node_id: str
    branch: str
    name: str
    effect: str
    level_req: int
    requires: tuple[str, ...]
    modifier: str
    value: float
    cost: int = 1


BRANCHES = (
    ("A", "VOID OFFENSE", (150, 96, 226)),
    ("B", "SHADOW MOBILITY", (96, 174, 198)),
    ("C", "ECLIPSE MASTERY", (206, 148, 92)),
)

NODES: tuple[SkillNode, ...] = (
    # -- Branch A: Void Offense -----------------------------------------
    SkillNode(
        "a1", "A", "BURST AMPLIFY",
        "VOID BURST DEALS 30 PCT MORE DAMAGE",
        2, (), "burst_damage", 1.30,
    ),
    SkillNode(
        "a2", "A", "SLASH AMPLIFY",
        "VOID SLASH DEALS 30 PCT MORE DAMAGE",
        3, (), "slash_damage", 1.30,
    ),
    SkillNode(
        "a3", "A", "CRITICAL EDGE",
        "CRITICAL HITS DEAL 25 PCT MORE DAMAGE",
        6, ("a1",), "crit_damage", 1.25,
    ),
    SkillNode(
        "a4", "A", "ELITE HUNTER",
        "DEAL 25 PCT MORE DAMAGE TO ELITES",
        10, ("a2",), "elite_damage", 1.25,
    ),
    # -- Branch B: Shadow Mobility --------------------------------------
    SkillNode(
        "b1", "B", "FLEET SHADOW",
        "SHADOW STEP COOLDOWN REDUCED 25 PCT",
        2, (), "shadow_cooldown", 0.75,
    ),
    SkillNode(
        "b2", "B", "LONG SHADOW",
        "SHADOW STEP TRAVEL INCREASED 30 PCT",
        4, ("b1",), "shadow_distance", 1.30,
    ),
    SkillNode(
        "b3", "B", "QUICK RECOVERY",
        "DODGE RECOVERY IS 20 PCT FASTER",
        5, ("b1",), "dodge_recovery", 0.80,
    ),
    SkillNode(
        "b4", "B", "DODGE SURGE",
        "MOVE 20 PCT FASTER FOR 1.5 SEC AFTER DODGE",
        8, ("b3",), "dodge_surge", 0.20,
    ),
    # -- Branch C: Eclipse Mastery --------------------------------------
    SkillNode(
        "c1", "C", "ECLIPSE WRATH",
        "ECLIPSE DEALS 30 PCT MORE DAMAGE",
        3, (), "eclipse_damage", 1.30,
    ),
    SkillNode(
        "c2", "C", "WIDENING ECLIPSE",
        "ECLIPSE RADIUS INCREASED 25 PCT",
        5, ("c1",), "eclipse_radius", 1.25,
    ),
    SkillNode(
        "c3", "C", "VOID WELL",
        "VOID ENERGY REGENERATION INCREASED 50 PCT",
        6, ("c1",), "void_regen", 1.50,
    ),
    SkillNode(
        "c4", "C", "EFFICIENT CASTING",
        "ALL SKILL ENERGY COSTS REDUCED 20 PCT",
        9, ("c3",), "skill_cost", 0.80,
    ),
)

NODES_BY_ID: dict[str, SkillNode] = {node.node_id: node for node in NODES}
VALID_NODE_IDS: frozenset[str] = frozenset(NODES_BY_ID)


def nodes_for_branch(branch: str) -> tuple[SkillNode, ...]:
    return tuple(node for node in NODES if node.branch == branch)


__all__ = [
    "BRANCHES", "NODES", "NODES_BY_ID", "VALID_NODE_IDS", "SkillNode",
    "nodes_for_branch",
]
