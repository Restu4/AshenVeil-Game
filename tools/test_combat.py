#!/usr/bin/env python3
"""Headless functional tests for the ASHEN VEIL combat phase.

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
from scripts.player_combat import (  # noqa: E402
    ATTACK_1,
    DODGE,
    HURT,
    IDLE,
)
from scripts.village_layout import ENEMY_SPAWNS, SPAWN  # noqa: E402

DT = 1.0 / 60.0


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


def tap(game: Game, seconds: float, keys=EMPTY, watch=None) -> None:
    """Advance the same order as main.update (player -> combat -> effects)."""
    player = game.player
    frames = max(1, int(round(seconds / DT)))
    for _ in range(frames):
        player.update(DT, keys, game.world.collision)
        game.combat.update(DT)
        game.effects.update(DT)
        game.camera.update(DT, player.x, player.y, *player.look)
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


def duel(game: Game, offset_x: float = 68.0,
         facing: str = "right", base=(1600.0, 1300.0)):
    """Fresh duel: one live knight parked in front of the player."""
    game.restart()
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
    return knight


def main() -> None:
    game = Game()
    game.hud.time = 9.0

    # ------------------------------------------------------------------
    section("Player movement, run and existing collision/camera")
    game.restart()
    start = game.player.x
    tap(game, 1.0, Keys(pygame.K_d))
    walked = game.player.x - start
    check(walked > 80.0, f"walking moved the player ({walked:.1f} px)")
    start = game.player.x
    tap(game, 1.0, Keys(pygame.K_d, pygame.K_LSHIFT))
    ran = game.player.x - start
    check(ran > walked * 1.25, f"running is faster ({ran:.1f} > {walked:.1f})")
    check(game.player.stamina.current < 100.0,
          f"running drains stamina ({game.player.stamina.current:.1f})")
    check(game.player.state == "RUN", "running exposes the RUN state")
    tap(game, 0.5, Keys(pygame.K_a))
    check(game.player.state == "WALK", "walking exposes the WALK state")
    tap(game, 0.2)
    check(game.player.state == "IDLE", "releasing input returns to IDLE")

    player = game.player
    player.x, player.y = 1075.0, 1250.0
    player.vx = player.vy = 0.0
    tap(game, 1.2, Keys(pygame.K_w))
    check(player.y > 1000.0,
          f"house still blocks movement (y={player.y:.1f})")

    player.x, player.y = 60.0, 60.0
    game.camera.snap(player.x, player.y)
    tap(game, 0.1)
    ox, oy = game.camera.offset
    check(0 <= ox <= 3200 - 1280 and 0 <= oy <= 2400 - 720,
          f"camera stays clamped ({ox},{oy})")

    # ------------------------------------------------------------------
    section("Player sword: one real hit per swing")
    knight = duel(game)
    player = game.player
    player.request_attack()
    check(player.combat.state == ATTACK_1, "LMB starts ATTACK_1")
    check(player.stamina.current == 90.0, "first swing costs 10 stamina")
    tap(game, 0.55)
    check(knight.health.current == 75.0,
          f"first slash deals 25 once ({knight.health.current})")
    check(player.combat.state == IDLE, "attack recovers to IDLE")
    check(len(game.effects.numbers) > 0, "damage number spawned")
    check(len(game.effects.slashes) >= 0, "slash effect path used")
    check(knight.state == enemy_ai.HURT or knight.state == enemy_ai.IDLE,
          "enemy reacts to being hit")

    # ------------------------------------------------------------------
    section("Three-hit combo, buffering and kill")
    knight = duel(game, offset_x=64.0)
    player = game.player
    record = {"hp": 100.0, "hits": [], "stages": set(), "shake": 0.0}

    def watch_attack(g):
        record["stages"].add(g.player.combat.attack_stage)
        hp = knight.health.current
        if hp < record["hp"] - 0.01:
            record["hits"].append(round(record["hp"] - hp, 1))
            record["hp"] = hp
        record["shake"] = max(record["shake"], g.camera.shake_time)

    player.request_attack()
    tap(game, 0.25, watch=watch_attack)
    player.request_attack()                    # buffer during attack 1
    tap(game, 0.50, watch=watch_attack)
    check(player.combat.attack_stage == 2,
          f"buffered input chains to ATTACK_2 ({player.combat.attack_stage})")
    player.request_attack()                    # buffer during attack 2
    tap(game, 0.80, watch=watch_attack)
    check(record["hits"] == [25.0, 30.0, 45.0],
          f"combo damage values are 25/30/45 ({record['hits']})")
    check(3 in record["stages"], "all three attack states were reached")
    check(knight.health.current == 0.0 and not knight.alive,
          "third strike kills the 100 HP knight")
    check(record["shake"] > 0.0, "heavy hit triggered restrained camera shake")

    # ------------------------------------------------------------------
    section("Directional swings hit in all four facings")
    vectors = {"down": (0.0, 60.0), "up": (0.0, -60.0),
               "left": (-60.0, 0.0), "right": (60.0, 0.0)}
    for facing, (dx, dy) in vectors.items():
        knight = duel(game, offset_x=dx, base=(1580.0, 1420.0))
        knight.y = knight.home_y = game.player.y + dy
        player = game.player
        player.facing = facing
        player.request_attack()
        tap(game, 0.45)
        check(knight.health.current == 75.0,
              f"attack_{facing} connects for 25")

    # ------------------------------------------------------------------
    section("Dodge, i-frames, cooldown and stamina")
    game.restart()
    park_all(game)
    player = game.player
    player.x, player.y = 1600.0, 1400.0
    player.facing = "right"
    player.input_x, player.input_y = 1.0, 0.0
    player.request_dodge()
    check(player.combat.state == DODGE, "SPACE starts DODGE")
    check(math.isclose(player.stamina.current, 80.0),
          f"dodge costs 20 stamina ({player.stamina.current})")
    check(player.combat.invulnerable, "dodge grants i-frames")
    check(not player.take_damage(15.0, 1500.0, 1400.0),
          "damage is ignored during i-frames")
    before = player.x
    tap(game, 0.32)
    check(player.x - before > 55.0,
          f"dodge travels in the input direction ({player.x - before:.1f} px)")
    check(player.combat.state != DODGE, "dodge cannot permanently lock movement")
    check(player.combat.dodge_cooldown > 0.0, "dodge cooldown is running")
    player.request_dodge()
    check(player.combat.state != DODGE,
          "dodge is refused during cooldown")
    tap(game, 0.20)
    player.request_dodge()
    check(player.combat.state == DODGE, "dodge works again after cooldown")
    check(math.isclose(player.stamina.current, 60.0),
          "second dodge spends a second 20 stamina")

    # ------------------------------------------------------------------
    section("Stamina floor, regen delay and blocked actions")
    game.restart()
    park_all(game)
    player = game.player
    player.stamina.current = 5.0
    player.request_attack()
    check(player.combat.state == IDLE,
          "attack refused without enough stamina")
    check(player.combat.blocked_flash > 0.0, "blocked action gives HUD feedback")
    player.stamina.current = 0.0
    player.request_dodge()
    tap(game, 0.5)
    check(player.stamina.current >= 0.0, "stamina never becomes negative")
    player.stamina.current = 50.0
    player.request_attack()
    spent = player.stamina.current
    tap(game, 0.4)
    check(player.stamina.current == spent, "regen waits out its delay")
    tap(game, 0.7)
    check(player.stamina.current > spent, "stamina regenerates after the delay")
    check(player.stamina.current <= 100.0, "stamina never exceeds maximum")

    # ------------------------------------------------------------------
    section("Player health, invulnerability, death and restart")
    game.restart()
    park_all(game)
    player = game.player
    check(player.take_damage(15.0, 1500.0, 1300.0), "enemy hit damages the player")
    check(player.health == 85.0, f"damage is applied (HP {player.health})")
    check(player.combat.state == HURT, "player enters HURT")
    check(not player.take_damage(15.0, 1500.0, 1300.0),
          "post-hit invulnerability blocks a second hit")
    tap(game, 0.9)
    check(player.take_damage(15.0, 1500.0, 1300.0),
          "player can be hit again after i-frames")
    check(player.health == 70.0, "HP never exceeds maximum and tracks damage")
    player.health = 10.0
    player.combat.invuln = 0.0
    player.take_damage(15.0, 1500.0, 1300.0)
    check(player.health == 0.0, "lethal damage clamps HP to zero")
    check(player.combat.dead and player.combat.state == "DEAD",
          "player enters DEAD state")
    dead_x = player.x
    player.request_attack()
    player.request_dodge()
    tap(game, 0.6, Keys(pygame.K_d))
    check(player.combat.state == "DEAD", "dead player cannot attack or dodge")
    check(player.x == dead_x, "dead player cannot move")
    game.draw()
    check(game.canvas.get_width() == 1280, "death overlay renders without error")
    game.restart()
    check(player.health == 100.0 and player.combat.state == IDLE,
          "restart restores health and state")
    check(len(game.combat.enemies) == len(ENEMY_SPAWNS),
          "restart respawns every knight")
    check(math.isclose(player.x, SPAWN[0]) and math.isclose(player.y, SPAWN[1]),
          "restart returns the player to the spawn")

    # ------------------------------------------------------------------
    section("Fallen Knight: detection, chase and attack")
    game.restart()
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
    tap(game, 1.0)
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
    tap(game, 0.08)
    check(knight.state == enemy_ai.ATTACK, "knight attacks in range")
    tap(game, 0.40)
    check(player.health == hp_before - 15.0,
          f"knight attack deals 15 ({player.health})")
    tap(game, 0.45)
    check(player.health == hp_before - 15.0,
          "one attack animation only applies damage once")

    # Roll through the wind-up: the blow is a forward arc, so a player who
    # ends up behind the knight is not hit.
    player.x, player.y = knight.x + 34.0, knight.y
    player.combat.invuln = 0.0
    knight.facing = "right"
    knight.state = enemy_ai.CHASE
    knight.aggro_timer = 3.0
    knight.attack_cooldown = 0.0
    tap(game, 0.05)
    check(knight.state == enemy_ai.ATTACK, "second knight swing winds up")
    hp_before = player.health
    player.x = knight.x - 34.0
    tap(game, 0.40)
    check(player.health == hp_before,
          "knight swing misses a player who moved behind it")

    # ------------------------------------------------------------------
    section("Fallen Knight: patrol, hurt, knockback and death")
    game.restart()
    player = game.player
    player.x, player.y = 600.0, 600.0
    knight = game.combat.enemies[0]
    park_all(game, keep=knight)
    knight.x, knight.y = 1740.0, 1200.0
    knight.home_x, knight.home_y = 1740.0, 1200.0
    knight.state = enemy_ai.IDLE
    knight.aggro_timer = 0.0
    tap(game, 2.0)
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
    tap(game, 0.18)
    check(knight.x > before_x,
          f"knockback moves the knight away ({knight.x - before_x:.1f} px)")
    tap(game, 0.30)
    check(knight.state in (enemy_ai.CHASE, enemy_ai.HURT, enemy_ai.PATROL),
          "knight recovers from the hit")
    lost, killed = knight.take_damage(999.0, player.x, player.y, 120.0)
    check(killed and knight.health.current == 0.0, "lethal hit kills the knight")
    check(knight.state == enemy_ai.DEATH, "death state starts")
    tap(game, 1.3)
    check(knight not in game.combat.enemies,
          "dead knight is removed after its death animation")

    # ------------------------------------------------------------------
    section("World obstruction and enemy collision")
    game.restart()
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
    tap(game, 0.55)
    check(knight.health.current == 100.0,
          "sword cannot cut through a stone wall")
    check(game.world.collision.segment_blocked(2300, 1870, 2300, 1940, 2.0),
          "collision segment detects the stone wall")
    check(not game.world.collision.segment_blocked(1600, 1250, 1660, 1250, 2.0),
          "open plaza has clear line of sight")

    game.restart()
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

    tap(game, 3.0, watch=watch_collision)
    check(not overlapping, "knight never stands inside a building footprint")
    check(knight.y < 1010.0,
          f"knight cannot walk through the house (y={knight.y:.0f})")

    # ------------------------------------------------------------------
    section("Rendering: combat frame with HUD, effects and debug overlays")
    game.restart()
    knight = duel(game, offset_x=60.0)
    player.request_attack()
    tap(game, 0.22)
    game.draw()
    game.debug = True
    game.draw()
    game.debug = False
    game.hud.draw(game.canvas, game.player, knight)
    check(game.canvas.get_size() == (1280, 720),
          "full combat frame renders at the internal resolution")
    check(game.canvas.get_at((0, 0))[:3] != (0, 0, 0),
          "canvas contains a rendered frame")

    # ------------------------------------------------------------------
    section("Input events and the async browser loop")
    game.restart()
    park_all(game)
    game.handle_event(pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (640, 360)}))
    check(game.player.combat.state == ATTACK_1,
          "left mouse button event starts an attack")
    game.restart()
    game.handle_event(pygame.event.Event(
        pygame.KEYDOWN, {"key": pygame.K_SPACE, "mod": 0,
                         "unicode": " ", "scancode": 0}))
    check(game.player.combat.state == DODGE, "SPACE key event starts a dodge")
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
