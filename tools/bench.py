#!/usr/bin/env python3
"""Rough headless draw benchmark (dummy video driver)."""
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


def main() -> None:
    game = Game()
    game.hud.time = 9.0
    game.player.x, game.player.y = 1500.0, 1080.0
    game.camera.snap(game.player.x + game.player.look[0],
                     game.player.y + game.player.look[1])
    for _ in range(5):
        game.update(1 / 60)
        game.draw()

    frames = 90
    phases = {"world": [], "atmos": [], "hud": [], "full": []}
    for _ in range(frames):
        game.update(1 / 60)
        t0 = time.perf_counter()
        game.world.draw(game.canvas, game.camera, game.player)
        t1 = time.perf_counter()
        game.atmosphere.draw(game.canvas, game.camera, game.player)
        t2 = time.perf_counter()
        game.hud.draw(game.canvas, game.player)
        t3 = time.perf_counter()
        game.present()
        t4 = time.perf_counter()
        phases["world"].append((t1 - t0) * 1000)
        phases["atmos"].append((t2 - t1) * 1000)
        phases["hud"].append((t3 - t2) * 1000)
        phases["full"].append((t4 - t0) * 1000)

    for name, samples in phases.items():
        samples = samples[10:]
        print(f"{name:6s} mean {statistics.mean(samples):6.2f} ms  "
              f"median {statistics.median(samples):6.2f} ms  "
              f"p95 {sorted(samples)[int(len(samples) * 0.95)]:6.2f} ms")
    pygame.quit()


if __name__ == "__main__":
    main()
