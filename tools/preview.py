#!/usr/bin/env python3
"""Render a set of preview screenshots without opening a window.

    python tools/preview.py

Useful for quickly checking composition after moving props or rebaking the
ground.  Screenshots are written to screenshots/.
"""
from __future__ import annotations

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

SHOTS = {
    "spawn": None,
    "plaza": ((1600, 1490), "up"),
    "church": ((1600, 1010), "up"),
    "south_gate": ((1600, 1960), "down"),
    "graveyard": ((2570, 1090), "up"),
    "ruins": ((2520, 2000), "up"),
    "tower": ((700, 1210), "left"),
    "field": ((880, 1830), "up"),
    "market": ((2010, 1280), "left"),
    "north_trail": ((1600, 520), "down"),
}


def main() -> None:
    out = ROOT / "screenshots"
    out.mkdir(exist_ok=True)
    game = Game()
    game.hud.time = 9.0
    for name, placement in SHOTS.items():
        if placement is None:
            game.player.x, game.player.y = 1500.0, 1140.0
            game.player.facing = "down"
        else:
            (x, y), facing = placement
            game.player.x, game.player.y = float(x), float(y)
            game.player.facing = facing
        game.player.vx = game.player.vy = 0.0
        game.player.animator.current_name = f"idle_{game.player.facing}"
        game.player.animator.current = game.player.animator.animations[
            game.player.animator.current_name
        ]
        game.camera.snap(game.player.x + game.player.look[0],
                         game.player.y + game.player.look[1])
        for _ in range(3):
            game.update(1 / 60)
        game.draw()
        pygame.image.save(game.canvas, out / f"{name}.png")
        print(f"  {name:12s} {game.player.x:6.0f},{game.player.y:6.0f}  "
              f"camera={game.camera.offset}")
    pygame.quit()


if __name__ == "__main__":
    main()
