#!/usr/bin/env python3
"""Headless functional tests for the ASHEN VEIL hack & slash combat.

Run from the project root:

    python tools/test_combat.py

The SDL dummy driver is forced before pygame is imported.  Every assertion
below is a real check against the game code - no browser/display claims.
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame  # noqa: E402

from main import Game  # noqa: E402
from scripts import enemy_ai  # noqa: E402
from scripts.combat_config import COMBO_WINDOW, ENEMY_SEPARATION  # noqa: E402
from scripts.player_combat import (  # noqa: E402
    ATTACK_1,
    ATTACK_STATES,
    DASH_ATTACK,
    DODGE,
    IDLE,
    SHADOW_STEP,
)
from scripts.skill_config import SKILL_MAX_PARTICLES  # noqa: E402
from scripts.village_layout import ENEMY_SPAWNS, SPAWN  # noqa: E402

DT = 1.0 / 60.0
OPEN_GROUND = (1580.0, 1420.0)


class Keys:
    def __init__(self, *pressed: int) -> None:
        self.pressed = set(pressed)

    def __getitem__(self, key: int) -> bool:
        return key in self.pressed


EMPTY = Keys()
PASSED = 0


def check(condition: bool, message: str) -> None:
    global PASSED
    if not condition:
        raise AssertionError(message)
    PASSED += 1
    print(f"  ok  {message}")


def section(title: str) -> None:
    print(f"\n[{title}]")


def advance(game: Game, seconds: float, keys=EMPTY, watch=None) -> None:
    """Advance exactly like main.update, including hit stop."""
    player = game.player
    frames = max(1, int(round(seconds / DT)))
    for _ in range(frames):
        sim_dt = game.combat.consume_hit_stop(DT)
        player.update(sim_dt, keys, game.world.collision)
        game.combat.update(sim_dt)
        game.skills.update(sim_dt)
        game.effects.update(sim_dt)
        game.camera.update(sim_dt, player.x, player.y, *player.look)
        if watch is not None:
            watch(game)


def park_all(game: Game, keep=None) -> None:
    for index, enemy in enumerate(game.combat.enemies):
        if enemy is keep:
            continue
        enemy.x = enemy.home_x = 2920.0
        enemy.y = enemy.home_y = 1520.0 + index * 40.0
        enemy.state = enemy_ai.IDLE
        enemy.aggro_timer = 0.0
        enemy.patrol_target = None
        enemy.health.reset()
        enemy.removed = False


def freeze_enemies(game: Game) -> None:
    for enemy in game.combat.enemies:
        enemy.update = lambda *args, **kwargs: None


def duel(game: Game, offset_x: float = 68.0, facing: str = "right",
         base=OPEN_GROUND, crit: float = 0.0):
    """Fresh duel: one live knight parked in front of the player."""
    game.restart()
    game.combat.crit_chance = crit
    player = game.player
    player.x, player.y = base
    player.facing = facing
    player.input_x = player.input_y = 0.0
    knight = game.combat.enemies[0]
    park_all(game, keep=knight)
    knight.x = knight.home_x = player.x + offset_x
    knight.y = knight.home_y = player.y
    knight.state = enemy_ai.IDLE
    knight.aggro_timer = 0.0
    knight.attack_cooldown = 5.0
    knight.health.reset()
    freeze_enemies(game)
    game.camera.snap(player.x, player.y)
    return knight


def jump_to_stage(game: Game, stage: int) -> None:
    """Open the combo window so the next request starts ``stage``."""
    combat = game.player.combat
    combat.state = IDLE
    combat.attack_stage = stage - 1
    combat.attack_time = 0.0
    combat.combo_window = COMBO_WINDOW
    game.player.request_attack()


def drive_combo(game: Game, knight, max_seconds: float = 4.0):
    """Spam the attack button and record every stage and damage instance."""
    player = game.player
    record = {
        "stages": set(),
        "stages_seen": [],
        "hits": [],
        "attack_ids": set(),
        "shake": 0.0,
        "novas": 0,
        "crit": False,
        "hit_stop": 0.0,
        "flash": 0.0,
    }
    previous = knight.health.current
    player.request_attack()
    frames = int(max_seconds / DT)
    for _ in range(frames):
        if player.combat.state in ATTACK_STATES:
            player.request_attack()      # rapid buffering
        sim_dt = game.combat.consume_hit_stop(DT)
        player.update(sim_dt, EMPTY, game.world.collision)
        game.combat.update(sim_dt)
        game.effects.update(sim_dt)
        game.camera.update(sim_dt, player.x, player.y, *player.look)

        stage = player.combat.attack_stage
        record["stages"].add(stage)
        if not record["stages_seen"] or record["stages_seen"][-1] != stage:
            record["stages_seen"].append(stage)
        record["attack_ids"].add(player.combat.attack_id)
        record["shake"] = max(record["shake"], game.camera.shake_time)
        record["novas"] = max(record["novas"], len(game.effects.novas))
        record["hit_stop"] = max(record["hit_stop"], game.combat.hit_stop)
        record["flash"] = max(record["flash"], game.effects.flash_timer)
        record["crit"] = record["crit"] or player.combat.crit_flash > 0.0
        if knight.health.current < previous - 0.01:
            record["hits"].append(round(previous - knight.health.current, 1))
            previous = knight.health.current
        if (player.combat.combo_count >= 5
                and player.combat.state not in ATTACK_STATES):
            break
    return record


def main() -> None:
    game = Game()
    game.hud.time = 9.0

    # ------------------------------------------------------------------
    section("Player movement, run, collision and camera")
    game.restart()
    start = game.player.x
    advance(game, 1.0, Keys(pygame.K_d))
    walked = game.player.x - start
    check(walked > 80.0, f"walking moved the player ({walked:.1f} px)")
    start = game.player.x
    advance(game, 1.0, Keys(pygame.K_d, pygame.K_LSHIFT))
    ran = game.player.x - start
    check(ran > walked * 1.25, f"running is faster ({ran:.1f} > {walked:.1f})")
    check(game.player.state == "RUN", "running exposes the RUN state")
    check(not hasattr(game.player, "stamina"),
          "stamina pool is gone; running is unrestricted")
    game.player.x, game.player.y = 760.0, 1420.0
    game.player.vx = game.player.vy = 0.0
    start = game.player.x
    advance(game, 2.4, Keys(pygame.K_d, pygame.K_LSHIFT))
    check(game.player.state == "RUN" and game.player.running
          and game.player.x - start > 300.0,
          f"running never runs out of stamina ({game.player.x - start:.0f} px)")
    advance(game, 0.5, Keys(pygame.K_a))
    check(game.player.state == "WALK", "walking exposes the WALK state")
    advance(game, 0.2)
    check(game.player.state == "IDLE", "releasing input returns to IDLE")

    player = game.player
    player.x, player.y = 1075.0, 1250.0
    player.vx = player.vy = 0.0
    advance(game, 1.2, Keys(pygame.K_w))
    check(player.y > 1000.0,
          f"house still blocks movement (y={player.y:.1f})")

    player.x, player.y = 60.0, 60.0
    game.camera.snap(player.x, player.y)
    advance(game, 0.1)
    ox, oy = game.camera.offset
    check(0 <= ox <= 3200 - 1280 and 0 <= oy <= 2400 - 720,
          f"camera stays clamped ({ox},{oy})")

    # ------------------------------------------------------------------
    section("Five-hit combo: damage, stages, buffering and effects")
    knight = duel(game)
    knight.health.maximum = 1000.0
    knight.health.reset()
    player = game.player
    player.request_attack()
    check(player.combat.state == ATTACK_1, "LMB starts ATTACK_1")
    check(not hasattr(player, "stamina"), "attacks are not stamina gated")
    record = drive_combo(game, knight)
    check(record["hits"] == [20.0, 22.0, 25.0, 30.0, 45.0],
          f"five hits deal 20/22/25/30/45 ({record['hits']})")
    check({1, 2, 3, 4, 5}.issubset(record["stages"]),
          f"all five combo states were reached ({sorted(record['stages'])})")
    check(record["stages_seen"] == [1, 2, 3, 4, 5, 0],
          f"combo advances one link at a time ({record['stages_seen']})")
    check(len(record["attack_ids"]) <= 6,
          f"buffered input never stacks animations ({len(record['attack_ids'])})")
    check(player.combat.combo_count == 5,
          f"combo counter tracks the five landed swings ({player.combat.combo_count})")
    check(record["shake"] > 0.0, "heavy links shake the camera lightly")
    check(record["novas"] > 0, "spin/finisher spawned a radial nova")
    check(record["hit_stop"] > 0.0, "hits trigger hit stop")
    check(record["flash"] > 0.0, "heavy strikes add a purple flash")
    check(player.combat.state == IDLE, "combo recovers to IDLE")
    check(len(game.effects.particles) <= 200,
          f"particle list stays capped ({len(game.effects.particles)})")

    # Rapid clicks in a single instant must not skip links or stack attacks.
    knight = duel(game)
    player = game.player
    for _ in range(24):
        player.request_attack()
    check(player.combat.state == ATTACK_1 and player.combat.attack_id == 1,
          "24 rapid clicks start exactly one swing")
    advance(game, 0.05)
    for _ in range(24):
        player.request_attack()
    advance(game, 1.6)
    check(player.combat.attack_stage <= 5,
          f"rapid input cannot exceed stage 5 ({player.combat.attack_stage})")
    check(player.combat.state in ATTACK_STATES or player.combat.state == IDLE,
          "rapid input leaves a valid combat state")

    # Combo auto reset after inactivity.
    advance(game, 0.33)
    check(player.combat.state == IDLE and player.combat.combo_buffer is False,
          "buffered clicks clear after the combo ends")
    advance(game, 2.6)
    check(player.combat.combo_count == 0 and player.combat.attack_stage == 0,
          "combo count and stage reset after inactivity")

    # ------------------------------------------------------------------
    section("Multi-enemy damage: one hit per enemy per swing")
    game.restart()
    game.combat.crit_chance = 0.0
    player = game.player
    player.x, player.y = OPEN_GROUND
    player.facing = "right"
    trio = game.combat.enemies[:3]
    spots = ((60.0, 0.0), (-52.0, 4.0), (0.0, -56.0))
    for enemy, (dx, dy) in zip(trio, spots):
        enemy.x = enemy.home_x = player.x + dx
        enemy.y = enemy.home_y = player.y + dy
        enemy.state = enemy_ai.CHASE
        enemy.aggro_timer = 3.0
        enemy.attack_cooldown = 5.0
        enemy.health.reset()
    park_all_except = [e for e in game.combat.enemies[3:]]
    for index, enemy in enumerate(park_all_except):
        enemy.x = enemy.home_x = 2920.0
        enemy.y = enemy.home_y = 1000.0 + index * 40.0
    freeze_enemies(game)
    game.camera.snap(player.x, player.y)

    jump_to_stage(game, 4)
    advance(game, 0.5)
    check(all(math.isclose(e.health.current, 70.0) for e in trio),
          f"stage 4 spin hits all three knights for 30 "
          f"({[e.health.current for e in trio]})")
    check(player.combat.combo_count == 1,
          "one swing registers one combo hit even against three enemies")
    check(len(game.combat._hit_enemies) == 3,
          "swing bookkeeping records each enemy exactly once")

    advance(game, 0.12)
    check(all(math.isclose(e.health.current, 70.0) for e in trio),
          "the same swing cannot damage an enemy twice")

    jump_to_stage(game, 5)
    advance(game, 0.6)
    check(all(math.isclose(e.health.current, 25.0) for e in trio),
          f"stage 5 finisher hits the whole ring for 45 "
          f"({[e.health.current for e in trio]})")
    check(player.combat.attack_stage == 0,
          "finisher ends the combo chain")

    # ------------------------------------------------------------------
    section("Knockback follows the attack direction")
    knight = duel(game, offset_x=50.0)
    player = game.player
    player.request_attack()
    advance(game, 0.25)
    check(knight.health.current == 80.0,
          f"first sword hit lands ({knight.health.current})")
    check(knight.knockback_x > 0.0 and abs(knight.knockback_y) < 1e-6,
          f"forward slash pushes along its facing "
          f"({knight.knockback_x:.1f},{knight.knockback_y:.1f})")

    knight = duel(game, offset_x=44.0)
    knight.y = knight.home_y = player.y + 16.0
    player.facing = "right"
    player.request_attack()
    advance(game, 0.25)
    check(knight.health.current == 80.0, "off-axis enemy still hit by the arc")
    check(knight.knockback_y == 0.0,
          "knockback does not radiate from the player on an arc swing")

    # ------------------------------------------------------------------
    section("Critical hits")
    knight = duel(game, crit=1.0)
    player = game.player
    player.request_attack()
    advance(game, 0.3)
    check(knight.health.current == 66.0,
          f"guaranteed crit deals 34 (20 x 1.7) ({knight.health.current})")
    check(player.combat.crit_flash > 0.0, "crit lights the HUD critical flash")
    check(len(game.effects.numbers) > 0,
          "crit damage number was spawned")

    # ------------------------------------------------------------------
    section("Hit stop freezes the simulation briefly")
    knight = duel(game, crit=0.0)
    player = game.player
    player.request_attack()
    advance(game, 0.08)
    check(game.combat.hit_stop > 0.0,
          f"a connected hit queues hit stop ({game.combat.hit_stop:.3f}s)")
    frozen_x = knight.x
    frozen_state = knight.state
    advance(game, DT)
    check(knight.x == frozen_x and knight.state == frozen_state,
          "the frozen frame does not advance enemy simulation")
    check(game.combat.consume_hit_stop(DT) >= 0.0,
          "hit stop keeps draining without going negative")

    # ------------------------------------------------------------------
    section("Dodge: i-frames, travel, cooldown and no resource cost")
    game.restart()
    game.combat.crit_chance = 0.0
    for enemy in game.combat.enemies:
        enemy.x = enemy.home_x = 2920.0
        enemy.y = enemy.home_y = 1520.0
    player = game.player
    player.x, player.y = OPEN_GROUND
    player.facing = "right"
    player.input_x, player.input_y = 1.0, 0.0
    player.request_dodge()
    check(player.combat.state == DODGE, "SPACE starts DODGE")
    check(player.combat.invulnerable, "dodge grants i-frames")
    check(not player.take_damage(15.0, 1500.0, 1420.0),
          "damage is ignored during i-frames")
    before = player.x
    advance(game, 0.3)
    check(player.x - before > 55.0,
          f"dodge travels in the input direction ({player.x - before:.1f} px)")
    check(player.combat.state != DODGE, "dodge cannot permanently lock movement")
    advance(game, 0.12)
    player.request_dodge()
    check(player.combat.state == DODGE, "dodge is ready again after its cooldown")
    check(not hasattr(player, "stamina"), "dodge never touches a stamina pool")

    # ------------------------------------------------------------------
    section("Dash attack: burst, front damage, cooldown and walls")
    knight = duel(game, offset_x=62.0, crit=0.0)
    player = game.player
    player.input_x, player.input_y = 1.0, 0.0
    start_x = player.x
    player.request_dash()
    check(player.combat.state == DASH_ATTACK, "E starts the dash attack")
    check(player.combat.invulnerable, "dash grants a brief i-frame window")
    advance(game, 0.45)
    check(player.x - start_x > 60.0,
          f"dash bursts forward ({player.x - start_x:.1f} px)")
    check(knight.health.current == 74.0,
          f"dash strike deals 26 in front ({knight.health.current})")
    check(player.combat.state != DASH_ATTACK,
          "dash recovers into normal movement")
    player.request_dash()
    check(player.combat.state != DASH_ATTACK,
          "dash is refused while its cooldown runs")

    # Dash into the plaza wall: the player slides to a stop, never teleports.
    game.restart()
    game.combat.crit_chance = 0.0
    for enemy in game.combat.enemies:
        enemy.x = enemy.home_x = 2920.0
        enemy.y = enemy.home_y = 1520.0
    player = game.player
    player.x, player.y = 1600.0, 1368.0
    player.facing = "up"
    player.input_x, player.input_y = 0.0, -1.0
    start_y = player.y
    player.request_dash()
    advance(game, 0.45)
    rect = pygame.Rect(int(player.x - 12), int(player.y - 9), 24, 18)
    check(player.y > 1335.0,
          f"dash cannot pass through the house wall (y={player.y:.1f})")
    check(game.world.collision.rect_free(rect),
          "dash never leaves the player inside a solid")
    check(player.y < start_y, "dash still made progress before the wall")

    # ------------------------------------------------------------------
    section("Player health, invulnerability, death and restart")
    game.restart()
    game.combat.crit_chance = 0.0
    for enemy in game.combat.enemies:
        enemy.x = enemy.home_x = 2920.0
        enemy.y = enemy.home_y = 1520.0
    player = game.player
    check(player.take_damage(15.0, 1500.0, 1420.0), "enemy hit damages the player")
    check(player.health == 85.0, f"damage is applied (HP {player.health})")
    check(player.combat.state == "HURT", "player enters HURT")
    check(not player.take_damage(15.0, 1500.0, 1420.0),
          "post-hit invulnerability blocks a second hit")
    advance(game, 0.9)
    check(player.take_damage(15.0, 1500.0, 1420.0),
          "player can be hit again after i-frames")
    check(player.health == 70.0, "HP never exceeds maximum and tracks damage")
    player.health = 10.0
    player.combat.invuln = 0.0
    player.take_damage(15.0, 1500.0, 1420.0)
    check(player.health == 0.0, "lethal damage clamps HP to zero")
    check(player.combat.dead and player.combat.state == "DEAD",
          "player enters DEAD state")
    dead_x = player.x
    player.request_attack()
    player.request_dodge()
    advance(game, 0.6, Keys(pygame.K_d))
    check(player.combat.state == "DEAD", "dead player cannot attack or dodge")
    check(player.x == dead_x, "dead player cannot move")
    game.draw()
    check(game.canvas.get_width() == 1280, "death overlay renders without error")
    game.restart()
    check(player.health == 100.0 and player.combat.state == IDLE,
          "restart restores health and state")
    check(len(game.combat.enemies) == len(ENEMY_SPAWNS),
          f"restart respawns all {len(ENEMY_SPAWNS)} knights")
    check(math.isclose(player.x, SPAWN[0]) and math.isclose(player.y, SPAWN[1]),
          "restart returns the player to the spawn")
    check(not (ROOT / "scripts" / "stamina.py").exists(),
          "the obsolete stamina module was removed")

    # ------------------------------------------------------------------
    section("Fallen Knight: detection, chase and readable attacks")
    game.restart()
    game.combat.crit_chance = 0.0
    player = game.player
    player.x, player.y = 1500.0, 1200.0
    knight = game.combat.enemies[0]
    park_all(game, keep=knight)
    knight.x = knight.home_x = 1650.0
    knight.y = knight.home_y = 1200.0
    knight.state = enemy_ai.IDLE
    knight.aggro_timer = 0.0
    knight.attack_cooldown = 5.0
    start_distance = math.hypot(knight.x - player.x, knight.y - player.y)
    advance(game, 1.0)
    end_distance = math.hypot(knight.x - player.x, knight.y - player.y)
    check(knight.aggro_timer > 0.0, "knight detects the player")
    check(knight.state in (enemy_ai.CHASE, enemy_ai.ATTACK),
          f"knight transitions to aggression ({knight.state})")
    check(end_distance < start_distance - 25.0,
          f"knight chases and closes distance ({start_distance:.0f}->{end_distance:.0f})")

    knight.x = knight.home_x = player.x + 34.0
    knight.y = knight.home_y = player.y
    knight.state = enemy_ai.CHASE
    knight.aggro_timer = 3.0
    knight.attack_cooldown = 0.0
    player.combat.invuln = 0.0
    hp_before = player.health
    advance(game, 0.08)
    check(knight.state == enemy_ai.ATTACK, "knight attacks when the token is free")
    advance(game, 0.40)
    check(player.health == hp_before - 12.0,
          f"knight attack deals 12 ({player.health})")
    advance(game, 0.45)
    check(player.health == hp_before - 12.0,
          "one attack animation only applies damage once")
    check(knight.animator.current_name.startswith("attack")
          or knight.state != enemy_ai.ATTACK,
          "a readable attack animation was played")

    # Roll behind the knight during the wind-up: the arc misses.
    player.x, player.y = knight.x + 34.0, knight.y
    player.combat.invuln = 0.0
    knight.facing = "right"
    knight.state = enemy_ai.CHASE
    knight.aggro_timer = 3.0
    knight.attack_cooldown = 0.0
    advance(game, 0.05)
    check(knight.state == enemy_ai.ATTACK, "second knight swing winds up")
    hp_before = player.health
    player.x = knight.x - 34.0
    advance(game, 0.40)
    check(player.health == hp_before,
          "knight swing misses a player who moved behind it")

    # ------------------------------------------------------------------
    section("Enemy pack: one attack token, no simultaneous blows, separation")
    game.restart()
    game.combat.crit_chance = 0.0
    player = game.player
    player.x, player.y = OPEN_GROUND
    trio = game.combat.enemies[:3]
    ring = ((36.0, 0.0), (-36.0, 0.0), (0.0, -38.0))
    for enemy, (dx, dy) in zip(trio, ring):
        enemy.x = enemy.home_x = player.x + dx
        enemy.y = enemy.home_y = player.y + dy
        enemy.state = enemy_ai.CHASE
        enemy.aggro_timer = 5.0
        enemy.attack_cooldown = 0.0
        enemy.health.reset()
    for index, enemy in enumerate(game.combat.enemies[3:]):
        enemy.x = enemy.home_x = 2920.0
        enemy.y = enemy.home_y = 1000.0 + index * 40.0
    simult = [0]
    attacks_started = set()

    def watch_gate(g):
        active = [e for e in g.combat.enemies
                  if e.alive and e.state == enemy_ai.ATTACK]
        simult[0] = max(simult[0], len(active))
        for enemy in active:
            attacks_started.add(enemy.id)

    advance(game, 3.0, watch=watch_gate)
    check(simult[0] <= 1,
          f"at most one knight winds up at a time (max {simult[0]})")
    check(len(attacks_started) >= 1, "the pack still attacks the player")

    # Two frozen knights dropped on the same spot get pushed apart.
    game.restart()
    pair = game.combat.enemies[:2]
    pair[0].x = pair[0].home_x = 1600.0
    pair[0].y = pair[0].home_y = 1420.0
    pair[1].x = pair[1].home_x = 1600.0
    pair[1].y = pair[1].home_y = 1420.0
    freeze_enemies(game)
    for _ in range(40):
        game.combat.update(DT)
    gap = math.hypot(pair[0].x - pair[1].x, pair[0].y - pair[1].y)
    check(gap >= ENEMY_SEPARATION - 1.0,
          f"separation pushes overlapping knights apart ({gap:.1f} px)")

    # ------------------------------------------------------------------
    section("Fallen Knight: patrol, hurt, knockback and death")
    game.restart()
    game.combat.crit_chance = 0.0
    player = game.player
    player.x, player.y = 600.0, 600.0
    knight = game.combat.enemies[0]
    park_all(game, keep=knight)
    knight.x, knight.y = 1740.0, 1200.0
    knight.home_x, knight.home_y = 1740.0, 1200.0
    knight.state = enemy_ai.IDLE
    knight.aggro_timer = 0.0
    advance(game, 2.0)
    check(knight.state in (enemy_ai.IDLE, enemy_ai.PATROL),
          f"knight patrols/idles when the player is far ({knight.state})")
    home_distance = math.hypot(knight.x - knight.home_x,
                               knight.y - knight.home_y)
    check(home_distance <= knight.patrol_radius + 25.0,
          f"patrol stays within its radius ({home_distance:.0f} px)")

    player.x, player.y = knight.x - 50.0, knight.y
    knight.health.reset()
    knight.state = enemy_ai.CHASE
    knight.aggro_timer = 3.0
    before_x = knight.x
    lost, killed = knight.take_damage(25.0, player.x, player.y, 110.0)
    check(lost == 25.0 and not killed and knight.health.current == 75.0,
          "knight takes sword damage")
    check(knight.state == enemy_ai.HURT, "knight enters HURT")
    check(abs(knight.knockback_x) > 0.0, "knockback is applied")
    advance(game, 0.18)
    check(knight.x > before_x,
          f"knockback moves the knight away ({knight.x - before_x:.1f} px)")
    advance(game, 0.30)
    check(knight.state not in (enemy_ai.HURT, enemy_ai.DEATH),
          f"knight recovers from the hit ({knight.state})")
    lost, killed = knight.take_damage(999.0, player.x, player.y, 120.0)
    check(killed and knight.health.current == 0.0, "lethal hit kills the knight")
    check(knight.state == enemy_ai.DEATH, "death state starts")
    advance(game, 1.3)
    check(knight not in game.combat.enemies,
          "dead knight is removed after its death animation")

    # ------------------------------------------------------------------
    section("World obstruction and enemy collision")
    game.restart()
    game.combat.crit_chance = 0.0
    player = game.player
    player.x, player.y = 2300.0, 1870.0
    knight = game.combat.enemies[0]
    park_all(game, keep=knight)
    knight.x = knight.home_x = 2300.0
    knight.y = knight.home_y = 1940.0
    knight.state = enemy_ai.IDLE
    knight.attack_cooldown = 5.0
    freeze_enemies(game)
    player.facing = "down"
    player.request_attack()
    advance(game, 0.55)
    check(knight.health.current == 100.0,
          "sword cannot cut through a stone wall")
    check(game.world.collision.segment_blocked(2300, 1870, 2300, 1940, 2.0),
          "collision segment detects the stone wall")
    check(not game.world.collision.segment_blocked(1600, 1250, 1660, 1250, 2.0),
          "open plaza has clear line of sight")

    game.restart()
    game.combat.crit_chance = 0.0
    player = game.player
    player.x, player.y = 1075.0, 1150.0
    knight = game.combat.enemies[0]
    park_all(game, keep=knight)
    knight.x = knight.home_x = 1075.0
    knight.y = knight.home_y = 985.0
    knight.state = enemy_ai.CHASE
    knight.aggro_timer = 5.0
    knight.attack_cooldown = 5.0
    overlapping = []

    def watch_collision(g):
        if not g.world.collision.rect_free(knight.hit_rect):
            overlapping.append((knight.x, knight.y))

    advance(game, 3.0, watch=watch_collision)
    check(not overlapping, "knight never stands inside a building footprint")
    check(knight.y < 1010.0,
          f"knight cannot walk through the house (y={knight.y:.0f})")

    # ------------------------------------------------------------------
    section("Void Essence: energy pool, regeneration and kill rewards")
    game.restart()
    park_all(game)
    freeze_enemies(game)
    skills = game.skills
    check(skills.energy.maximum == 100.0 and skills.energy.current == 100.0,
          "void energy starts full at 100/100")
    check(skills.energy is not game.player.vitality,
          "void energy is a separate resource from HP")
    skills.energy.regen = 8.0
    skills.energy.current = 50.0
    advance(game, 1.0)
    check(math.isclose(skills.energy.current, 58.0, abs_tol=0.2),
          f"energy regenerates 8/s with delta time ({skills.energy.current:.1f})")
    skills.energy.current = 97.0
    advance(game, 1.0)
    check(skills.energy.current == 100.0,
          "energy regeneration clamps at the maximum")
    check(not skills.energy.spend(150.0) and skills.energy.current == 100.0,
          "energy can never be spent below zero")
    check(skills.energy.spend(20.0) and skills.energy.current == 80.0,
          "energy spend subtracts exactly the cost")
    skills.energy.gain(999.0)
    check(skills.energy.current == 100.0, "energy gain clamps at the maximum")

    skills.energy.regen = 0.0
    skills.energy.current = 50.0
    controller = game.combat.enemies[0]
    controller.health.current = 10.0
    lost, killed = game.combat.damage_enemy(
        controller, 999.0, controller.x - 30.0, controller.y, 0.0)
    check(lost > 0.0 and killed, "combat manager can kill through the skill API")
    check(math.isclose(skills.energy.current, 58.0),
          f"an enemy kill rewards 8 void energy ({skills.energy.current:.1f})")

    # Sword kills feed the same reward hook.
    knight = duel(game, offset_x=50.0, crit=0.0)
    game.skills.energy.regen = 0.0
    game.skills.energy.current = 50.0
    game.player.request_attack()
    knight.health.current = 15.0
    advance(game, 0.3)
    check(knight.health.dead and math.isclose(game.skills.energy.current, 58.0),
          f"sword kills also reward void energy ({game.skills.energy.current:.1f})")

    # ------------------------------------------------------------------
    section("VOID BURST (Q): radial damage, cost, cooldown and one hit per cast")
    game.restart()
    game.combat.crit_chance = 0.0
    skills = game.skills
    skills.energy.regen = 0.0
    player = game.player
    player.x, player.y = OPEN_GROUND
    player.facing = "right"
    park_all(game)
    trio = game.combat.enemies[:3]
    spots = ((60.0, 0.0), (-52.0, 4.0), (0.0, -56.0))
    for enemy, (dx, dy) in zip(trio, spots):
        enemy.x = enemy.home_x = player.x + dx
        enemy.y = enemy.home_y = player.y + dy
        enemy.health.reset()
        enemy.attack_cooldown = 5.0
    outside = game.combat.enemies[3]
    outside.x = outside.home_x = player.x + 240.0
    outside.y = outside.home_y = player.y
    outside.health.reset()
    freeze_enemies(game)
    game.camera.snap(player.x, player.y)
    hp_before = player.health
    skills.energy.current = 100.0
    check(skills.cast_burst(), "Q casts VOID BURST")
    check(math.isclose(skills.energy.current, 80.0),
          f"void burst costs 20 energy ({skills.energy.current:.1f})")
    check(player.combat.casting, "the burst plays a short cast lock")
    check(all(math.isclose(e.health.current, 65.0) for e in trio),
          f"burst deals 35 to every nearby knight "
          f"({[e.health.current for e in trio]})")
    check(outside.health.current == 100.0,
          "burst radius stops at 110 px")
    check(trio[0].knockback_x > 0.0 and trio[1].knockback_x < 0.0,
          "burst knockback radiates outward from the player")
    check(trio[2].knockback_y < 0.0,
          "vertical targets are pushed away on the y axis")
    check(len(game.effects.numbers) >= 3,
          "burst spawns damage numbers through the existing effect system")
    check(skills.burst.timer > 2.9,
          f"burst starts its 3 s cooldown ({skills.burst.timer:.2f})")
    check(not skills.cast_burst(), "burst is refused during its cooldown")
    advance(game, 0.3)
    check(all(math.isclose(e.health.current, 65.0) for e in trio),
          "one burst cast never damages the same enemy twice")
    check(player.health == hp_before, "void magic never damages the player")
    skills.energy.current = 19.0
    skills.burst.timer = 0.0
    check(not skills.cast_burst() and math.isclose(skills.energy.current, 19.0),
          "insufficient energy blocks the burst without spending")
    check(all(math.isclose(e.health.current, 65.0) for e in trio),
          "a failed cast deals no damage")

    # ------------------------------------------------------------------
    section("SHADOW STEP (E): dash, i-frames, collision and cooldown")
    game.restart()
    skills = game.skills
    skills.energy.regen = 0.0
    player = game.player
    park_all(game)
    freeze_enemies(game)
    player.x, player.y = OPEN_GROUND
    player.facing = "right"
    player.input_x, player.input_y = 1.0, 0.0
    skills.energy.current = 100.0
    check(skills.cast_shadow(), "E casts SHADOW STEP")
    check(math.isclose(skills.energy.current, 85.0),
          f"shadow step costs 15 energy ({skills.energy.current:.1f})")
    check(player.combat.state == SHADOW_STEP,
          f"shadow step enters its own state ({player.combat.state})")
    check(player.combat.invulnerable, "shadow step grants brief i-frames")
    check(not player.take_damage(15.0, 1500.0, 1420.0),
          "damage is ignored during shadow step")
    check(len(skills.skill_effects.afterimages) >= 1,
          "shadow step spawned a purple afterimage")
    before = player.x
    advance(game, 0.30)
    check(player.x - before > 100.0,
          f"shadow step travels quickly ({player.x - before:.1f} px)")
    check(player.combat.state != SHADOW_STEP,
          "shadow step releases control after its duration")
    check(skills.shadow.timer > 1.6,
          f"shadow step starts its 2 s cooldown ({skills.shadow.timer:.2f})")
    check(not skills.cast_shadow(), "shadow step is refused during cooldown")

    game.restart()
    skills = game.skills
    skills.energy.regen = 0.0
    player = game.player
    park_all(game)
    freeze_enemies(game)
    player.x, player.y = 1600.0, 1368.0
    player.facing = "up"
    player.input_x, player.input_y = 0.0, -1.0
    skills.energy.current = 100.0
    start_y = player.y
    check(skills.cast_shadow(), "shadow step can be cast near a wall")
    advance(game, 0.40)
    rect = pygame.Rect(int(player.x - 12), int(player.y - 9), 24, 18)
    check(player.y > 1335.0,
          f"shadow step cannot pass through the house wall (y={player.y:.1f})")
    check(game.world.collision.rect_free(rect),
          "shadow step never leaves the player inside a solid")
    check(player.y < start_y, "shadow step still made progress before the wall")

    # ------------------------------------------------------------------
    section("VOID SLASH (R): travelling wave, multi-hit, range and cooldown")
    game.restart()
    game.combat.crit_chance = 0.0
    skills = game.skills
    skills.energy.regen = 0.0
    player = game.player
    player.x, player.y = OPEN_GROUND
    player.facing = "right"
    park_all(game)
    near, far, behind = game.combat.enemies[:3]
    near.x = near.home_x = player.x + 120.0
    near.y = near.home_y = player.y
    far.x = far.home_x = player.x + 250.0
    far.y = far.home_y = player.y
    behind.x = behind.home_x = player.x - 120.0
    behind.y = behind.home_y = player.y
    for enemy in (near, far, behind):
        enemy.health.reset()
        enemy.attack_cooldown = 5.0
    freeze_enemies(game)
    game.camera.snap(player.x, player.y)
    hp_before = player.health
    skills.energy.current = 100.0
    check(skills.cast_slash(), "R casts VOID SLASH")
    check(math.isclose(skills.energy.current, 75.0),
          f"void slash costs 25 energy ({skills.energy.current:.1f})")
    check(len(skills.slash.waves) == 1, "one travelling wave was spawned")
    check(player.combat.casting, "void slash commits the player to a swing")
    advance(game, 0.55)
    check(math.isclose(near.health.current, 55.0),
          f"the wave hits the first knight for 45 ({near.health.current})")
    check(math.isclose(far.health.current, 55.0),
          f"the wave keeps travelling into the next knight ({far.health.current})")
    check(behind.health.current == 100.0,
          "the wave never damages enemies behind the player")
    check(near.knockback_x > 0.0,
          "the wave knocks enemies along its travel direction")
    advance(game, 0.6)
    check(not skills.slash.waves,
          "the wave disappears after its 320 px range")
    check(math.isclose(near.health.current, 55.0)
          and math.isclose(far.health.current, 55.0),
          "each enemy is hit only once per wave")
    check(skills.slash.timer > 0.0 and not skills.cast_slash(),
          "void slash is refused during its 5 s cooldown")
    check(player.health == hp_before, "void slash never hurts the player")

    # ------------------------------------------------------------------
    section("ECLIPSE (F): wind-up, ultimate damage, knockback and lockout")
    game.restart()
    game.combat.crit_chance = 0.0
    skills = game.skills
    skills.energy.regen = 0.0
    player = game.player
    player.x, player.y = OPEN_GROUND
    player.facing = "right"
    park_all(game)
    near, far = game.combat.enemies[:2]
    near.x = near.home_x = player.x + 140.0
    near.y = near.home_y = player.y
    far.x = far.home_x = player.x + 400.0
    far.y = far.home_y = player.y
    near.health.reset()
    far.health.reset()
    freeze_enemies(game)
    game.camera.snap(player.x, player.y)
    hp_before = player.health
    skills.energy.current = 100.0
    check(skills.cast_eclipse(), "F begins the ECLIPSE ultimate")
    check(math.isclose(skills.energy.current, 40.0),
          f"eclipse costs 60 energy ({skills.energy.current:.1f})")
    check(skills.eclipse.charging and player.combat.casting,
          "eclipse locks the player into a visible wind-up")
    check(math.isclose(skills.eclipse.timer, 18.0),
          f"eclipse applies its 18 s cooldown on cast ({skills.eclipse.timer:.1f})")
    cooldown_at_cast = skills.eclipse.timer
    check(near.health.current == 100.0,
          "eclipse deals no damage before the wind-up finishes")
    skills.energy.current = 100.0
    skills.eclipse.timer = 0.0
    check(not skills.cast_eclipse(),
          "eclipse cannot trigger again while its animation is active")
    skills.eclipse.timer = cooldown_at_cast
    skills.energy.current = 0.0
    advance(game, 0.66)
    check(not skills.eclipse.charging, "eclipse detonates after the wind-up")
    check(near.health.current == 0.0,
          f"eclipse deals 100 damage in its radius ({near.health.current})")
    check(far.health.current == 100.0,
          "eclipse radius stops at 220 px")
    check(math.isclose(skills.energy.current, 8.0),
          f"the ultimate kill rewards 8 energy ({skills.energy.current:.1f})")
    check(skills.skill_effects.dark_timer > 0.0,
          "eclipse darkens the screen after detonation")
    check(game.camera.shake_time > 0.0, "eclipse shakes the camera")
    check(skills.eclipse.timer > 17.0,
          f"eclipse starts its 18 s cooldown ({skills.eclipse.timer:.1f})")
    check(not skills.cast_eclipse(), "eclipse is refused after detonation")
    check(player.health == hp_before, "eclipse never damages the player")
    game.draw()
    check(len(skills.skill_effects.particles) <= SKILL_MAX_PARTICLES,
          f"skill particles stay capped ({len(skills.skill_effects.particles)})")

    # ------------------------------------------------------------------
    section("Void Essence HUD: energy bar, four slots, cooldown and disabled")
    game.restart()
    skills = game.skills
    player = game.player
    check(game.hud.skill_hud is not None, "the HUD owns a Void Essence panel")
    check([skill.key for skill in skills.skills] == ["Q", "E", "R", "F"],
          f"four skill slots expose their keys "
          f"({[skill.key for skill in skills.skills]})")
    check([skill.cost for skill in skills.skills] == [20.0, 15.0, 25.0, 60.0],
          "skill slots expose their energy costs")
    game.hud.draw(game.canvas, player, game.combat, game.camera, skills)
    px = game.canvas.get_at((64, 154))[:3]
    check(px[2] > px[0] and px[2] > 60,
          f"the void energy bar renders purple when full ({px})")
    skills.energy.current = 0.0
    skills.burst.timer = 3.0
    skills.eclipse.pending = {"x": player.x, "y": player.y,
                              "timer": 0.2, "hit": set()}
    game.hud.draw(game.canvas, player, game.combat, game.camera, skills)
    px = game.canvas.get_at((64, 154))[:3]
    check(px[2] < 60, f"an empty energy bar drains the purple fill ({px})")
    check(game.canvas.get_size() == (1280, 720),
          "the skill HUD renders inside the existing resolution")
    check(skills.energy.current == 0.0 and not skills.energy.can_afford(15.0),
          "an empty pool disables every skill")
    game.draw()
    check(game.canvas.get_at((0, 0))[:3] != (0, 0, 0),
          "full frame with skill HUD and disabled slots renders")

    # ------------------------------------------------------------------
    section("Rendering: HUD, combo readout, enemy bars and debug overlays")
    game.restart()
    game.combat.crit_chance = 0.0
    knight = duel(game, offset_x=56.0)
    player = game.player
    player.request_attack()
    advance(game, 0.12)
    player.combat.combo_count = 3
    player.combat.combo_decay = 1.5
    player.combat.attack_stage = 3
    game.draw()
    game.debug = True
    game.draw()
    game.debug = False
    game.hud.draw(game.canvas, game.player, game.combat, game.camera,
                  game.skills)
    check(game.canvas.get_size() == (1280, 720),
          "full combat frame renders at the internal resolution")
    check(game.canvas.get_at((0, 0))[:3] != (0, 0, 0),
          "canvas contains a rendered frame")
    check(game.hud.combat_ui._combo_panel is not None,
          "combo panel exists in the cached combat UI")
    check(game.hud.skill_hud._panel is not None,
          "void essence panel is cached, not rebuilt per frame")

    # ------------------------------------------------------------------
    section("Input events and the async browser loop")
    game.restart()
    for enemy in game.combat.enemies:
        enemy.x = enemy.home_x = 2920.0
        enemy.y = enemy.home_y = 1520.0
    game.handle_event(pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (640, 360)}))
    check(game.player.combat.state == ATTACK_1,
          "left mouse button event starts an attack")
    game.restart()
    game.handle_event(pygame.event.Event(
        pygame.KEYDOWN, {"key": game.dash_key, "mod": 0,
                         "unicode": "c", "scancode": 0}))
    check(game.player.combat.state == DASH_ATTACK,
          "C key event starts the dash attack")
    game.restart()
    game.handle_event(pygame.event.Event(
        pygame.KEYDOWN, {"key": pygame.K_q, "mod": 0,
                         "unicode": "q", "scancode": 0}))
    check(game.skills.energy.current == 80.0,
          "Q key event casts Void Burst and spends 20 energy")
    game.restart()
    game.handle_event(pygame.event.Event(
        pygame.KEYDOWN, {"key": pygame.K_e, "mod": 0,
                         "unicode": "e", "scancode": 0}))
    check(game.player.combat.state == SHADOW_STEP
          and game.skills.energy.current == 85.0,
          "E key event casts Shadow Step and spends 15 energy")
    game.restart()
    game.handle_event(pygame.event.Event(
        pygame.KEYDOWN, {"key": pygame.K_r, "mod": 0,
                         "unicode": "r", "scancode": 0}))
    check(len(game.skills.slash.waves) == 1
          and game.skills.energy.current == 75.0,
          "R key event casts Void Slash and spends 25 energy")
    game.restart()
    game.handle_event(pygame.event.Event(
        pygame.KEYDOWN, {"key": pygame.K_f, "mod": 0,
                         "unicode": "f", "scancode": 0}))
    check(game.skills.eclipse.charging
          and game.skills.energy.current == 40.0,
          "F key event begins Eclipse and spends 60 energy")
    game.restart()
    game.handle_event(pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, {"button": 3, "pos": (640, 360)}))
    check(game.player.combat.state == DASH_ATTACK,
          "right mouse button also dashes")
    game.restart()
    game.handle_event(pygame.event.Event(
        pygame.KEYDOWN, {"key": pygame.K_SPACE, "mod": 0,
                         "unicode": " ", "scancode": 0}))
    check(game.player.combat.state == DODGE, "SPACE key event starts a dodge")
    game.player.health = 10.0
    game.player.combat.invuln = 0.0
    game.player.take_damage(15.0, 1700.0, 1300.0)
    game.handle_event(pygame.event.Event(
        pygame.KEYDOWN, {"key": pygame.K_r, "mod": 0,
                         "unicode": "r", "scancode": 0}))
    check(game.player.combat.dead,
          "R is now Void Slash and no longer restarts a dead run")
    game.handle_event(pygame.event.Event(
        pygame.KEYDOWN, {"key": pygame.K_RETURN, "mod": 0,
                         "unicode": "\r", "scancode": 0}))
    check(not game.player.combat.dead and game.player.health == 100.0,
          "Enter restarts the run after death")
    game.player.health = 10.0
    game.player.combat.invuln = 0.0
    game.player.take_damage(15.0, 1700.0, 1300.0)
    game.handle_event(pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (640, 360)}))
    check(game.player.health == 100.0 and game.player.combat.state == IDLE,
          "clicking after death restarts the run")

    class FrameClock:
        def __init__(self, frames: int) -> None:
            self.frames = frames
            self.ticks = 0

        def tick(self, fps: int = 0) -> int:
            self.ticks += 1
            if self.ticks >= self.frames:
                game.running = False
            return 16

        def get_fps(self) -> float:
            return 60.0

    import asyncio
    game.running = True
    game.clock = FrameClock(6)
    asyncio.run(game.run())
    check(game.clock.ticks == 6 and not game.running,
          f"async loop ran 6 awaited frames ({game.clock.ticks})")

    pygame.quit()
    print(f"\nALL CHECKS PASSED ({PASSED} assertions).")


if __name__ == "__main__":
    main()
