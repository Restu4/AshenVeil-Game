"""Delta-time AI shared by every enemy archetype.

The state machine is archetype-driven: melee enemies chase, telegraph and swing;
ranged enemies keep their distance, retreat when crowded and fire a projectile.
All tuning comes from the ``Enemy`` instance (which copies it from
``enemy_config``), so this module never hard-codes a knight.

States
------
IDLE          wander around the home point / stand still
CHASE         close the distance or hold the preferred ranged band
ATTACK_WINDUP readable telegraph, no damage yet
ATTACK        the damage / projectile frame
RECOVERY      committed follow-through, cannot turn yet
RETREAT       ranged-only back-off after a shot or when crowded
HURT          short stagger
DEATH         corpse fade, then removal

``PATROL`` is kept as a compatibility alias for the old wander state.
"""
from __future__ import annotations

import math

IDLE = "IDLE"
PATROL = "PATROL"
CHASE = "CHASE"
ATTACK_WINDUP = "ATTACK_WINDUP"
ATTACK = "ATTACK"
RECOVERY = "RECOVERY"
RETREAT = "RETREAT"
HURT = "HURT"
DEATH = "DEATH"
DEAD = DEATH

ATTACK_STATES = frozenset((ATTACK_WINDUP, ATTACK, RECOVERY))

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


# ---------------------------------------------------------------------------
# Main update
# ---------------------------------------------------------------------------
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

    # Knockback carries through every living state.
    _apply_knockback(enemy, dt, collision)

    if enemy.state == HURT:
        enemy.hurt_timer -= dt
        if enemy.hurt_timer <= 0.0:
            enemy.state = CHASE if enemy.aggro_timer > 0.0 else IDLE
            enemy.patrol_target = None
        _animate(enemy, dt)
        return

    dx = player.x - enemy.x
    dy = player.y - enemy.y
    distance = math.hypot(dx, dy)
    player_dead = player.combat.dead

    # Detection and short-term memory.
    if not player_dead and distance <= enemy.detection:
        enemy.aggro_timer = enemy.memory
        enemy.alerted = True
        if enemy.state in (IDLE, PATROL):
            enemy.state = CHASE
            enemy.patrol_target = None
            enemy.facing = facing_from_delta(dx, dy, enemy.facing)

    # Leash so a pack does not follow the player across the whole village.
    home_distance = math.hypot(enemy.x - enemy.home_x, enemy.y - enemy.home_y)
    if enemy.aggro_timer > 0.0 and home_distance > enemy.leash:
        enemy.aggro_timer = 0.0
        enemy.state = IDLE
        enemy.patrol_target = None

    # Attack sequence is committed until recovery ends.
    if enemy.state in ATTACK_STATES:
        _update_attack_state(enemy, dt, player, collision, distance)
        _animate(enemy, dt)
        return

    if enemy.state == RETREAT:
        _update_retreat(enemy, dt, player, collision, dx, dy, distance)
        _animate(enemy, dt)
        return

    if not player_dead and enemy.aggro_timer > 0.0:
        if enemy.ranged:
            _update_ranged(enemy, dt, player, collision, dx, dy, distance)
        else:
            _update_melee(enemy, dt, player, collision, dx, dy, distance)
    else:
        _wander(enemy, dt, collision)

    _animate(enemy, dt)


# ---------------------------------------------------------------------------
# Melee
# ---------------------------------------------------------------------------
def _update_melee(enemy, dt, player, collision, dx, dy, distance) -> None:
    in_range = distance <= enemy.attack_range
    if (in_range and enemy.attack_cooldown <= 0.0 and enemy.can_attack
            and _line_clear(enemy, player, collision)):
        _start_attack(enemy, player, dx, dy)
        return

    enemy.state = CHASE
    hold = enemy.attack_range * (0.82 if enemy.can_attack else 1.28)
    if distance > hold:
        enemy.facing = facing_from_delta(dx, dy, enemy.facing)
        _steer(enemy, dt, collision, dx / max(distance, 0.001),
               dy / max(distance, 0.001), enemy.chase_speed)
    else:
        enemy.vx = enemy.vy = 0.0


# ---------------------------------------------------------------------------
# Ranged
# ---------------------------------------------------------------------------
def _update_ranged(enemy, dt, player, collision, dx, dy, distance) -> None:
    # Crowded: back off.  This is a state (not a nudge) so the retreat reads.
    if distance < enemy.retreat_distance:
        enemy.state = RETREAT
        enemy.state_time = 0.0
        enemy.retreat_timer = enemy.retreat_time
        return

    if (distance <= enemy.attack_range and enemy.attack_cooldown <= 0.0
            and enemy.can_attack and _line_clear(enemy, player, collision)):
        _start_attack(enemy, player, dx, dy)
        return

    enemy.state = CHASE
    enemy.facing = facing_from_delta(dx, dy, enemy.facing)
    desired = enemy.preferred_distance
    if distance > desired + 34.0:
        _steer(enemy, dt, collision, dx / max(distance, 0.001),
               dy / max(distance, 0.001), enemy.chase_speed)
    elif distance < desired - 18.0:
        _steer(enemy, dt, collision, -dx / max(distance, 0.001),
               -dy / max(distance, 0.001), enemy.retreat_speed)
    else:
        enemy.vx = enemy.vy = 0.0


def _update_retreat(enemy, dt, player, collision, dx, dy, distance) -> None:
    enemy.retreat_timer -= dt
    enemy.facing = facing_from_delta(dx, dy, enemy.facing)
    # Retreat only while the player is still too close; then reopen fire.
    if enemy.retreat_timer <= 0.0 or distance >= enemy.retreat_distance + 52.0:
        enemy.state = CHASE if enemy.aggro_timer > 0.0 else IDLE
        enemy.state_time = 0.0
        return
    _steer(enemy, dt, collision, -dx / max(distance, 0.001),
           -dy / max(distance, 0.001), enemy.retreat_speed)


# ---------------------------------------------------------------------------
# Attack sequence
# ---------------------------------------------------------------------------
def _start_attack(enemy, player, dx: float, dy: float) -> None:
    if not enemy.can_attack:
        return
    enemy.state = ATTACK_WINDUP
    enemy.state_time = 0.0
    enemy.attack_time = 0.0
    enemy.attack_hit_done = False
    enemy.attack_cooldown = enemy.attack_cooldown_max
    enemy.facing = facing_from_delta(dx, dy, enemy.facing)
    enemy.animator.play("attack", enemy.facing, restart=True)


def _update_attack_state(enemy, dt: float, player, collision,
                         distance: float) -> None:
    enemy.vx = enemy.vy = 0.0
    enemy.attack_time += dt
    windup_end = enemy.windup
    active_end = enemy.windup + enemy.active

    if enemy.state == ATTACK_WINDUP and enemy.attack_time >= windup_end:
        enemy.state = ATTACK
        enemy.state_time = 0.0
        if enemy.ranged:
            _fire_projectile(enemy, player, collision)
        else:
            _resolve_melee(enemy, player, collision, distance)

    elif enemy.state == ATTACK and enemy.attack_time >= active_end:
        enemy.state = RECOVERY
        enemy.state_time = 0.0

    elif enemy.state == RECOVERY and enemy.attack_time >= enemy.attack_total:
        if enemy.aggro_timer <= 0.0:
            enemy.state = IDLE
        elif enemy.ranged and distance < enemy.retreat_distance + 24.0:
            enemy.state = RETREAT
            enemy.retreat_timer = enemy.retreat_time
        else:
            enemy.state = CHASE
        enemy.patrol_target = None
        enemy.state_time = 0.0


def _resolve_melee(enemy, player, collision, distance: float) -> None:
    if enemy.attack_hit_done:
        return
    enemy.attack_hit_done = True
    fx, fy = FACING_VECTORS[enemy.facing]
    facing_dot = ((player.x - enemy.x) * fx + (player.y - enemy.y) * fy)
    facing_dot /= max(distance, 0.001)
    hit = False
    if (distance <= enemy.attack_range + 14.0
            and facing_dot > -0.15
            and not player.combat.invulnerable
            and not player.combat.dead):
        if not collision.segment_blocked(enemy.x, enemy.y - 18.0,
                                         player.x, player.y - 18.0, 3):
            player.take_damage(enemy.damage, enemy.x, enemy.y)
            hit = True
    # Consumed by the manager for a short swipe arc + light shake.
    enemy.pending_swipe = (enemy.x, enemy.y, enemy.facing, hit)


def _fire_projectile(enemy, player, collision) -> None:
    if enemy.attack_hit_done:
        return
    enemy.attack_hit_done = True
    dx = player.x - (enemy.x + 10.0)
    dy = (player.y - 18.0) - (enemy.y - 26.0)
    length = math.hypot(dx, dy) or 1.0
    nx, ny = dx / length, dy / length
    origin_x = enemy.x + nx * 16.0
    origin_y = enemy.y - 26.0 + ny * 8.0
    # A wall between caster and target means the shot is wasted on the wall.
    # Check the body-to-body line the AI uses, not the raised muzzle: a muzzle
    # offset can otherwise poke through a thin fence and fire past it.
    blocked = collision.segment_blocked(enemy.x, enemy.y - 18.0,
                                        player.x, player.y - 18.0, 3)
    enemy.pending_projectile = (origin_x, origin_y, nx, ny, blocked)


# ---------------------------------------------------------------------------
# Wandering / idle
# ---------------------------------------------------------------------------
def _wander(enemy, dt, collision) -> None:
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
           enemy.patrol_speed)


# ---------------------------------------------------------------------------
# Steering / knockback / animation
# ---------------------------------------------------------------------------
def _line_clear(enemy, player, collision) -> bool:
    return not collision.segment_blocked(enemy.x, enemy.y - 18.0,
                                         player.x, player.y - 18.0, 3)


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
    decay = enemy.knockback_decay * dt
    enemy.knockback_x -= math.copysign(min(abs(enemy.knockback_x), decay),
                                       enemy.knockback_x)
    enemy.knockback_y -= math.copysign(min(abs(enemy.knockback_y), decay),
                                       enemy.knockback_y)
    if hit_x:
        enemy.knockback_x = 0.0
    if hit_y:
        enemy.knockback_y = 0.0


def _animate(enemy, dt: float) -> None:
    if enemy.state in (CHASE, RETREAT, PATROL):
        enemy.animator.play("walk", enemy.facing)
    elif enemy.state == IDLE:
        enemy.animator.play("idle", enemy.facing)
    elif enemy.state in ATTACK_STATES:
        # Already started by _start_attack; do not restart every frame.
        enemy.animator.play("attack", enemy.facing)
    enemy.animator.update(dt)
