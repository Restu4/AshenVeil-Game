"""Central combat tuning for ASHEN VEIL.

Every gameplay-facing number lives here so the feel can be adjusted without
touching the state machines.  Values are in seconds, pixels and hit points.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Player vitality
# ---------------------------------------------------------------------------
PLAYER_HEALTH_MAX = 100.0
PLAYER_HURT_TIME = 0.28
PLAYER_HIT_INVULN = 0.85
PLAYER_HURT_KNOCKBACK = 150.0
PLAYER_HURT_DECAY = 900.0

# ---------------------------------------------------------------------------
# Sword combo: three committed swings with a late-cancel recovery.
# ---------------------------------------------------------------------------
ATTACK_STARTUP = 0.12
ATTACK_ACTIVE = 0.16
ATTACK_RECOVERY = 0.20
ATTACK_TOTAL = ATTACK_STARTUP + ATTACK_ACTIVE + ATTACK_RECOVERY
ATTACK_COMBO_OPEN = 0.20          # can buffer from here
COMBO_WINDOW = 0.55               # time after a swing to continue
ATTACK_DAMAGE = (25.0, 30.0, 45.0)
ATTACK_STAMINA_COST = 10.0
ATTACK_KNOCKBACK = (95.0, 110.0, 235.0)
ATTACK_REACH = 64.0
ATTACK_WIDTH = 58.0
ATTACK_MOVE_SCALE = 0.20          # shuffle, do not glide, while swinging
ATTACK_SHAKE = (0.0, 0.0, 5.0)
ATTACK_HEAVY = (False, False, True)

# ---------------------------------------------------------------------------
# Dodge
# ---------------------------------------------------------------------------
DODGE_DURATION = 0.30
DODGE_COOLDOWN = 0.45
DODGE_STAMINA_COST = 20.0
DODGE_IFRAME = 0.20
DODGE_SPEED = 370.0

# ---------------------------------------------------------------------------
# Fallen Knight
# ---------------------------------------------------------------------------
ENEMY_HEALTH_MAX = 100.0
ENEMY_DAMAGE = 15.0
ENEMY_DETECTION = 180.0
ENEMY_ATTACK_RANGE = 42.0
ENEMY_ATTACK_COOLDOWN = 1.2
ENEMY_ATTACK_WINDUP = 0.38
ENEMY_ATTACK_TOTAL = 0.78
ENEMY_CHASE_SPEED = 88.0
ENEMY_PATROL_SPEED = 46.0
ENEMY_PATROL_RADIUS = 95.0
ENEMY_HALF_W = 13.0
ENEMY_HALF_H = 9.0
ENEMY_HURT_TIME = 0.24
ENEMY_HIT_FLASH = 0.12
ENEMY_DEATH_TIME = 1.15
ENEMY_KNOCKBACK_DECAY = 420.0
ENEMY_MEMORY = 3.2
ENEMY_LEASH = 620.0

# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------
SHAKE_PLAYER_HURT = 3.0
SHAKE_PLAYER_HURT_TIME = 0.16
HURT_VIGNETTE_TIME = 0.45
DAMAGE_NUMBER_TIME = 0.85
