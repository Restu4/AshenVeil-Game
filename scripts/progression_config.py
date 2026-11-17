"""Central tuning for Phase 7 character progression.

Every gameplay-facing progression value lives here: the EXP curve, kill and
quest rewards, attribute scaling, level-up grants and enemy reward tiers.
This module deliberately imports no game systems, so the save layer, managers
and UI can all read it without circular imports.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Character level
# ---------------------------------------------------------------------------
START_LEVEL = 1
MAX_LEVEL = 30
ATTRIBUTE_POINTS_PER_LEVEL = 3
SKILL_POINT_INTERVAL = 2          # one skill point every N levels
MAX_ATTRIBUTE_RANK = 10           # per-attribute safety cap

EXP_BASE = 60.0
EXP_GROWTH = 1.13

# ---------------------------------------------------------------------------
# Rewards
# ---------------------------------------------------------------------------
EXP_REWARDS = {
    "regular": 20,
    "strong": 40,
    "elite": 100,
    "boss": 500,
}
QUEST_EXP_DEFAULT = 0

# ---------------------------------------------------------------------------
# Attributes: 3 free points per level, real gameplay effects
# ---------------------------------------------------------------------------
ATTRIBUTE_KEYS = ("str", "vit", "agi", "int")
ATTRIBUTE_LABELS = {
    "str": "STRENGTH",
    "vit": "VITALITY",
    "agi": "AGILITY",
    "int": "INTELLIGENCE",
}
ATTRIBUTE_EFFECTS = {
    "str": "+2 ATTACK DAMAGE",
    "vit": "+12 MAXIMUM HP",
    "agi": "+2 SPEED +1 PCT CRIT",
    "int": "+4 VOID +2 PCT VOID POWER",
}

STR_ATTACK_PER_POINT = 2.0
VIT_HP_PER_POINT = 12.0
AGI_SPEED_PER_POINT = 2.0
AGI_CRIT_PER_POINT = 0.01
INT_VOID_PER_POINT = 4.0
INT_VOID_POWER_PER_POINT = 0.02

# ---------------------------------------------------------------------------
# Anti-farming / level-up feedback
# ---------------------------------------------------------------------------
MAX_DEFEATED_KEYS = 4000
LEVEL_UP_HIT_STOP = 0.12
LEVEL_UP_SURGE_TIME = 1.5
LEVEL_UP_SURGE_MULT = 0.20


def exp_for_level(level: int) -> int:
    """EXP required to advance from ``level`` to ``level + 1``."""
    level = max(START_LEVEL, min(MAX_LEVEL, int(level)))
    return max(1, int(round(EXP_BASE * (EXP_GROWTH ** (level - 1)))))


def attribute_points_for_level(level: int) -> int:
    """Total attribute points granted by reaching ``level``."""
    return max(0, (int(level) - START_LEVEL) * ATTRIBUTE_POINTS_PER_LEVEL)


def skill_points_for_level(level: int) -> int:
    """Total skill points granted by reaching ``level``."""
    if SKILL_POINT_INTERVAL <= 0:
        return 0
    return max(0, (int(level) - START_LEVEL) // SKILL_POINT_INTERVAL)


def enemy_tier(enemy) -> str:
    """Classify an enemy for EXP rewards, reusing the existing boss marker."""
    if getattr(enemy, "is_boss", False):
        return "boss"
    key = str(getattr(enemy, "key", "")).lower()
    subtitle = str(getattr(enemy, "subtitle", "")).upper()
    if key == "corrupted_warden" or "ELITE" in subtitle:
        return "elite"
    if key == "fallen_knight":
        return "strong"
    return "regular"


def exp_for_enemy(enemy) -> int:
    """Configured EXP reward for one defeated enemy."""
    return int(EXP_REWARDS.get(enemy_tier(enemy), EXP_REWARDS["regular"]))


def defeated_key(enemy, level_id: str = "") -> str:
    """Stable per-profile key so reload/re-entry cannot re-award an enemy."""
    prefix = str(level_id or "run")
    if getattr(enemy, "is_boss", False):
        return f"{prefix}:boss"
    try:
        enemy_id = int(getattr(enemy, "id", -1))
    except (TypeError, ValueError):
        enemy_id = -1
    return f"{prefix}:{enemy_id}"


def clamp_int(value, low: int, high: int, fallback: int = 0) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError, OverflowError):
        number = fallback
    return max(low, min(high, number))


__all__ = [
    "AGI_CRIT_PER_POINT", "AGI_SPEED_PER_POINT", "ATTRIBUTE_EFFECTS",
    "ATTRIBUTE_KEYS", "ATTRIBUTE_LABELS", "ATTRIBUTE_POINTS_PER_LEVEL",
    "EXP_BASE", "EXP_GROWTH", "EXP_REWARDS", "INT_VOID_PER_POINT",
    "INT_VOID_POWER_PER_POINT", "LEVEL_UP_HIT_STOP", "LEVEL_UP_SURGE_MULT",
    "LEVEL_UP_SURGE_TIME", "MAX_ATTRIBUTE_RANK", "MAX_DEFEATED_KEYS",
    "MAX_LEVEL", "QUEST_EXP_DEFAULT", "SKILL_POINT_INTERVAL",
    "START_LEVEL", "STR_ATTACK_PER_POINT", "VIT_HP_PER_POINT",
    "attribute_points_for_level", "clamp_int", "defeated_key",
    "enemy_tier", "exp_for_enemy", "exp_for_level",
    "skill_points_for_level",
]
