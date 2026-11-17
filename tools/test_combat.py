#!/usr/bin/env python3
"""Headless functional tests for ASHEN VEIL (Phase 1 - Phase 4).

Run from the project root:

    python tools/test_combat.py

The SDL dummy driver is forced before pygame is imported.  Every assertion
below is a real check against the game code; nothing here claims to have run a
browser.  Sections map to the Phase 4 acceptance areas:

 1  player movement, camera and collision
 2  five-hit combo, dodge, dash
 3  enemy archetypes and their configured stats
 4  AI states (IDLE/PATROL -> CHASE -> WINDUP -> ATTACK -> RECOVERY)
 5  HURT / DEATH feedback and removal
 6  ranged retreat, projectiles and impact effects
 7  attacks can never pass through walls
 8  hit feedback: flash, particles, numbers, knockback, shake, hit stop
 9  compact HUD geometry, rendering and window scaling
10  spawner validity, small start group, active/total caps
11  one skill per keypress and the Q/dash key conflict
12  Pygbag async source and built web artifacts
"""
from __future__ import annotations

import math
import os
import sys
import tarfile
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame  # noqa: E402

from main import Game  # noqa: E402
from scripts import enemy_ai  # noqa: E402
from scripts.combat_config import (  # noqa: E402
    COMBO_WINDOW,
    ENEMY_SEPARATION,
    HIT_STOP_FINISHER,
    HIT_STOP_HEAVY,
    HIT_STOP_NORMAL,
)
from scripts.combat_ui import (  # noqa: E402
    COMBO_H,
    COMBO_W,
    COMBO_X,
    COMBO_Y,
    ENEMY_H,
    ENEMY_W,
    ENEMY_X,
    ENEMY_Y,
)
from scripts.enemy_art import ProceduralAnimator  # noqa: E402
from scripts.enemy_config import (  # noqa: E402
    ARCHETYPES,
    ENEMY_MAX_ACTIVE,
    ENEMY_PROJECTILE_MAX,
    ENEMY_SPAWN_TOTAL_CAP,
    ENEMY_START_GROUP,
    get_archetype,
)
from scripts.hud import (  # noqa: E402
    DASH_H,
    DASH_W,
    HELP_H,
    HELP_W,
    HP_H,
    HP_W,
    HP_X,
    HP_Y,
    VOID_H,
    VOID_W,
    VOID_X,
    VOID_Y,
)
from scripts.player_combat import (  # noqa: E402
    ATTACK_1,
    ATTACK_STATES,
    DASH_ATTACK,
    DODGE,
    IDLE,
    SHADOW_STEP,
)
from scripts.skill_config import SKILL_MAX_PARTICLES  # noqa: E402
from scripts.skill_hud import (  # noqa: E402
    PANEL_W,
    PANEL_X,
    PANEL_Y,
    SLOT,
    SLOT_GAP,
)
from scripts.village_layout import ENEMY_SPAWN_POINTS, SPAWN  # noqa: E402
from settings import SCREEN_H, SCREEN_W  # noqa: E402

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


def enemy_of(game: Game, key: str):
    return next(e for e in game.combat.enemies if e.key == key)


def knight_of(game: Game):
    return enemy_of(game, "fallen_knight")


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
    """Fresh duel: one live Fallen Knight parked in front of the player."""
    game.restart()
    game.combat.crit_chance = crit
    player = game.player
    player.x, player.y = base
    player.facing = facing
    player.input_x = player.input_y = 0.0
    knight = knight_of(game)
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


def feedback_peaks(game: Game, seconds: float) -> dict[str, float]:
    """Largest camera shake and hit-stop values seen across a short window."""
    peak = {"shake": 0.0, "stop": 0.0}

    def watch(g) -> None:
        peak["shake"] = max(peak["shake"], g.camera.shake_strength)
        peak["stop"] = max(peak["stop"], g.combat.hit_stop)

    advance(game, seconds, watch=watch)
    return peak


def main() -> None:
    game = Game()
    game.hud.time = 9.0

    # ==================================================================
    section("1. Player movement, run, collision and camera")
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

    # ==================================================================
    section("2. Five-hit combo, dodge and dash")
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

    advance(game, 0.33)
    check(player.combat.state == IDLE and player.combat.combo_buffer is False,
          "buffered clicks clear after the combo ends")
    advance(game, 2.6)
    check(player.combat.combo_count == 0 and player.combat.attack_stage == 0,
          "combo count and stage reset after inactivity")

    # Dodge: i-frames, travel, cooldown and no resource cost.
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

    # Dash attack: burst, front damage, cooldown and walls.
    knight = duel(game, offset_x=62.0, crit=0.0)
    player = game.player
    player.input_x, player.input_y = 1.0, 0.0
    start_x = player.x
    player.request_dash()
    check(player.combat.state == DASH_ATTACK, "C starts the dash attack")
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

    # Multi-enemy damage: one hit per enemy per swing.
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
    freeze_enemies(game)
    game.camera.snap(player.x, player.y)
    before = [e.health.current for e in trio]

    jump_to_stage(game, 4)
    advance(game, 0.5)
    check(all(math.isclose(b - e.health.current, 30.0)
              for b, e in zip(before, trio)),
          f"stage 4 spin hits every archetype for 30 "
          f"({[b - e.health.current for b, e in zip(before, trio)]})")
    check(player.combat.combo_count == 1,
          "one swing registers one combo hit even against three enemies")
    check(len(game.combat._hit_enemies) == 3,
          "swing bookkeeping records each enemy exactly once")

    advance(game, 0.12)
    check(all(math.isclose(b - e.health.current, 30.0)
              for b, e in zip(before, trio)),
          "the same swing cannot damage an enemy twice")

    before = [e.health.current for e in trio]
    jump_to_stage(game, 5)
    advance(game, 0.6)
    check(all(math.isclose(b - e.health.current, min(45.0, b))
              for b, e in zip(before, trio)),
          f"stage 5 finisher applies 45 (clamped by remaining HP) "
          f"({[round(b - e.health.current, 1) for b, e in zip(before, trio)]})")
    check(player.combat.attack_stage == 0,
          "finisher ends the combo chain")

    # Knockback follows the attack direction.
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

    # Critical hits.
    knight = duel(game, crit=1.0)
    player = game.player
    player.request_attack()
    advance(game, 0.3)
    check(knight.health.current == 66.0,
          f"guaranteed crit deals 34 (20 x 1.7) ({knight.health.current})")
    check(player.combat.crit_flash > 0.0, "crit lights the HUD critical flash")
    check(len(game.effects.numbers) > 0, "crit damage number was spawned")

    # Hit stop freezes the simulation briefly.
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

    # ==================================================================
    section("3. Enemy archetypes and configurable stats")
    check(set(ARCHETYPES) == {"fallen_knight", "void_stalker", "ashen_cultist"},
          f"three archetypes are configured ({sorted(ARCHETYPES)})")
    knight_arch = get_archetype("fallen_knight")
    stalker_arch = get_archetype("void_stalker")
    cultist_arch = get_archetype("ashen_cultist")
    check(knight_arch.max_health == 100.0,
          f"Fallen Knight has 100 HP ({knight_arch.max_health})")
    check(stalker_arch.max_health == 65.0,
          f"Void Stalker has 65 HP ({stalker_arch.max_health})")
    check(cultist_arch.max_health == 75.0,
          f"Ashen Cultist has 75 HP ({cultist_arch.max_health})")
    check(stalker_arch.chase_speed > knight_arch.chase_speed > cultist_arch.chase_speed,
          f"stalker is fastest, cultist slowest "
          f"({stalker_arch.chase_speed}/{knight_arch.chase_speed}/"
          f"{cultist_arch.chase_speed})")
    check(stalker_arch.windup < knight_arch.windup < cultist_arch.windup,
          f"quick claws telegraph sooner than the cultist "
          f"({stalker_arch.windup}/{knight_arch.windup}/{cultist_arch.windup})")
    check(not knight_arch.ranged and not stalker_arch.ranged,
          "knight and stalker are melee archetypes")
    check(cultist_arch.ranged and cultist_arch.damage == 0.0
          and cultist_arch.projectile_damage > 0.0,
          "cultist is ranged and damages through its projectile")
    check(cultist_arch.retreat_distance < cultist_arch.preferred_distance,
          f"cultist retreats inside its preferred band "
          f"({cultist_arch.retreat_distance} < {cultist_arch.preferred_distance})")

    game.restart()
    keys = [e.key for e in game.combat.enemies]
    check(keys == list(ENEMY_START_GROUP),
          f"the start group contains one of each archetype ({keys})")
    for enemy in game.combat.enemies:
        check(enemy.name == get_archetype(enemy.key).name
              and math.isclose(enemy.health.maximum,
                               get_archetype(enemy.key).max_health),
              f"{enemy.name} spawned with its configured HP "
              f"({enemy.health.maximum})")

    stalker = ProceduralAnimator("void_stalker", 2.0)
    cultist = ProceduralAnimator("ashen_cultist", 2.0)
    stalker_frame = stalker.image
    check(stalker_frame.get_size() == (128, 128),
          f"stalker art is a scaled 64 px frame ({stalker_frame.get_size()})")
    check(pygame.mask.from_surface(stalker_frame).count() > 80,
          "stalker frame contains visible pixel art, not an empty rect")
    check(pygame.mask.from_surface(cultist.image).count() > 80,
          "cultist frame contains visible pixel art")
    check(ProceduralAnimator("void_stalker", 2.0).image is stalker_frame,
          "procedural frames are cached and shared between instances")

    # ==================================================================
    section("4. AI states: idle, chase, wind-up, attack, recovery")
    expected_states = {
        enemy_ai.IDLE,
        enemy_ai.PATROL,
        enemy_ai.CHASE,
        enemy_ai.ATTACK_WINDUP,
        enemy_ai.ATTACK,
        enemy_ai.RECOVERY,
        enemy_ai.RETREAT,
        enemy_ai.HURT,
        enemy_ai.DEATH,
    }
    state_values = {value for value in vars(enemy_ai).values()
                    if isinstance(value, str)}
    check(expected_states.issubset(state_values),
          "every required AI state constant exists")
    check(enemy_ai.ATTACK_STATES == frozenset(
        (enemy_ai.ATTACK_WINDUP, enemy_ai.ATTACK, enemy_ai.RECOVERY)),
          "wind-up, attack and recovery are explicit committed states")
    check(enemy_ai.PATROL == "PATROL" and enemy_ai.DEAD == enemy_ai.DEATH,
          "legacy AI aliases remain compatible")

    game.restart()
    game.combat.crit_chance = 0.0
    player = game.player
    player.x, player.y = 1500.0, 1200.0
    knight = knight_of(game)
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
    check(knight.state not in (enemy_ai.IDLE, enemy_ai.PATROL),
          f"knight transitions to aggression ({knight.state})")
    check(end_distance < start_distance - 25.0,
          f"knight chases and closes distance "
          f"({start_distance:.0f}->{end_distance:.0f})")

    # The full attack sequence is observable and commits in order.
    game.restart()
    game.combat.crit_chance = 0.0
    player = game.player
    player.x, player.y = OPEN_GROUND
    player.combat.invuln = 0.0
    knight = knight_of(game)
    park_all(game, keep=knight)
    knight.x = knight.home_x = player.x + 34.0
    knight.y = knight.home_y = player.y
    knight.state = enemy_ai.CHASE
    knight.aggro_timer = 4.0
    knight.attack_cooldown = 0.0
    seen = []
    hp_events = []
    attack_anim = [False]
    previous_hp = player.health

    def watch_attack(g) -> None:
        nonlocal previous_hp
        if not seen or seen[-1] != knight.state:
            seen.append(knight.state)
        if knight.animator.current_name.startswith("attack"):
            attack_anim[0] = True
        if player.health < previous_hp - 0.01:
            hp_events.append(previous_hp - player.health)
            previous_hp = player.health

    advance(game, 1.0, watch=watch_attack)
    check(enemy_ai.ATTACK_WINDUP in seen,
          f"wind-up precedes the blow ({seen})")
    check(enemy_ai.ATTACK in seen, f"attack frame is reached ({seen})")
    check(enemy_ai.RECOVERY in seen, f"recovery follows the attack ({seen})")
    check(len(hp_events) == 1 and math.isclose(hp_events[0], 12.0),
          f"the knight swing lands exactly once for 12 ({hp_events})")
    check(attack_anim[0], "a readable attack animation was played")

    # A player who rolls behind the committed wind-up is not hit.
    player.x, player.y = knight.x + 34.0, knight.y
    player.combat.invuln = 0.0
    knight.facing = "right"
    knight.state = enemy_ai.CHASE
    knight.aggro_timer = 3.0
    knight.attack_cooldown = 0.0
    advance(game, 0.05)
    check(knight.state == enemy_ai.ATTACK_WINDUP,
          "second knight swing begins its wind-up")
    hp_before = player.health
    player.x = knight.x - 34.0
    advance(game, 0.40)
    check(player.health == hp_before,
          "knight swing misses a player who moved behind it")

    # Idle/patrol when the player is far away.
    game.restart()
    game.combat.crit_chance = 0.0
    player = game.player
    player.x, player.y = 600.0, 600.0
    knight = knight_of(game)
    park_all(game, keep=knight)
    knight.x, knight.y = 1740.0, 1200.0
    knight.home_x, knight.home_y = 1740.0, 1200.0
    knight.state = enemy_ai.IDLE
    knight.aggro_timer = 0.0
    advance(game, 2.0)
    check(knight.state in (enemy_ai.IDLE, enemy_ai.PATROL),
          f"knight idles/patrols when the player is far ({knight.state})")
    home_distance = math.hypot(knight.x - knight.home_x,
                               knight.y - knight.home_y)
    check(home_distance <= knight.patrol_radius + 40.0,
          f"patrol stays near its home point ({home_distance:.0f} px)")

    # ==================================================================
    section("5. HURT and DEATH states, flash and removal")
    game.restart()
    game.combat.crit_chance = 0.0
    player = game.player
    knight = knight_of(game)
    park_all(game, keep=knight)
    player.x, player.y = knight.x - 50.0, knight.y
    knight.health.reset()
    knight.state = enemy_ai.CHASE
    knight.aggro_timer = 3.0
    before_x = knight.x
    lost, killed = knight.take_damage(25.0, player.x, player.y, 110.0)
    check(lost == 25.0 and not killed and knight.health.current == 75.0,
          "knight takes sword damage")
    check(knight.state == enemy_ai.HURT, "knight enters HURT")
    check(knight.flash_timer > 0.0, "hit flash timer starts on damage")
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

    # ==================================================================
    section("6. Ranged cultist: retreat, bolt, impact and one shot")
    game.restart()
    game.combat.crit_chance = 0.0
    player = game.player
    player.x, player.y = OPEN_GROUND
    player.combat.invuln = 0.0
    cultist = enemy_of(game, "ashen_cultist")
    park_all(game, keep=cultist)
    cultist.x = cultist.home_x = player.x + 100.0
    cultist.y = cultist.home_y = player.y
    cultist.state = enemy_ai.CHASE
    cultist.aggro_timer = 5.0
    cultist.attack_cooldown = 0.0
    retreat_states = []
    start_distance = math.hypot(cultist.x - player.x, cultist.y - player.y)

    def watch_retreat(g) -> None:
        if not retreat_states or retreat_states[-1] != cultist.state:
            retreat_states.append(cultist.state)

    advance(game, 0.6, watch=watch_retreat)
    check(enemy_ai.RETREAT in retreat_states,
          f"cultist retreats when the player is too close ({retreat_states})")
    check(math.hypot(cultist.x - player.x,
                     cultist.y - player.y) > start_distance,
          "retreat actually increases the gap")

    # Now at the preferred distance: wind up, fire, hit the player.
    player.x, player.y = OPEN_GROUND
    player.combat.invuln = 0.0
    cultist.x = cultist.home_x = player.x + 200.0
    cultist.y = cultist.home_y = player.y
    cultist.state = enemy_ai.CHASE
    cultist.aggro_timer = 5.0
    cultist.attack_cooldown = 0.0
    game.combat.projectiles.clear()
    game.effects.clear()
    hp_before = player.health
    advance(game, 0.10)
    check(cultist.state == enemy_ai.ATTACK_WINDUP,
          f"cultist visibly winds up at range ({cultist.state})")
    advance(game, 0.55)
    check(len(game.combat.projectiles.projectiles) == 1,
          f"one purple bolt was fired "
          f"({len(game.combat.projectiles.projectiles)})")
    bolt = game.combat.projectiles.projectiles[0]
    check(bolt.color[2] > bolt.color[0] and bolt.damage == 10.0,
          f"bolt is purple and deals 10 ({bolt.color}, {bolt.damage})")
    check(cultist.pending_projectile is None,
          "the projectile signal is consumed exactly once")
    game.draw()
    impact_particles = [0]

    def watch_impact(g) -> None:
        impact_particles[0] = max(impact_particles[0],
                                  len(g.effects.particles))

    advance(game, 1.2, watch=watch_impact)
    check(math.isclose(player.health, hp_before - 10.0),
          f"the bolt damages the player once ({player.health})")
    check(not game.combat.projectiles.projectiles,
          "the bolt is removed after impact")
    check(impact_particles[0] > 0,
          f"projectile impact spawns particles ({impact_particles[0]})")
    check(len(game.combat.projectiles.projectiles) <= ENEMY_PROJECTILE_MAX,
          f"live projectiles stay capped ({ENEMY_PROJECTILE_MAX})")

    # ==================================================================
    section("7. No attack may pass through a solid wall")
    game.restart()
    game.combat.crit_chance = 0.0
    player = game.player
    collision = game.world.collision
    fence = next(
        rect for rect in collision.rects
        if 50 <= rect.w <= 140 and 14 <= rect.h <= 24 and rect.y > 900
    )
    fence_cx = fence.centerx

    knight = knight_of(game)
    park_all(game, keep=knight)
    player.x, player.y = fence_cx, fence.top - 10.0
    player.facing = "down"
    player.combat.invuln = 0.0
    knight.x = knight.home_x = fence_cx
    knight.y = knight.home_y = fence.bottom + 10.0
    knight.facing = "up"
    knight.state = enemy_ai.ATTACK_WINDUP
    knight.attack_time = knight.windup
    knight.attack_hit_done = False
    check(collision.segment_blocked(knight.x, knight.y - 18.0,
                                    player.x, player.y - 18.0, 3.0),
          "a fence sits between the knight and the player")
    hp_before = player.health
    knight.update(DT, player, collision)
    check(knight.pending_swipe is not None
          and knight.pending_swipe[3] is False,
          "melee resolve refuses to hit through the fence")
    check(player.health == hp_before,
          "the walled knight deals no damage")

    cultist = enemy_of(game, "ashen_cultist")
    park_all(game, keep=cultist)
    cultist.x = cultist.home_x = fence_cx
    cultist.y = cultist.home_y = fence.bottom + 10.0
    cultist.facing = "up"
    cultist.state = enemy_ai.ATTACK_WINDUP
    cultist.attack_time = cultist.windup
    cultist.attack_hit_done = False
    cultist.attack_cooldown = 5.0
    game.combat.projectiles.clear()
    game.effects.clear()
    hp_before = player.health
    cultist.update(DT, player, collision)
    check(cultist.pending_projectile is not None
          and cultist.pending_projectile[4] is True,
          "a blocked cast is flagged before it becomes a projectile")
    game.combat.update(DT)
    check(not game.combat.projectiles.projectiles,
          "no bolt is created through the fence")
    check(player.health == hp_before, "the blocked bolt deals no damage")
    check(len(game.effects.particles) > 0,
          "the blocked cast still pops harmlessly on the wall")

    # A clear line of sight is still allowed.
    check(not collision.segment_blocked(1600, 1250, 1660, 1250, 2.0),
          "open plaza has clear line of sight")
    check(collision.segment_blocked(2300, 1870, 2300, 1940, 2.0),
          "the stone wall is detected on the existing combat line")

    # ==================================================================
    section("8. HUD and combat visual feedback")
    game.restart()
    game.combat.crit_chance = 0.0
    effects = game.effects
    effects.clear()
    effects.spawn_damage_number(100.0, 100.0, 7.0, heavy=False, crit=False)
    light_surface = effects.numbers[-1]["surface"]
    effects.spawn_damage_number(100.0, 100.0, 22.0, heavy=True, crit=False)
    heavy_surface = effects.numbers[-1]["surface"]
    effects.spawn_damage_number(100.0, 100.0, 34.0, heavy=False, crit=True)
    crit_surface = effects.numbers[-1]["surface"]
    check(heavy_surface.get_width() > light_surface.get_width()
          and crit_surface.get_width() >= heavy_surface.get_width(),
          f"damage numbers are readable 2x/3x pixel text "
          f"({light_surface.get_size()} / {heavy_surface.get_size()} / "
          f"{crit_surface.get_size()})")

    effects.spawn_impact(1600.0, 1400.0, heavy=False, crit=False)
    check(len(effects.particles) > 0, "sword impacts spawn sparks")
    effects.spawn_projectile_impact(1600.0, 1400.0, (198, 126, 255))
    check(len(effects.particles) <= 200,
          f"impact particles stay capped ({len(effects.particles)})")
    effects.spawn_enemy_swipe(1600.0, 1400.0, "right", (204, 94, 98), True)
    check(len(effects.swipes) == 1, "enemy strikes spawn a swipe arc")
    effects.draw_world(game.canvas, game.camera)
    effects.draw_overlay(game.canvas, game.camera)
    check(game.canvas.get_size() == (SCREEN_W, SCREEN_H),
          "swipe/particle overlay renders inside the canvas")

    check(HIT_STOP_FINISHER > HIT_STOP_HEAVY > HIT_STOP_NORMAL > 0.0,
          f"feedback scales with hit weight "
          f"({HIT_STOP_NORMAL}/{HIT_STOP_HEAVY}/{HIT_STOP_FINISHER})")

    # Light link vs heavy spin: shake and hit stop are stronger on the spin.
    duel(game)
    game.player.request_attack()
    light = feedback_peaks(game, 0.5)

    duel(game)
    jump_to_stage(game, 4)
    heavy = feedback_peaks(game, 0.6)
    check(heavy["shake"] > light["shake"],
          f"heavy strike shakes harder "
          f"({heavy['shake']:.1f} > {light['shake']:.1f})")
    check(heavy["stop"] > light["stop"],
          f"heavy strike freezes longer "
          f"({heavy['stop'] * 1000:.0f}ms > {light['stop'] * 1000:.0f}ms)")

    # ==================================================================
    section("9. Compact HUD geometry, rendering and scaling")
    check(190 <= HP_W <= 220 and 12 <= HP_H <= 14,
          f"HP bar is compact ({HP_W}x{HP_H})")
    check(160 <= VOID_W <= 190 and 8 <= VOID_H <= 10,
          f"Void bar is compact ({VOID_W}x{VOID_H})")
    check(HP_X <= 24 and HP_Y <= 24,
          f"HP sits in the top-left corner ({HP_X},{HP_Y})")
    check(VOID_X == HP_X and VOID_Y > HP_Y + HP_H,
          f"Void bar sits directly below HP ({VOID_X},{VOID_Y})")
    check(2 <= DASH_H <= 5 and DASH_W <= 140,
          f"dash gauge is a thin line ({DASH_W}x{DASH_H})")
    check(38 <= SLOT <= 44,
          f"skill icons are small ({SLOT} px)")
    check(PANEL_X > SCREEN_W * 0.75 and PANEL_Y > SCREEN_H * 0.75,
          f"four skill icons live bottom-right ({PANEL_X},{PANEL_Y})")
    check(PANEL_X + PANEL_W <= SCREEN_W and PANEL_Y + SLOT <= SCREEN_H,
          "the skill strip stays fully on screen")
    check(PANEL_W == SLOT * 4 + SLOT_GAP * 3,
          f"the skill strip is exactly four icons wide ({PANEL_W})")
    check(ENEMY_W == 300 and ENEMY_H == 46 and ENEMY_Y <= 20
          and ENEMY_X == (SCREEN_W - ENEMY_W) // 2,
          f"engaged target bar is a slim top-centre plate ({ENEMY_W}x{ENEMY_H})")
    check(COMBO_W == 120 and COMBO_H == 52
          and COMBO_X + COMBO_W <= SCREEN_W and COMBO_Y <= 30,
          f"combo readout is a small upper-right block ({COMBO_W}x{COMBO_H})")
    check(HELP_W <= 460 and HELP_H <= 36,
          f"the control hint strip is small ({HELP_W}x{HELP_H})")

    game.restart()
    game.hud.time = 9.0
    game.hud.show_help = False
    skills = game.skills
    player = game.player
    skills.energy.reset()
    game.canvas.fill((0, 0, 0))
    game.hud.draw(game.canvas, player, game.combat, game.camera, skills)
    hp_px = game.canvas.get_at((HP_X + 10, HP_Y + 6))
    void_px = game.canvas.get_at((VOID_X + 10, VOID_Y + 4))
    skill_px = game.canvas.get_at((PANEL_X + SLOT // 2, PANEL_Y + SLOT // 2))
    check(hp_px[0] > hp_px[1] and hp_px[0] > hp_px[2] and hp_px[0] > 60,
          f"full HP renders muted crimson ({hp_px})")
    check(void_px[2] > void_px[0] and void_px[2] > 60,
          f"full Void renders dark violet ({void_px})")
    check(skill_px[:3] != (0, 0, 0) and skill_px[2] > skill_px[0],
          f"skill glyph renders inside its 42 px slot ({skill_px})")

    skills.energy.current = 0.0
    game.canvas.fill((0, 0, 0))
    game.hud.draw(game.canvas, player, game.combat, game.camera, skills)
    empty_px = game.canvas.get_at((VOID_X + 10, VOID_Y + 4))
    check(empty_px[2] < 60,
          f"an empty Void bar drains the purple fill ({empty_px})")
    check(not skills.energy.can_afford(15.0),
          "an empty pool disables every skill")
    skills.energy.reset()

    player.combat.combo_count = 3
    player.combat.combo_decay = 1.5
    player.combat.attack_stage = 3
    game.combat.engaged = knight_of(game)
    game.canvas.fill((0, 0, 0))
    game.hud.draw(game.canvas, player, game.combat, game.camera, skills)
    check(game.hud.combat_ui._combo_panel.get_size() == (COMBO_W, COMBO_H),
          "combo panel is cached at its compact size")
    check(game.hud.combat_ui._enemy_panel.get_size() == (ENEMY_W, ENEMY_H),
          "engaged panel is cached at its compact size")
    check(game.canvas.get_at((COMBO_X + 4, COMBO_Y + 4))[:3] != (0, 0, 0),
          "combo readout actually draws in the upper-right")
    check(game.canvas.get_at((ENEMY_X + 4, ENEMY_Y + 4))[:3] != (0, 0, 0),
          "engaged bar actually draws top-centre")

    # Window scaling letterboxes the fixed 1280x720 canvas and leaves the
    # internal HUD geometry untouched (no off-screen or stretched bars).
    game.handle_event(pygame.event.Event(
        pygame.VIDEORESIZE, {"size": (1000, 1000), "w": 1000, "h": 1000}))
    game.present()
    check(game.canvas.get_size() == (SCREEN_W, SCREEN_H),
          "HUD and world always render at the internal 1280x720 resolution")
    check(game._scaled_size == (1000, 562),
          f"a square window letterboxes 16:9 ({game._scaled_size})")
    check(PANEL_X == SCREEN_W - 20 - PANEL_W
          and PANEL_X + PANEL_W <= SCREEN_W,
          "skill icons stay anchored bottom-right after a window resize")
    game.handle_event(pygame.event.Event(
        pygame.VIDEORESIZE, {"size": (1280, 720), "w": 1280, "h": 720}))
    game.present()

    # ==================================================================
    section("10. Spawner: valid points, small start group, hard caps")
    game.restart()
    spawner = game.combat.spawner
    player = game.player
    check(spawner.total_spawned == len(ENEMY_START_GROUP),
          f"only a small start group spawns ({spawner.total_spawned})")
    check(len(spawner.spawn_log) == len(ENEMY_START_GROUP),
          "every initial spawn is logged")
    check([key for key, _x, _y in spawner.spawn_log]
          == list(ENEMY_START_GROUP),
          "the opening group is one knight, one stalker, one cultist")
    check(len(ENEMY_SPAWN_POINTS) > ENEMY_MAX_ACTIVE,
          f"there are more candidate points than the active cap "
          f"({len(ENEMY_SPAWN_POINTS)} > {ENEMY_MAX_ACTIVE})")

    alive = [e for e in game.combat.enemies if e.alive]
    for enemy in alive:
        margin = 3.0
        box = pygame.Rect(
            int(round(enemy.x - enemy.half_w - margin)),
            int(round(enemy.y - enemy.half_h - margin)),
            int(round((enemy.half_w + margin) * 2)),
            int(round((enemy.half_h + margin) * 2)),
        )
        check(game.world.collision.rect_free(box),
              f"{enemy.name} did not spawn inside a solid")
        check(math.hypot(enemy.x - player.x, enemy.y - player.y) >= 240.0,
              f"{enemy.name} spawned well clear of the player "
              f"({math.hypot(enemy.x - player.x, enemy.y - player.y):.0f} px)")
    for index, first in enumerate(alive):
        for second in alive[index + 1:]:
            check(math.hypot(first.x - second.x, first.y - second.y)
                  >= 30.0,
                  "initial enemies never spawn stacked")

    archetype = get_archetype("fallen_knight")
    check(not spawner._position_valid(fence_cx, fence.centery, archetype),
          "a point inside a solid is rejected")
    _key, valid_x, valid_y = spawner.spawn_log[0]
    player.x, player.y = valid_x, valid_y
    check(not spawner._position_valid(valid_x, valid_y, archetype),
          "a point under the player is rejected")
    player.x, player.y = 1500.0, 1080.0
    existing = alive[0]
    check(not spawner._position_valid(existing.x, existing.y, archetype),
          "a point overlapping another enemy is rejected")

    # Active cap: fill the band, then prove update() refuses to add more.
    for _ in range(8):
        if spawner.alive_count >= ENEMY_MAX_ACTIVE:
            break
        if spawner.spawn("void_stalker") is None:
            break
    check(spawner.alive_count == ENEMY_MAX_ACTIVE,
          f"the active cap can be reached ({spawner.alive_count})")
    before_total = spawner.total_spawned
    spawner.timer = 0.0
    advance(game, 1.0)
    check(spawner.total_spawned == before_total,
          f"no spawn while the active cap is full ({before_total})")

    # Total cap: the village eventually runs dry.
    spawner.combat.enemies[:] = []
    guard = 0
    while spawner.total_spawned < ENEMY_SPAWN_TOTAL_CAP and guard < 20:
        spawned = spawner.spawn("fallen_knight")
        guard += 1
        if spawned is None:
            break
        spawner.combat.enemies[:] = []
    check(spawner.total_spawned == ENEMY_SPAWN_TOTAL_CAP,
          f"the total spawn cap is finite ({spawner.total_spawned}"
          f"/{ENEMY_SPAWN_TOTAL_CAP})")
    check(spawner.exhausted and spawner.spawn("void_stalker") is None,
          "an exhausted spawner refuses further enemies")
    before_total = spawner.total_spawned
    spawner.timer = 0.0
    advance(game, 1.0)
    check(spawner.total_spawned == before_total,
          "exhausted spawning never restarts infinitely")

    # ==================================================================
    section("11. One cast per keypress; Q never triggers two abilities")
    game.restart()
    check(game.skill_keys == {
        "Q": pygame.K_q, "E": pygame.K_e,
        "R": pygame.K_r, "F": pygame.K_f,
    }, "skills are bound explicitly to Q/E/R/F")
    check(game.dash_key not in game.skill_keys.values(),
          f"the dash key ({pygame.key.name(game.dash_key)}) never aliases a skill")
    check(len(set(game.skill_keys.values())) == 4,
          "all four skill keys are distinct")

    skills = game.skills
    check(skills.energy.current == 100.0, "Void starts full before the cast")
    game.handle_event(pygame.event.Event(
        pygame.KEYDOWN, {"key": pygame.K_q, "mod": 0,
                         "unicode": "q", "scancode": 0}))
    check(math.isclose(skills.energy.current, 80.0),
          f"Q spends exactly the burst cost ({skills.energy.current})")
    check(skills.burst.timer > 0.0,
          "Q starts the burst cooldown")
    check(skills.shadow.timer == 0.0 and skills.slash.timer == 0.0
          and skills.eclipse.timer == 0.0,
          "Q did not cast any other ability")
    check(game.player.combat.state not in (DASH_ATTACK, DODGE)
          and not game.player.combat.dashing,
          "Q did not also dash or dodge")
    game.handle_event(pygame.event.Event(
        pygame.KEYDOWN, {"key": pygame.K_q, "mod": 0,
                         "unicode": "q", "scancode": 0}))
    check(math.isclose(skills.energy.current, 80.0),
          "a second Q during cooldown spends no energy")

    game.restart()
    game.handle_event(pygame.event.Event(
        pygame.KEYDOWN, {"key": game.dash_key, "mod": 0,
                         "unicode": "c", "scancode": 0}))
    check(game.player.combat.state == DASH_ATTACK,
          "the dash key dashes")
    check(game.skills.energy.current == 100.0
          and all(skill.timer == 0.0 for skill in game.skills.skills),
          "the dash key never spends Void or casts a skill")

    game.restart()
    game.handle_event(pygame.event.Event(
        pygame.KEYDOWN, {"key": pygame.K_e, "mod": 0,
                         "unicode": "e", "scancode": 0}))
    check(game.player.combat.state == SHADOW_STEP
          and math.isclose(game.skills.energy.current, 85.0),
          "E only casts Shadow Step (not the dash)")

    game.restart()
    game.handle_event(pygame.event.Event(
        pygame.KEYDOWN, {"key": pygame.K_r, "mod": 0,
                         "unicode": "r", "scancode": 0}))
    check(len(game.skills.slash.waves) == 1
          and math.isclose(game.skills.energy.current, 75.0),
          "R only casts Void Slash")
    game.restart()
    game.handle_event(pygame.event.Event(
        pygame.KEYDOWN, {"key": pygame.K_f, "mod": 0,
                         "unicode": "f", "scancode": 0}))
    check(game.skills.eclipse.charging
          and math.isclose(game.skills.energy.current, 40.0),
          "F only begins Eclipse")

    # ==================================================================
    section("12. Pygbag async source and web build artifacts")
    main_source = (ROOT / "main.py").read_text(encoding="utf-8")
    check("async def main" in main_source and "await game.run()" in main_source,
          "main.py exposes an awaited async entry point")
    check("await asyncio.sleep(0)" in main_source,
          "the frame loop yields to the browser every frame")
    check("emscripten" in main_source,
          "the game detects the Emscripten/Pygbag platform")
    check("asyncio.run(main())" in main_source,
          "the desktop entry point still runs the async loop")
    check("pygame.event.get()" in main_source and "clock.tick" in main_source,
          "the loop keeps a normal pygame event/clock pipeline")
    check(not (ROOT / "scripts" / "stamina.py").exists(),
          "the obsolete stamina module was removed")
    check((ROOT / "pygbag.ini").exists(),
          "pygbag.ini exists for the web build")

    index = ROOT / "build" / "web" / "index.html"
    archive = ROOT / "build" / "web" / "game.tar.gz"
    check(index.exists() and index.stat().st_size > 1000,
          f"Pygbag produced build/web/index.html ({index.stat().st_size} bytes)"
          if index.exists() else "build/web/index.html exists")
    check(archive.exists() and archive.stat().st_size > 100000,
          "Pygbag produced the packaged game archive")
    if archive.exists():
        with tarfile.open(archive, "r:gz") as bundle:
            names = bundle.getnames()
        check(any(name.endswith("main.py") for name in names),
              "the web archive contains main.py")
        check(any(name.endswith("scripts/projectile.py") for name in names),
              "the web archive contains the Phase 4 projectile module")
        check(not any("/tools/" in name for name in names),
              "development tools are excluded from the web archive")

    # ==================================================================
    section("Runtime input, death/restart and async loop")
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
    check(game.player.combat.dead, "lethal damage kills the player")
    game.handle_event(pygame.event.Event(
        pygame.KEYDOWN, {"key": pygame.K_r, "mod": 0,
                         "unicode": "r", "scancode": 0}))
    check(game.player.combat.dead,
          "R is Void Slash and no longer restarts a dead run")
    game.handle_event(pygame.event.Event(
        pygame.KEYDOWN, {"key": pygame.K_RETURN, "mod": 0,
                         "unicode": "\r", "scancode": 0}))
    check(not game.player.combat.dead and game.player.health == 100.0,
          "Enter restarts the run after death")
    check(len(game.combat.enemies) == len(ENEMY_START_GROUP),
          "restart rebuilds the small start group")
    check(math.isclose(game.player.x, SPAWN[0])
          and math.isclose(game.player.y, SPAWN[1]),
          "restart returns the player to the spawn")
    check(game.skills.energy.current == 100.0,
          "restart refills Void Energy")
    check(game.canvas.get_size() == (SCREEN_W, SCREEN_H),
          "full frame renders at the internal resolution")
    game.debug = True
    game.draw()
    game.debug = False
    check(game.canvas.get_at((0, 0))[:3] != (0, 0, 0),
          "debug overlay renders without error")

    # Skill rendering still works after the HUD shrink.
    game.restart()
    game.player.x, game.player.y = OPEN_GROUND
    game.skills.energy.current = 100.0
    game.skills.cast_burst()
    advance(game, 0.1)
    game.draw()
    check(len(game.skills.skill_effects.particles) <= SKILL_MAX_PARTICLES,
          f"skill particles stay capped "
          f"({len(game.skills.skill_effects.particles)})")

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
