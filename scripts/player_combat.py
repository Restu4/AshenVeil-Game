"""Player combat state machine: five-hit combo, dodge, dash attack and i-frames.

The controller owns timers and intent.  ``Player`` owns movement, collision
and animation, which keeps the two concerns from turning into one big class.
"""
from __future__ import annotations

import math

from scripts.combat_config import (
    ATTACK_ACTIVE,
    ATTACK_COMBO_OPEN,
    ATTACK_COUNT,
    ATTACK_DAMAGE,
    ATTACK_FPS,
    ATTACK_HEAVY,
    ATTACK_KNOCKBACK,
    ATTACK_MOVE_SCALE,
    ATTACK_RECOVERY,
    ATTACK_STARTUP,
    ATTACK_TOTAL,
    COMBO_RESET_TIME,
    COMBO_WINDOW,
    CRIT_FLASH_TIME,
    DASH_COOLDOWN,
    DASH_DAMAGE,
    DASH_DURATION,
    DASH_FPS,
    DASH_IFRAME,
    DASH_KNOCKBACK,
    DODGE_COOLDOWN,
    DODGE_DURATION,
    DODGE_IFRAME,
    PLAYER_HIT_INVULN,
    PLAYER_HURT_KNOCKBACK,
    PLAYER_HURT_TIME,
)
from scripts.skill_config import SHADOW_DURATION, SHADOW_IFRAME

# Player states
IDLE = "IDLE"
WALK = "WALK"
RUN = "RUN"
ATTACK_1 = "ATTACK_1"
ATTACK_2 = "ATTACK_2"
ATTACK_3 = "ATTACK_3"
ATTACK_4 = "ATTACK_4"
ATTACK_5 = "ATTACK_5"
DASH_ATTACK = "DASH_ATTACK"
SHADOW_STEP = "SHADOW_STEP"
DODGE = "DODGE"
HURT = "HURT"
DEAD = "DEAD"

ATTACK_STATES = (ATTACK_1, ATTACK_2, ATTACK_3, ATTACK_4, ATTACK_5)

FACING_VECTORS = {
    "down": (0.0, 1.0),
    "up": (0.0, -1.0),
    "left": (-1.0, 0.0),
    "right": (1.0, 0.0),
}


def _facing_from_vector(x: float, y: float, fallback: str) -> str:
    if abs(x) < 0.001 and abs(y) < 0.001:
        return fallback
    if abs(x) > abs(y):
        return "right" if x > 0 else "left"
    return "down" if y > 0 else "up"


class PlayerCombat:
    def __init__(self, player) -> None:
        self.player = player
        self.state = IDLE
        self.attack_stage = 0           # 1..5 while swinging
        self.attack_time = 0.0
        self.attack_id = 0
        self.attack_consumed = 0        # kept for debug tooling
        self.combo_buffer = False
        self.combo_window = 0.0
        self.combo_count = 0            # landed hits in the HUD counter
        self.combo_decay = 0.0

        self.dodge_time = 0.0
        self.dodge_cooldown = 0.0
        self.dodge_x = 0.0
        self.dodge_y = 0.0

        self.dash_time = 0.0
        self.dash_cooldown = 0.0
        self.dash_x = 0.0
        self.dash_y = 0.0

        # Void skills: Shadow Step reuses the collision sweep, cast locks keep
        # a wind-up from being interrupted by sword input.
        self.shadow_time = 0.0
        self.shadow_x = 0.0
        self.shadow_y = 0.0
        self.cast_time = 0.0
        self.cast_total = 0.0
        self.cast_id = 0

        self.invuln = 0.0
        self.hurt_time = 0.0
        self.hurt_flash = 0.0
        self.blocked_flash = 0.0
        self.hurt_signal = False
        self.dead = False
        self.death_time = 0.0
        self.crit_flash = 0.0

    # ------------------------------------------------------------------
    # Intent
    # ------------------------------------------------------------------
    def request_attack(self) -> None:
        if self.dead or self.cast_time > 0.0 or self.state in (
                HURT, DODGE, DASH_ATTACK, SHADOW_STEP):
            return
        if self.state in ATTACK_STATES:
            # Rapid clicks are buffered into exactly one next link.
            self.combo_buffer = True
            return

        if self.combo_window > 0.0 and 1 <= self.attack_stage < ATTACK_COUNT:
            self._start_attack(self.attack_stage + 1)
        else:
            self._start_attack(1)

    def request_dodge(self) -> None:
        if self.dead or self.cast_time > 0.0 or self.state in (
                HURT, DODGE, SHADOW_STEP):
            return
        if self.dodge_cooldown > 0.0:
            return

        ix, iy = self.player.input_x, self.player.input_y
        if abs(ix) < 0.001 and abs(iy) < 0.001:
            ix, iy = FACING_VECTORS[self.player.facing]
        length = math.hypot(ix, iy) or 1.0
        self.dodge_x, self.dodge_y = ix / length, iy / length
        self.player.facing = _facing_from_vector(ix, iy, self.player.facing)

        self.dodge_time = DODGE_DURATION
        self.dodge_cooldown = DODGE_COOLDOWN
        self.invuln = max(self.invuln, DODGE_IFRAME)
        self.state = DODGE
        self.attack_stage = 0
        self.attack_time = 0.0
        self.combo_buffer = False
        self.combo_window = 0.0
        self.dash_time = 0.0

    def request_dash(self) -> None:
        """Dash attack: a short forward burst with a wide sword strike."""
        if self.dead or self.cast_time > 0.0 or self.state in (
                HURT, DODGE, DASH_ATTACK, SHADOW_STEP):
            return
        if self.dash_cooldown > 0.0:
            return

        ix, iy = self.player.input_x, self.player.input_y
        if abs(ix) < 0.001 and abs(iy) < 0.001:
            ix, iy = FACING_VECTORS[self.player.facing]
        length = math.hypot(ix, iy) or 1.0
        self.dash_x, self.dash_y = ix / length, iy / length
        self.player.facing = _facing_from_vector(ix, iy, self.player.facing)

        self.dash_time = DASH_DURATION
        self.dash_cooldown = DASH_COOLDOWN
        self.invuln = max(self.invuln, DASH_IFRAME)
        self.state = DASH_ATTACK
        self.attack_stage = 0
        self.attack_time = 0.0
        self.attack_id += 1
        self.combo_buffer = False
        self.combo_window = 0.0
        self.dodge_time = 0.0

    def begin_shadow_step(self) -> bool:
        """Trigger the SHADOW STEP void dash without spending energy here."""
        if self.dead or self.cast_time > 0.0:
            return False
        if self.state in (HURT, DODGE, DASH_ATTACK, SHADOW_STEP):
            return False

        ix, iy = self.player.input_x, self.player.input_y
        if abs(ix) < 0.001 and abs(iy) < 0.001:
            ix, iy = FACING_VECTORS[self.player.facing]
        length = math.hypot(ix, iy) or 1.0
        self.shadow_x, self.shadow_y = ix / length, iy / length
        self.player.facing = _facing_from_vector(ix, iy, self.player.facing)

        self.shadow_time = SHADOW_DURATION
        self.invuln = max(self.invuln, SHADOW_IFRAME)
        self.state = SHADOW_STEP
        self.attack_stage = 0
        self.attack_time = 0.0
        self.combo_buffer = False
        self.combo_window = 0.0
        self.dodge_time = 0.0
        self.dash_time = 0.0
        return True

    def begin_cast(self, duration: float) -> bool:
        """Lock the player into a short skill wind-up/cast recovery."""
        if self.dead or self.state == HURT:
            return False
        self.cast_time = max(0.01, float(duration))
        self.cast_total = self.cast_time
        self.cast_id += 1
        self.attack_stage = 0
        self.attack_time = 0.0
        self.combo_buffer = False
        self.combo_window = 0.0
        self.dodge_time = 0.0
        self.dash_time = 0.0
        self.state = IDLE
        return True

    # ------------------------------------------------------------------
    def _start_attack(self, stage: int) -> bool:
        self.state = ATTACK_STATES[stage - 1]
        self.attack_stage = stage
        self.attack_time = 0.0
        self.attack_id += 1
        self.attack_consumed = 0
        self.combo_buffer = False
        self.combo_window = 0.0
        return True

    def _finish_attack(self) -> None:
        if self.attack_stage < ATTACK_COUNT:
            self.combo_window = COMBO_WINDOW
        else:
            self.combo_window = 0.0
            self.attack_stage = 0
        self.state = IDLE
        self.attack_time = 0.0
        self.combo_buffer = False

    # ------------------------------------------------------------------
    # Timers
    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        dt = max(0.0, dt)
        self.dodge_cooldown = max(0.0, self.dodge_cooldown - dt)
        self.dash_cooldown = max(0.0, self.dash_cooldown - dt)
        self.cast_time = max(0.0, self.cast_time - dt)
        self.invuln = max(0.0, self.invuln - dt)
        self.hurt_flash = max(0.0, self.hurt_flash - dt)
        self.blocked_flash = max(0.0, self.blocked_flash - dt)
        self.crit_flash = max(0.0, self.crit_flash - dt)

        if self.combo_decay > 0.0:
            self.combo_decay = max(0.0, self.combo_decay - dt)
            if self.combo_decay <= 0.0:
                self.combo_count = 0

        if self.dead:
            self.death_time += dt
            return

        if self.state == HURT:
            self.hurt_time -= dt
            if self.hurt_time <= 0.0:
                self.state = IDLE
            return

        if self.state == DODGE:
            self.dodge_time -= dt
            if self.dodge_time <= 0.0:
                self.dodge_time = 0.0
                self.state = IDLE
            return

        if self.state == SHADOW_STEP:
            self.shadow_time -= dt
            if self.shadow_time <= 0.0:
                self.shadow_time = 0.0
                self.state = IDLE
            return

        if self.state == DASH_ATTACK:
            self.dash_time -= dt
            if self.dash_time <= 0.0:
                self.dash_time = 0.0
                self.state = IDLE
                self.attack_stage = 0
                self.combo_window = 0.0
            return

        if self.state in ATTACK_STATES:
            self.attack_time += dt
            total = ATTACK_TOTAL[self.attack_stage - 1]
            if self.attack_time >= total:
                if self.combo_buffer and self.attack_stage < ATTACK_COUNT:
                    self._start_attack(self.attack_stage + 1)
                    return
                self._finish_attack()
                return

        if self.combo_window > 0.0:
            self.combo_window = max(0.0, self.combo_window - dt)
            if self.combo_window <= 0.0:
                self.attack_stage = 0

    # ------------------------------------------------------------------
    # Damage / feedback
    # ------------------------------------------------------------------
    def take_damage(self, amount: float, source_x: float, source_y: float) -> bool:
        if self.dead or self.invuln > 0.0:
            return False
        lost = self.player.vitality.damage(amount)
        if lost <= 0.0:
            return False
        self.hurt_signal = True
        self.hurt_flash = 0.18
        self.invuln = PLAYER_HIT_INVULN
        self.attack_stage = 0
        self.attack_time = 0.0
        self.combo_window = 0.0
        self.combo_buffer = False
        self.combo_count = 0
        self.combo_decay = 0.0
        self.dodge_time = 0.0
        self.dash_time = 0.0
        self.shadow_time = 0.0
        self.cast_time = 0.0

        dx = self.player.x - source_x
        dy = self.player.y - source_y
        length = math.hypot(dx, dy)
        if length < 0.001:
            dx, dy, length = *FACING_VECTORS[self.player.facing], 1.0
        self.player.knockback_x = dx / length * PLAYER_HURT_KNOCKBACK
        self.player.knockback_y = dy / length * PLAYER_HURT_KNOCKBACK

        if self.player.vitality.dead:
            self.dead = True
            self.state = DEAD
            self.death_time = 0.0
            self.hurt_time = 0.0
        else:
            self.state = HURT
            self.hurt_time = PLAYER_HURT_TIME
        return True

    def register_hit(self, crit: bool = False) -> None:
        """Called by the combat manager when a swing connects."""
        self.combo_count += 1
        self.combo_decay = COMBO_RESET_TIME
        if crit:
            self.crit_flash = CRIT_FLASH_TIME

    def consume_hurt_signal(self) -> bool:
        signal = self.hurt_signal
        self.hurt_signal = False
        return signal

    def reset(self) -> None:
        self.state = IDLE
        self.attack_stage = 0
        self.attack_time = 0.0
        self.attack_id = 0
        self.attack_consumed = 0
        self.combo_buffer = False
        self.combo_window = 0.0
        self.combo_count = 0
        self.combo_decay = 0.0
        self.dodge_time = 0.0
        self.dodge_cooldown = 0.0
        self.dodge_x = self.dodge_y = 0.0
        self.dash_time = 0.0
        self.dash_cooldown = 0.0
        self.dash_x = self.dash_y = 0.0
        self.shadow_time = 0.0
        self.shadow_x = self.shadow_y = 0.0
        self.cast_time = 0.0
        self.cast_total = 0.0
        self.cast_id = 0
        self.invuln = 0.0
        self.hurt_time = 0.0
        self.hurt_flash = 0.0
        self.blocked_flash = 0.0
        self.hurt_signal = False
        self.dead = False
        self.death_time = 0.0
        self.crit_flash = 0.0

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    @property
    def attack_phase(self) -> str | None:
        if self.state == DASH_ATTACK:
            return "active" if self.dash_time > 0.0 else None
        if self.state not in ATTACK_STATES:
            return None
        startup = ATTACK_STARTUP[self.attack_stage - 1]
        active = ATTACK_ACTIVE[self.attack_stage - 1]
        total = ATTACK_TOTAL[self.attack_stage - 1]
        if self.attack_time < startup:
            return "startup"
        if self.attack_time < startup + active:
            return "active"
        if self.attack_time < total + 0.001:
            return "recovery"
        return None

    @property
    def attack_active(self) -> bool:
        return self.attack_phase == "active"

    @property
    def stage_startup(self) -> float:
        if not 1 <= self.attack_stage <= ATTACK_COUNT:
            return 0.0
        return ATTACK_STARTUP[self.attack_stage - 1]

    @property
    def attack_damage(self) -> float:
        if self.state == DASH_ATTACK:
            return DASH_DAMAGE
        return ATTACK_DAMAGE[max(0, self.attack_stage - 1)]

    @property
    def attack_knockback(self) -> float:
        if self.state == DASH_ATTACK:
            return DASH_KNOCKBACK
        return ATTACK_KNOCKBACK[max(0, self.attack_stage - 1)]

    @property
    def attack_heavy(self) -> bool:
        if self.state == DASH_ATTACK:
            return True
        return ATTACK_HEAVY[max(0, self.attack_stage - 1)]

    @property
    def attack_fps(self) -> float:
        if self.state == DASH_ATTACK:
            return DASH_FPS
        return ATTACK_FPS[max(0, self.attack_stage - 1)]

    @property
    def dodging(self) -> bool:
        return self.state == DODGE and self.dodge_time > 0.0

    @property
    def dashing(self) -> bool:
        return self.state == DASH_ATTACK and self.dash_time > 0.0

    @property
    def shadow_step(self) -> bool:
        return self.state == SHADOW_STEP and self.shadow_time > 0.0

    @property
    def casting(self) -> bool:
        return self.cast_time > 0.0

    @property
    def can_cast_skill(self) -> bool:
        return not self.dead and self.state != HURT and not self.casting

    @property
    def invulnerable(self) -> bool:
        return self.invuln > 0.0 or self.dead

    @property
    def can_buffer(self) -> bool:
        return self.state in ATTACK_STATES and self.attack_time >= ATTACK_COMBO_OPEN

    @property
    def movement_scale(self) -> float:
        if self.dead or self.state in (HURT, DODGE, SHADOW_STEP):
            return 0.0
        if self.casting:
            return 0.25
        if self.state == DASH_ATTACK:
            return 1.0
        if self.state in ATTACK_STATES:
            return ATTACK_MOVE_SCALE[self.attack_stage - 1]
        return 1.0

    @property
    def dash_ready_ratio(self) -> float:
        if DASH_COOLDOWN <= 0.0:
            return 1.0
        return max(0.0, min(1.0, 1.0 - self.dash_cooldown / DASH_COOLDOWN))
