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
from scripts.progression_config import (
    AGI_CRIT_PER_POINT,
    AGI_SPEED_PER_POINT,
    ATTRIBUTE_KEYS,
    INT_VOID_PER_POINT,
    INT_VOID_POWER_PER_POINT,
    MAX_ATTRIBUTE_RANK,
    MAX_LEVEL,
    START_LEVEL,
    STR_ATTACK_PER_POINT,
    VIT_HP_PER_POINT,
    clamp_int,
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
                 "crit_chance", "crit_damage", "max_void", "attributes",
                 "void_power")

    def __init__(self, level: int = START_LEVEL) -> None:
        self.level = max(START_LEVEL, min(MAX_LEVEL, int(level)))
        self.attributes: dict[str, int] = {key: 0 for key in ATTRIBUTE_KEYS}
        self.void_power = 1.0
        self.reset()

    def reset(self) -> None:
        """Restore base statistics plus attributes, before equipment is added."""
        strength = self.attributes.get("str", 0)
        vitality = self.attributes.get("vit", 0)
        agility = self.attributes.get("agi", 0)
        intellect = self.attributes.get("int", 0)

        self.attack = BASE_ATTACK + strength * STR_ATTACK_PER_POINT
        self.defense = BASE_DEFENSE
        self.max_hp = BASE_MAX_HP + vitality * VIT_HP_PER_POINT
        self.speed = BASE_SPEED + agility * AGI_SPEED_PER_POINT
        self.crit_chance = BASE_CRIT_CHANCE + agility * AGI_CRIT_PER_POINT
        self.crit_damage = BASE_CRIT_DAMAGE
        self.max_void = BASE_MAX_VOID + intellect * INT_VOID_PER_POINT
        self.void_power = 1.0 + intellect * INT_VOID_POWER_PER_POINT

    def set_attributes(self, values: dict | None) -> None:
        """Replace allocated attributes, then let the caller recompute gear."""
        for key in ATTRIBUTE_KEYS:
            raw = values.get(key, 0) if isinstance(values, dict) else 0
            self.attributes[key] = clamp_int(
                raw, 0, MAX_ATTRIBUTE_RANK, 0
            )
        self.reset()
        self.clamp()

    def apply(self, item: ItemDef) -> None:
        """Add one item's bonuses to the current snapshot."""
        for key, value in item.stats.items():
            if key in STAT_KEYS:
                setattr(self, key, getattr(self, key) + float(value))
        self.clamp()

    def clamp(self) -> None:
        self.level = max(START_LEVEL, min(MAX_LEVEL, int(self.level)))
        self.attack = max(0.0, self.attack)
        self.defense = max(0.0, self.defense)
        self.max_hp = max(1.0, self.max_hp)
        self.speed = max(20.0, min(600.0, self.speed))
        self.crit_chance = max(0.0, min(1.0, self.crit_chance))
        self.crit_damage = max(1.0, min(10.0, self.crit_damage))
        self.max_void = max(1.0, self.max_void)
        self.void_power = max(1.0, min(10.0, self.void_power))

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
        delta = value - (stats.value(key) - _base_value(key, stats))
        if abs(delta) > 1e-9:
            result.append((key, delta))
    return result


def _base_value(key: str, stats: "PlayerStats | None" = None) -> float:
    base = {
        "attack": BASE_ATTACK,
        "defense": BASE_DEFENSE,
        "max_hp": BASE_MAX_HP,
        "speed": BASE_SPEED,
        "crit_chance": BASE_CRIT_CHANCE,
        "crit_damage": BASE_CRIT_DAMAGE,
        "max_void": BASE_MAX_VOID,
    }.get(key, 0.0)
    attrs = stats.attributes if stats is not None else None
    if not isinstance(attrs, dict):
        return base
    if key == "attack":
        return base + attrs.get("str", 0) * STR_ATTACK_PER_POINT
    if key == "max_hp":
        return base + attrs.get("vit", 0) * VIT_HP_PER_POINT
    if key == "speed":
        return base + attrs.get("agi", 0) * AGI_SPEED_PER_POINT
    if key == "crit_chance":
        return base + attrs.get("agi", 0) * AGI_CRIT_PER_POINT
    if key == "max_void":
        return base + attrs.get("int", 0) * INT_VOID_PER_POINT
    return base


__all__ = [
    "BASE_ATTACK", "BASE_CRIT_CHANCE", "BASE_CRIT_DAMAGE", "BASE_DEFENSE",
    "BASE_MAX_HP", "BASE_MAX_VOID", "BASE_SPEED", "DEFENSE_DAMAGE_FLOOR",
    "PlayerStats", "compare_stats", "format_stat", "item_stat_lines",
    "stat_label",
]
