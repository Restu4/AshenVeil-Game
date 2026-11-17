"""Central tuning for the VOID ESSENCE dark-magic system.

Everything gameplay-facing lives here so the four skills can be re-balanced
without touching the state machines.  Values are seconds, pixels, hit points
and energy points.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Void Energy resource
# ---------------------------------------------------------------------------
VOID_ENERGY_MAX = 100.0
VOID_ENERGY_START = 100.0
VOID_REGEN_PER_SEC = 8.0
VOID_KILL_REWARD = 8.0

# ---------------------------------------------------------------------------
# Skill 1 - VOID BURST  (Q)
# ---------------------------------------------------------------------------
BURST_NAME = "VOID BURST"
BURST_KEY = "Q"
BURST_COST = 20.0
BURST_DAMAGE = 35.0
BURST_RADIUS = 110.0
BURST_COOLDOWN = 3.0
BURST_KNOCKBACK = 165.0
BURST_HIT_STOP = 0.055
BURST_SHAKE = 3.4
BURST_CAST_LOCK = 0.06

# ---------------------------------------------------------------------------
# Skill 2 - SHADOW STEP  (E)
# ---------------------------------------------------------------------------
SHADOW_NAME = "SHADOW STEP"
SHADOW_KEY = "E"
SHADOW_COST = 15.0
SHADOW_COOLDOWN = 2.0
SHADOW_DURATION = 0.25
SHADOW_SPEED = 690.0
SHADOW_IFRAME = 0.22
SHADOW_TRAIL_INTERVAL = 0.042

# ---------------------------------------------------------------------------
# Skill 3 - VOID SLASH  (R)
# ---------------------------------------------------------------------------
SLASH_NAME = "VOID SLASH"
SLASH_KEY = "R"
SLASH_COST = 25.0
SLASH_DAMAGE = 45.0
SLASH_COOLDOWN = 5.0
SLASH_RANGE = 320.0
SLASH_SPEED = 560.0
SLASH_HIT_RADIUS = 36.0
SLASH_KNOCKBACK = 215.0
SLASH_HIT_STOP = 0.050
SLASH_SHAKE = 4.6
SLASH_CAST_LOCK = 0.14
SLASH_TRAIL_INTERVAL = 0.030

# ---------------------------------------------------------------------------
# Ultimate - ECLIPSE  (F)
# ---------------------------------------------------------------------------
ECLIPSE_NAME = "ECLIPSE"
ECLIPSE_KEY = "F"
ECLIPSE_COST = 60.0
ECLIPSE_DAMAGE = 100.0
ECLIPSE_RADIUS = 220.0
ECLIPSE_COOLDOWN = 18.0
ECLIPSE_WINDUP = 0.55
ECLIPSE_KNOCKBACK = 360.0
ECLIPSE_HIT_STOP = 0.090
ECLIPSE_SHAKE = 9.0

# ---------------------------------------------------------------------------
# Presentation limits (browser safety)
# ---------------------------------------------------------------------------
SKILL_MAX_PARTICLES = 240
SKILL_MAX_RINGS = 10
SKILL_MAX_AFTERIMAGES = 24
SKILL_MAX_WAVES = 4
SKILL_NUMBER_LIMIT = 16
