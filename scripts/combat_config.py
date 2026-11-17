"""Central combat tuning for ASHEN VEIL.

Every gameplay-facing number lives here so the feel can be adjusted without
touching the state machines.  Values are in seconds, pixels and hit points.

The combat direction is fast hack & slash: attacks are free and quick, the
five-hit combo is the core loop, and stamina no longer gates offence.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Player vitality
# ---------------------------------------------------------------------------
PLAYER_HEALTH_MAX = 100.0
PLAYER_HURT_TIME = 0.22
PLAYER_HIT_INVULN = 0.75
PLAYER_HURT_KNOCKBACK = 165.0
PLAYER_HURT_DECAY = 980.0

# ---------------------------------------------------------------------------
# Five-hit sword combo
#
# Stage:   1 horizontal  2 reverse  3 diagonal  4 spin  5 finisher
# Every swing is startup -> active -> recovery.  Timings are per stage so the
# first two links snap, the spin commits a little, and the finisher lands with
# weight.  Attacks cost no stamina.
# ---------------------------------------------------------------------------
ATTACK_COUNT = 5
ATTACK_STARTUP = (0.055, 0.055, 0.065, 0.085, 0.115)
ATTACK_ACTIVE = (0.095, 0.095, 0.105, 0.135, 0.165)
ATTACK_RECOVERY = (0.070, 0.070, 0.085, 0.110, 0.170)
ATTACK_TOTAL = tuple(
    startup + active + recovery
    for startup, active, recovery
    in zip(ATTACK_STARTUP, ATTACK_ACTIVE, ATTACK_RECOVERY)
)
ATTACK_COMBO_OPEN = 0.045          # buffered clicks are accepted this early
COMBO_WINDOW = 0.50                # time after a swing to chain the next link
COMBO_RESET_TIME = 2.2             # HUD combo counter decay

ATTACK_DAMAGE = (20.0, 22.0, 25.0, 30.0, 45.0)
ATTACK_KNOCKBACK = (70.0, 80.0, 95.0, 180.0, 280.0)
ATTACK_REACH = (58.0, 60.0, 64.0, 84.0, 94.0)
ATTACK_WIDTH = (54.0, 56.0, 60.0, 78.0, 96.0)
ATTACK_MOVE_SCALE = (0.55, 0.55, 0.50, 0.40, 0.30)
ATTACK_SHAKE = (1.0, 1.0, 1.2, 3.4, 6.5)
ATTACK_HEAVY = (False, False, False, True, True)
ATTACK_SPIN = (False, False, False, True, True)
ATTACK_FPS = (19.0, 19.0, 17.0, 15.0, 12.0)

# ---------------------------------------------------------------------------
# Critical hits
# ---------------------------------------------------------------------------
CRIT_CHANCE = 0.18
CRIT_MULTIPLIER = 1.7
CRIT_KNOCKBACK_MULT = 1.25

# ---------------------------------------------------------------------------
# Dodge: fast, cheap, and never gated by a resource bar.
# ---------------------------------------------------------------------------
DODGE_DURATION = 0.22
DODGE_COOLDOWN = 0.30
DODGE_IFRAME = 0.16
DODGE_SPEED = 470.0

# ---------------------------------------------------------------------------
# Dash attack (default key E, configurable through DASH_KEY_NAME).
# ---------------------------------------------------------------------------
DASH_KEY_NAME = "E"
DASH_DURATION = 0.20
DASH_COOLDOWN = 0.85
DASH_SPEED = 640.0
DASH_DAMAGE = 26.0
DASH_KNOCKBACK = 195.0
DASH_REACH = 78.0
DASH_WIDTH = 74.0
DASH_IFRAME = 0.08
DASH_SHAKE = 3.0
DASH_FPS = 20.0

# ---------------------------------------------------------------------------
# Hit stop: a few frozen frames make hits read without hurting responsiveness.
# ---------------------------------------------------------------------------
HIT_STOP_NORMAL = 0.035
HIT_STOP_HEAVY = 0.070
HIT_STOP_FINISHER = 0.105

# ---------------------------------------------------------------------------
# Fallen Knight: readable, individually cooldown-gated so two knights never
# land an unavoidable simultaneous blow.
# ---------------------------------------------------------------------------
ENEMY_HEALTH_MAX = 100.0
ENEMY_DAMAGE = 12.0
ENEMY_DETECTION = 230.0
ENEMY_ATTACK_RANGE = 44.0
ENEMY_ATTACK_COOLDOWN = 1.35
ENEMY_ATTACK_WINDUP = 0.40
ENEMY_ATTACK_TOTAL = 0.80
ENEMY_CHASE_SPEED = 96.0
ENEMY_PATROL_SPEED = 46.0
ENEMY_PATROL_RADIUS = 95.0
ENEMY_HALF_W = 13.0
ENEMY_HALF_H = 9.0
ENEMY_HURT_TIME = 0.22
ENEMY_HIT_FLASH = 0.12
ENEMY_DEATH_TIME = 1.10
ENEMY_KNOCKBACK_DECAY = 520.0
ENEMY_MEMORY = 3.6
ENEMY_LEASH = 700.0
ENEMY_SEPARATION = 30.0
ENEMY_SPAWN_COOLDOWN = 0.45
ENEMY_SPAWN_JITTER = 0.30
ENEMY_ATTACK_TOKEN_RANGE = 1.7   # multiplier on ENEMY_ATTACK_RANGE

# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------
SHAKE_PLAYER_HURT = 3.0
SHAKE_PLAYER_HURT_TIME = 0.16
HURT_VIGNETTE_TIME = 0.45
DAMAGE_NUMBER_TIME = 0.85
CRIT_FLASH_TIME = 0.55
