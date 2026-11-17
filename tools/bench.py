#!/usr/bin/env python3
"""Rough headless draw benchmark (dummy video driver).

Measures a calm exploration frame and a busy combat frame.  The numbers are
single-threaded CPU timings under the dummy SDL driver, so they are a
regression guide rather than an absolute browser budget.

    python tools/bench.py
"""
from __future__ import annotations

import os
import statistics
import sys
import time
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame  # noqa: E402

from main import Game  # noqa: E402


def bench(game: Game, label: str, frames: int = 90) -> None:
    for _ in range(5):
        game.update(1 / 60)
        game.draw()

    phases = {"world": [], "atmos": [], "effects": [], "hud": [], "full": []}
    for _ in range(frames):
        game.update(1 / 60)
        t0 = time.perf_counter()
        game.world.draw(game.canvas, game.camera, game.player,
                        game.combat.enemies)
        t1 = time.perf_counter()
        game.atmosphere.draw(game.canvas, game.camera, game.player)
        t2 = time.perf_counter()
        game.effects.draw_world(game.canvas, game.camera)
        game.effects.draw_overlay(game.canvas, game.camera)
        t3 = time.perf_counter()
        game.hud.draw(game.canvas, game.player, game.combat.engaged)
        t4 = time.perf_counter()
        game.present()
        t5 = time.perf_counter()
        phases["world"].append((t1 - t0) * 1000)
        phases["atmos"].append((t2 - t1) * 1000)
        phases["effects"].append((t3 - t2) * 1000)
        phases["hud"].append((t4 - t3) * 1000)
        phases["full"].append((t5 - t0) * 1000)

    print(f"\n[{label}]")
    for name, samples in phases.items():
        samples = samples[10:]
        print(f"  {name:7s} mean {statistics.mean(samples):6.2f} ms  "
              f"median {statistics.median(samples):6.2f} ms  "
              f"p95 {sorted(samples)[int(len(samples) * 0.95)]:6.2f} ms")


def main() -> None:
    game = Game()
    game.hud.time = 9.0
    game.player.x, game.player.y = 1500.0, 1080.0
    game.camera.snap(game.player.x + game.player.look[0],
                     game.player.y + game.player.look[1])
    bench(game, "exploration frame - open plaza", 45)

    # Busy combat frame: three knights near the plaza, active slash, sparks,
    # damage numbers and the engaged bar.
    game.restart()
    player = game.player
    player.x, player.y = 1660.0, 1210.0
    player.facing = "right"
    spots = ((1724.0, 1210.0), (1600.0, 1120.0), (1510.0, 1310.0))
    for enemy, (ex, ey) in zip(game.combat.enemies, spots):
        enemy.x = enemy.home_x = ex
        enemy.y = enemy.home_y = ey
    game.camera.snap(player.x + player.look[0], player.y + player.look[1])
    for swing in range(40):
        if swing % 12 == 0:
            player.request_attack()
        game.update(1 / 60)
        if game.effects.numbers:
            game.effects.spawn_impact(1724.0, 1180.0, heavy=(swing % 24 == 0))
        game.draw()
    bench(game, "combat frame - three knights, slash + particles + bar", 90)

    print(f"\n  active particles: {len(game.effects.particles)}  "
          f"slashes: {len(game.effects.slashes)}  "
          f"numbers: {len(game.effects.numbers)}  "
          f"enemies: {len(game.combat.enemies)}")
    pygame.quit()


if __name__ == "__main__":
    main()
