"""Delta-time AI for the Fallen Knight.

State constants and steering live here; ``scripts/enemy.py`` owns the entity,
animation and damage plumbing.  No imports from ``enemy`` means there is no
circular dependency.
"""
from __future__ import annotations

import math

from scripts.combat_config import (
    ENEMY_ATTACK_COOLDOWN,
    ENEMY_ATTACK_RANGE,
    ENEMY_ATTACK_TOTAL,
    ENEMY_ATTACK_WINDUP,
    ENEMY_CHASE_SPEED,
    ENEMY_DAMAGE,
    ENEMY_DETECTION,
    ENEMY_KNOCKBACK_DECAY,
    ENEMY_LEASH,
    ENEMY_MEMORY,
    ENEMY_PATROL_SPEED,
)

IDLE = "IDLE"
PATROL = "PATROL"
CHASE = "CHASE"
ATTACK = "ATTACK"
HURT = "HURT"
DEATH = "DEATH"

FACING_VECTORS = {
    "down": (0.0, 1.0),
    "up": (0.0, -1.0),
    "left": (-1.0, 0.0),
    "right": (1.0, 0.0),
}


def facing_from_delta(dx: float, dy: float, fallback: str = "down") -> str:
    if abs(dx) < 0.001 and abs(dy) < 0.001:
        return fallback
    if abs(dx) > abs(dy):
        return "right" if dx > 0 else "left"
    return "down" if dy > 0 else "up"


def update_enemy(enemy, dt: float, player, collision) -> None:
    enemy.flash_timer = max(0.0, enemy.flash_timer - dt)
    enemy.attack_cooldown = max(0.0, enemy.attack_cooldown - dt)
    enemy.aggro_timer = max(0.0, enemy.aggro_timer - dt)
    enemy.state_time += dt

    if enemy.state == DEATH:
        enemy.death_timer -= dt
        enemy.vx = enemy.vy = 0.0
        enemy.animator.update(dt)
        if enemy.death_timer <= 0.0:
            enemy.removed = True
        return

    # Knockback is applied in every non-death state; it is part of HURT but
    # also carries into the first frames of a chase.
    _apply_knockback(enemy, dt, collision)

    if enemy.state == HURT:
        enemy.hurt_timer -= dt
        if enemy.hurt_timer <= 0.0:
            enemy.state = CHASE if enemy.aggro_timer > 0.0 else PATROL
            enemy.patrol_target = None
        _animate(enemy, dt)
        return

    dx = player.x - enemy.x
    dy = player.y - enemy.y
    distance = math.hypot(dx, dy)
    player_dead = player.combat.dead

    # Detection and short-term memory.
    if not player_dead and distance <= ENEMY_DETECTION:
        enemy.aggro_timer = ENEMY_MEMORY
        enemy.alerted = True
        if enemy.state in (IDLE, PATROL):
            enemy.state = CHASE
            enemy.patrol_target = None
            enemy.facing = facing_from_delta(dx, dy, enemy.facing)

    # Leash so knights do not follow the player across the whole village.
    home_distance = math.hypot(enemy.x - enemy.home_x, enemy.y - enemy.home_y)
    if enemy.aggro_timer > 0.0 and home_distance > ENEMY_LEASH:
        enemy.aggro_timer = 0.0
        enemy.state = PATROL
        enemy.patrol_target = None

    if enemy.state == ATTACK:
        _update_attack(enemy, dt, player, collision, distance)
        _animate(enemy, dt)
        return

    if not player_dead and enemy.aggro_timer > 0.0:
        hold = ENEMY_ATTACK_RANGE * (0.82 if enemy.can_attack else 1.28)
        if (distance <= ENEMY_ATTACK_RANGE and enemy.attack_cooldown <= 0.0
                and enemy.can_attack):
            _start_attack(enemy, player, dx, dy)
        else:
            enemy.state = CHASE
            if distance > hold:
                speed = ENEMY_CHASE_SPEED
                enemy.facing = facing_from_delta(dx, dy, enemy.facing)
                _steer(enemy, dt, collision, dx / max(distance, 0.001),
                       dy / max(distance, 0.001), speed)
            else:
                enemy.vx = enemy.vy = 0.0
    else:
        _patrol(enemy, dt, collision)

    _animate(enemy, dt)


# ---------------------------------------------------------------------------
def _start_attack(enemy, player, dx: float, dy: float) -> None:
    if not enemy.can_attack:
        return
    enemy.state = ATTACK
    enemy.state_time = 0.0
    enemy.attack_time = 0.0
    enemy.attack_hit_done = False
    enemy.attack_cooldown = ENEMY_ATTACK_COOLDOWN
    enemy.facing = facing_from_delta(dx, dy, enemy.facing)
    enemy.animator.play("attack", enemy.facing, restart=True)


def _update_attack(enemy, dt: float, player, collision, distance: float) -> None:
    enemy.vx = enemy.vy = 0.0
    enemy.attack_time += dt
    if (not enemy.attack_hit_done
            and enemy.attack_time >= ENEMY_ATTACK_WINDUP):
        enemy.attack_hit_done = True
        # The blow lands in a forward arc, so circling behind a knight or
        # rolling through the swing avoids it.
        fx, fy = FACING_VECTORS[enemy.facing]
        in_front = ((player.x - enemy.x) * fx + (player.y - enemy.y) * fy)
        in_front /= max(distance, 0.001)
        if (distance <= ENEMY_ATTACK_RANGE + 14.0
                and in_front > -0.15
                and not player.combat.invulnerable
                and not player.combat.dead):
            chest_y = enemy.y - 18.0
            if not collision.segment_blocked(enemy.x, chest_y,
                                             player.x, player.y - 18.0, 3):
                player.take_damage(ENEMY_DAMAGE, enemy.x, enemy.y)
    if enemy.attack_time >= ENEMY_ATTACK_TOTAL:
        enemy.state = CHASE if enemy.aggro_timer > 0.0 else PATROL
        enemy.patrol_target = None
        enemy.state_time = 0.0


# ---------------------------------------------------------------------------
def _patrol(enemy, dt: float, collision) -> None:
    if enemy.patrol_wait > 0.0:
        enemy.patrol_wait -= dt
        enemy.state = IDLE
        enemy.vx = enemy.vy = 0.0
        return

    if enemy.patrol_target is None:
        angle = enemy.rng.uniform(0.0, math.tau)
        radius = enemy.rng.uniform(12.0, max(14.0, enemy.patrol_radius))
        enemy.patrol_target = (
            enemy.home_x + math.cos(angle) * radius,
            enemy.home_y + math.sin(angle) * radius,
        )
        enemy.state = PATROL

    tx, ty = enemy.patrol_target
    dx, dy = tx - enemy.x, ty - enemy.y
    distance = math.hypot(dx, dy)
    if distance <= 6.0:
        enemy.patrol_target = None
        enemy.patrol_wait = enemy.rng.uniform(1.3, 2.8)
        enemy.vx = enemy.vy = 0.0
        enemy.state = IDLE
        return

    enemy.state = PATROL
    enemy.facing = facing_from_delta(dx, dy, enemy.facing)
    _steer(enemy, dt, collision, dx / distance, dy / distance,
           ENEMY_PATROL_SPEED)


def _steer(enemy, dt: float, collision, nx: float, ny: float,
           speed: float) -> None:
    if enemy.avoid_timer > 0.0:
        enemy.avoid_timer -= dt
        # Bend around whatever stopped us instead of grinding into it.
        bend_x = nx * 0.55 - ny * 0.85 * enemy.avoid_sign
        bend_y = ny * 0.55 + nx * 0.85 * enemy.avoid_sign
        length = math.hypot(bend_x, bend_y) or 1.0
        nx, ny = bend_x / length, bend_y / length

    vx = nx * speed
    vy = ny * speed
    enemy.vx, enemy.vy = vx, vy
    dx = vx * dt
    dy = vy * dt
    if not dx and not dy:
        return
    enemy.x, enemy.y, hit_x, hit_y = collision.move(
        enemy.x, enemy.y, dx, dy, enemy.half_w, enemy.half_h
    )
    if hit_x and hit_y and enemy.avoid_timer <= 0.0:
        enemy.avoid_timer = 0.45
        enemy.avoid_sign *= -1
    elif hit_x or hit_y:
        enemy.vx *= 0.5
        enemy.vy *= 0.5


def _apply_knockback(enemy, dt: float, collision) -> None:
    if abs(enemy.knockback_x) < 0.5 and abs(enemy.knockback_y) < 0.5:
        enemy.knockback_x = enemy.knockback_y = 0.0
        return
    enemy.x, enemy.y, hit_x, hit_y = collision.move(
        enemy.x, enemy.y,
        enemy.knockback_x * dt, enemy.knockback_y * dt,
        enemy.half_w, enemy.half_h,
    )
    decay = ENEMY_KNOCKBACK_DECAY * dt
    enemy.knockback_x -= math.copysign(min(abs(enemy.knockback_x), decay),
                                       enemy.knockback_x)
    enemy.knockback_y -= math.copysign(min(abs(enemy.knockback_y), decay),
                                       enemy.knockback_y)
    if hit_x:
        enemy.knockback_x = 0.0
    if hit_y:
        enemy.knockback_y = 0.0


def _animate(enemy, dt: float) -> None:
    if enemy.state in (CHASE, PATROL):
        enemy.animator.play("walk", enemy.facing)
    elif enemy.state == IDLE:
        enemy.animator.play("idle", enemy.facing)
    enemy.animator.update(dt)
