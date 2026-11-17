"""Enemy archetypes, spawn rules and projectile tuning.

The three village enemies share one entity and one AI state machine; only the
numbers and the art source change.  Every gameplay-facing value lives in this
module so a balance pass never touches the state machine.

Stats are deliberately small and readable:

* FALLEN KNIGHT - 100 HP, deliberate melee, long readable wind-up.
* VOID STALKER  - 65 HP, very fast, quick low-damage claws.
* ASHEN CULTIST - 75 HP, keeps its distance, fires a purple bolt.
"""
from __future__ import annotations

from dataclasses import dataclass

from scripts.combat_config import (
    ENEMY_ATTACK_COOLDOWN,
    ENEMY_ATTACK_RANGE,
    ENEMY_ATTACK_TOTAL,
    ENEMY_ATTACK_WINDUP,
    ENEMY_CHASE_SPEED,
    ENEMY_DAMAGE,
    ENEMY_DEATH_TIME,
    ENEMY_DETECTION,
    ENEMY_HALF_H,
    ENEMY_HALF_W,
    ENEMY_HEALTH_MAX,
    ENEMY_HIT_FLASH,
    ENEMY_HURT_TIME,
    ENEMY_KNOCKBACK_DECAY,
    ENEMY_LEASH,
    ENEMY_MEMORY,
    ENEMY_PATROL_RADIUS,
    ENEMY_PATROL_SPEED,
)


@dataclass(frozen=True)
class EnemyArchetype:
    key: str
    name: str
    subtitle: str
    art: str                    # sheet name or procedural art key
    max_health: float
    damage: float
    detection: float
    attack_range: float
    attack_cooldown: float
    windup: float
    active: float
    recovery: float
    chase_speed: float
    patrol_speed: float
    patrol_radius: float
    half_w: float
    half_h: float
    hurt_time: float
    hit_flash: float
    death_time: float
    knockback_decay: float
    memory: float
    leash: float
    attack_fps: float = 8.5
    swipe_color: tuple[int, int, int] = (204, 94, 98)
    # Ranged behaviour.  All zero/False for melee archetypes.
    ranged: bool = False
    preferred_distance: float = 0.0
    retreat_distance: float = 0.0
    retreat_speed: float = 0.0
    retreat_time: float = 0.0
    projectile_speed: float = 0.0
    projectile_damage: float = 0.0
    projectile_radius: float = 0.0
    projectile_range: float = 0.0
    projectile_color: tuple[int, int, int] = (198, 126, 255)

    @property
    def total_time(self) -> float:
        return self.windup + self.active + self.recovery

    @property
    def hitbox(self) -> tuple[float, float]:
        return self.half_w, self.half_h


# The knight keeps the original Phase 2/3 tuning: 100 HP, 12 damage, 0.40 s
# wind-up, 0.80 s total swing.  The split into active/recovery is explicit now
# so the AI can telegraph, strike and recover as separate states.
_FALLEN_ACTIVE = 0.12
_FALLEN_RECOVERY = max(0.0, ENEMY_ATTACK_TOTAL - ENEMY_ATTACK_WINDUP - _FALLEN_ACTIVE)
_FALLEN_WINDUP = ENEMY_ATTACK_WINDUP

ARCHETYPES: dict[str, EnemyArchetype] = {
    "fallen_knight": EnemyArchetype(
        key="fallen_knight",
        name="FALLEN KNIGHT",
        subtitle="UNDEAD SENTINEL",
        art="fallen_knight",
        max_health=ENEMY_HEALTH_MAX,
        damage=ENEMY_DAMAGE,
        detection=ENEMY_DETECTION,
        attack_range=ENEMY_ATTACK_RANGE,
        attack_cooldown=ENEMY_ATTACK_COOLDOWN,
        windup=_FALLEN_WINDUP,
        active=_FALLEN_ACTIVE,
        recovery=_FALLEN_RECOVERY,
        chase_speed=ENEMY_CHASE_SPEED,
        patrol_speed=ENEMY_PATROL_SPEED,
        patrol_radius=ENEMY_PATROL_RADIUS,
        half_w=ENEMY_HALF_W,
        half_h=ENEMY_HALF_H,
        hurt_time=ENEMY_HURT_TIME,
        hit_flash=ENEMY_HIT_FLASH,
        death_time=ENEMY_DEATH_TIME,
        knockback_decay=ENEMY_KNOCKBACK_DECAY,
        memory=ENEMY_MEMORY,
        leash=ENEMY_LEASH,
        attack_fps=8.5,
        swipe_color=(204, 94, 98),
    ),
    "void_stalker": EnemyArchetype(
        key="void_stalker",
        name="VOID STALKER",
        subtitle="VEIL HUNTER",
        art="void_stalker",
        max_health=65.0,
        damage=7.0,
        detection=320.0,
        attack_range=39.0,
        attack_cooldown=0.82,
        windup=0.22,
        active=0.08,
        recovery=0.16,
        chase_speed=152.0,
        patrol_speed=64.0,
        patrol_radius=120.0,
        half_w=11.0,
        half_h=8.0,
        hurt_time=0.17,
        hit_flash=0.10,
        death_time=0.95,
        knockback_decay=700.0,
        memory=4.0,
        leash=900.0,
        attack_fps=16.0,
        swipe_color=(196, 128, 240),
    ),
    "ashen_cultist": EnemyArchetype(
        key="ashen_cultist",
        name="ASHEN CULTIST",
        subtitle="VEIL CHANTER",
        art="ashen_cultist",
        max_health=75.0,
        damage=0.0,
        detection=400.0,
        attack_range=285.0,
        attack_cooldown=2.15,
        windup=0.55,
        active=0.10,
        recovery=0.30,
        chase_speed=78.0,
        patrol_speed=40.0,
        patrol_radius=70.0,
        half_w=11.0,
        half_h=8.0,
        hurt_time=0.20,
        hit_flash=0.12,
        death_time=1.05,
        knockback_decay=560.0,
        memory=4.6,
        leash=820.0,
        attack_fps=7.5,
        swipe_color=(198, 126, 255),
        ranged=True,
        preferred_distance=205.0,
        retreat_distance=140.0,
        retreat_speed=132.0,
        retreat_time=0.85,
        projectile_speed=250.0,
        projectile_damage=10.0,
        projectile_radius=7.0,
        projectile_range=470.0,
        projectile_color=(198, 126, 255),
    ),
}

# Ordered start group: one of every archetype, small and readable.
ENEMY_START_GROUP: tuple[str, ...] = ("fallen_knight", "void_stalker", "ashen_cultist")
ENEMY_RESPAWN_ORDER: tuple[str, ...] = ("void_stalker", "fallen_knight",
                                        "ashen_cultist", "fallen_knight",
                                        "void_stalker", "ashen_cultist")

# ---------------------------------------------------------------------------
# Spawning: finite, capped, and always validated against solids/the player.
# ---------------------------------------------------------------------------
ENEMY_MAX_ACTIVE = 6
ENEMY_SPAWN_INTERVAL = 9.0
ENEMY_SPAWN_TOTAL_CAP = 9          # includes the starting group
ENEMY_SPAWN_MIN_PLAYER_DISTANCE = 420.0
ENEMY_INITIAL_MIN_PLAYER_DISTANCE = 250.0
ENEMY_SPAWN_MIN_ENEMY_DISTANCE = 86.0
ENEMY_SPAWN_JITTER = 22.0
ENEMY_SPAWN_COOLDOWN = 0.45
ENEMY_SPAWN_COOLDOWN_JITTER = 0.30

# ---------------------------------------------------------------------------
# Enemy projectiles (browser-light: simple circles and capped lists).
# ---------------------------------------------------------------------------
ENEMY_PROJECTILE_MAX = 12
ENEMY_PROJECTILE_LIFETIME = 3.0


def get_archetype(key: str) -> EnemyArchetype:
    return ARCHETYPES.get(key, ARCHETYPES["fallen_knight"])


def archetype_for_index(index: int) -> EnemyArchetype:
    keys = list(ARCHETYPES)
    return ARCHETYPES[keys[index % len(keys)]]
