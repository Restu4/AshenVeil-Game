"""Derived player statistics: base values plus equipment bonuses.

The numbers here are the *real* numbers the simulation reads.  Nothing is a
cosmetic display value: attack feeds hitboxes, defense feeds damage intake,
speed feeds movement, critical values feed CombatManager and the two pools feed
the health and void resources.
"""
from __future__ import annotations

from scripts.combat_config import (
    ATTACK_DAMAGE,
    CRIT_CHANCE,
    CRIT_MULTIPLIER,
    PLAYER_HEALTH_MAX,
)
from scripts.skill_config import VOID_ENERGY_MAX
from scripts.item_database import (
    STAT_IS_PERCENT,
    STAT_KEYS,
    STAT_LABELS,
    ItemDef,
)
from settings import PLAYER_WALK_SPEED

BASE_ATTACK = float(ATTACK_DAMAGE[0])
BASE_DEFENSE = 0.0
BASE_MAX_HP = float(PLAYER_HEALTH_MAX)
BASE_SPEED = float(PLAYER_WALK_SPEED)
BASE_CRIT_CHANCE = float(CRIT_CHANCE)
BASE_CRIT_DAMAGE = float(CRIT_MULTIPLIER)
BASE_MAX_VOID = float(VOID_ENERGY_MAX)

# Floor for damage after defense: even heavy armour cannot make the player
# immune, which keeps boss fights dangerous.
DEFENSE_DAMAGE_FLOOR = 0.18


class PlayerStats:
    """A recomputable snapshot of the equipped character."""

    __slots__ = ("level", "attack", "defense", "max_hp", "speed",
                 "crit_chance", "crit_damage", "max_void")

    def __init__(self, level: int = 7) -> None:
        self.level = max(1, min(99, int(level)))
        self.reset()

    def reset(self) -> None:
        """Restore untouched base statistics before equipment is applied."""
        self.attack = BASE_ATTACK
        self.defense = BASE_DEFENSE
        self.max_hp = BASE_MAX_HP
        self.speed = BASE_SPEED
        self.crit_chance = BASE_CRIT_CHANCE
        self.crit_damage = BASE_CRIT_DAMAGE
        self.max_void = BASE_MAX_VOID

    def apply(self, item: ItemDef) -> None:
        """Add one item's bonuses to the current snapshot."""
        for key, value in item.stats.items():
            if key in STAT_KEYS:
                setattr(self, key, getattr(self, key) + float(value))
        self.clamp()

    def clamp(self) -> None:
        self.level = max(1, min(99, int(self.level)))
        self.attack = max(0.0, self.attack)
        self.defense = max(0.0, self.defense)
        self.max_hp = max(1.0, self.max_hp)
        self.speed = max(20.0, min(600.0, self.speed))
        self.crit_chance = max(0.0, min(1.0, self.crit_chance))
        self.crit_damage = max(1.0, min(10.0, self.crit_damage))
        self.max_void = max(1.0, self.max_void)

    @property
    def attack_bonus(self) -> float:
        return self.attack - BASE_ATTACK

    @property
    def speed_bonus(self) -> float:
        return self.speed - BASE_SPEED

    def value(self, key: str) -> float:
        if key not in STAT_KEYS:
            return 0.0
        return float(getattr(self, key))

    def as_dict(self) -> dict[str, float]:
        return {key: self.value(key) for key in STAT_KEYS}

    def mitigation(self, amount: float) -> float:
        """Damage actually taken after flat armour, with a safety floor."""
        if amount <= 0.0:
            return 0.0
        reduced = max(amount * DEFENSE_DAMAGE_FLOOR, amount - self.defense)
        return max(0.0, reduced)


def format_stat(key: str, value: float, signed: bool = False) -> str:
    """Short, pixel-font safe representation of a stat value."""
    if key in STAT_IS_PERCENT:
        text = f"{int(round(value * 100))} PCT"
    else:
        text = str(int(round(value)))
    if signed and value > 0.0:
        text = "+" + text
    return text


def stat_label(key: str) -> str:
    return STAT_LABELS.get(key, key.upper())


def item_stat_lines(item: ItemDef) -> list[str]:
    """Ordered, formatted bonuses for an item definition."""
    lines: list[str] = []
    for key in STAT_KEYS:
        value = item.stats.get(key)
        if value:
            lines.append(f"{stat_label(key)} {format_stat(key, value, signed=True)}")
    if item.effect_text:
        lines.append(item.effect_text)
    return lines


def compare_stats(item: ItemDef, stats: PlayerStats) -> list[tuple[str, float]]:
    """Per-stat delta of ``item`` against the current equipped snapshot."""
    result: list[tuple[str, float]] = []
    for key in STAT_KEYS:
        value = item.stats.get(key, 0.0)
        if not value:
            continue
        delta = value - (stats.value(key) - _base_value(key))
        if abs(delta) > 1e-9:
            result.append((key, delta))
    return result


def _base_value(key: str) -> float:
    return {
        "attack": BASE_ATTACK,
        "defense": BASE_DEFENSE,
        "max_hp": BASE_MAX_HP,
        "speed": BASE_SPEED,
        "crit_chance": BASE_CRIT_CHANCE,
        "crit_damage": BASE_CRIT_DAMAGE,
        "max_void": BASE_MAX_VOID,
    }.get(key, 0.0)


__all__ = [
    "BASE_ATTACK", "BASE_CRIT_CHANCE", "BASE_CRIT_DAMAGE", "BASE_DEFENSE",
    "BASE_MAX_HP", "BASE_MAX_VOID", "BASE_SPEED", "DEFENSE_DAMAGE_FLOOR",
    "PlayerStats", "compare_stats", "format_stat", "item_stat_lines",
    "stat_label",
]
