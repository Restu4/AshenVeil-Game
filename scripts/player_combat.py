"""Player combat state machine: attacks, combo, dodge and i-frames.

The controller owns timers and intent.  ``Player`` owns movement, collision
and animation, which keeps the two concerns from turning into one big class.
"""
from __future__ import annotations

import math

from scripts.combat_config import (
    ATTACK_ACTIVE,
    ATTACK_COMBO_OPEN,
    ATTACK_DAMAGE,
    ATTACK_HEAVY,
    ATTACK_KNOCKBACK,
    ATTACK_STAMINA_COST,
    ATTACK_STARTUP,
    ATTACK_TOTAL,
    COMBO_WINDOW,
    DODGE_COOLDOWN,
    DODGE_DURATION,
    DODGE_IFRAME,
    DODGE_STAMINA_COST,
    PLAYER_HIT_INVULN,
    PLAYER_HURT_KNOCKBACK,
    PLAYER_HURT_TIME,
)

# Player states
IDLE = "IDLE"
WALK = "WALK"
RUN = "RUN"
ATTACK_1 = "ATTACK_1"
ATTACK_2 = "ATTACK_2"
ATTACK_3 = "ATTACK_3"
DODGE = "DODGE"
HURT = "HURT"
DEAD = "DEAD"

ATTACK_STATES = (ATTACK_1, ATTACK_2, ATTACK_3)

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
        self.attack_stage = 0           # 1..3 while swinging
        self.attack_time = 0.0
        self.attack_id = 0
        self.attack_consumed = 0        # damage events already resolved
        self.combo_buffer = False
        self.combo_window = 0.0

        self.dodge_time = 0.0
        self.dodge_cooldown = 0.0
        self.dodge_x = 0.0
        self.dodge_y = 0.0

        self.invuln = 0.0
        self.hurt_time = 0.0
        self.hurt_flash = 0.0
        self.blocked_flash = 0.0
        self.hurt_signal = False
        self.dead = False
        self.death_time = 0.0

    # ------------------------------------------------------------------
    # Intent
    # ------------------------------------------------------------------
    def request_attack(self) -> None:
        if self.dead or self.state in (HURT, DODGE):
            return
        if self.state in ATTACK_STATES:
            # Buffer the next link once the swing is far enough along.
            if self.attack_time >= ATTACK_COMBO_OPEN:
                self.combo_buffer = True
            return

        if self.combo_window > 0.0 and 1 <= self.attack_stage < 3:
            self._start_attack(self.attack_stage + 1)
        else:
            self._start_attack(1)

    def request_dodge(self) -> None:
        if self.dead or self.state in (HURT, DODGE):
            return
        if self.dodge_cooldown > 0.0:
            return
        if self.state in ATTACK_STATES and self.attack_phase != "recovery":
            return  # attacks commit through startup and active frames
        if not self.player.stamina.spend(DODGE_STAMINA_COST):
            self.blocked_flash = 0.55
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

    # ------------------------------------------------------------------
    def _start_attack(self, stage: int) -> bool:
        if not self.player.stamina.spend(ATTACK_STAMINA_COST):
            self.blocked_flash = 0.55
            return False
        self.state = (ATTACK_1, ATTACK_2, ATTACK_3)[stage - 1]
        self.attack_stage = stage
        self.attack_time = 0.0
        self.attack_id += 1
        self.attack_consumed = 0
        self.combo_buffer = False
        self.combo_window = 0.0
        return True

    def _finish_attack(self) -> None:
        if self.attack_stage < 3:
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
        self.dodge_cooldown = max(0.0, self.dodge_cooldown - dt)
        self.invuln = max(0.0, self.invuln - dt)
        self.hurt_flash = max(0.0, self.hurt_flash - dt)
        self.blocked_flash = max(0.0, self.blocked_flash - dt)

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

        if self.state in ATTACK_STATES:
            self.attack_time += dt
            if self.attack_time >= ATTACK_TOTAL:
                if self.combo_buffer and self.attack_stage < 3 \
                        and self._start_attack(self.attack_stage + 1):
                    return
                self._finish_attack()
                return

        if self.combo_window > 0.0:
            self.combo_window = max(0.0, self.combo_window - dt)
            if self.combo_window <= 0.0:
                self.attack_stage = 0

    # ------------------------------------------------------------------
    # Damage
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
        self.dodge_time = 0.0

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
        self.dodge_time = 0.0
        self.dodge_cooldown = 0.0
        self.dodge_x = self.dodge_y = 0.0
        self.invuln = 0.0
        self.hurt_time = 0.0
        self.hurt_flash = 0.0
        self.blocked_flash = 0.0
        self.hurt_signal = False
        self.dead = False
        self.death_time = 0.0

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    @property
    def attack_phase(self) -> str | None:
        if self.state not in ATTACK_STATES:
            return None
        if self.attack_time < ATTACK_STARTUP:
            return "startup"
        if self.attack_time < ATTACK_STARTUP + ATTACK_ACTIVE:
            return "active"
        if self.attack_time < ATTACK_TOTAL + 0.001:
            return "recovery"
        return None

    @property
    def attack_active(self) -> bool:
        return self.attack_phase == "active"

    @property
    def attack_damage(self) -> float:
        return ATTACK_DAMAGE[max(0, self.attack_stage - 1)]

    @property
    def attack_knockback(self) -> float:
        return ATTACK_KNOCKBACK[max(0, self.attack_stage - 1)]

    @property
    def attack_heavy(self) -> bool:
        return ATTACK_HEAVY[max(0, self.attack_stage - 1)]

    @property
    def dodging(self) -> bool:
        return self.state == DODGE and self.dodge_time > 0.0

    @property
    def invulnerable(self) -> bool:
        return self.invuln > 0.0 or self.dead

    @property
    def movement_scale(self) -> float:
        if self.dead or self.state in (HURT, DODGE):
            return 0.0
        if self.state in ATTACK_STATES:
            return 0.20
        return 1.0
