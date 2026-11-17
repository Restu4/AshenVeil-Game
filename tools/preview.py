#!/usr/bin/env python3
"""Render a set of preview screenshots without opening a window.

    python tools/preview.py

Useful for quickly checking composition after moving props or rebaking the
ground.  Screenshots are written to screenshots/.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
# Keep previews deterministic and never touch the real progression profile.
_PREVIEW_SAVE_DIR = tempfile.mkdtemp(prefix="ashen_veil_preview_")
os.environ.setdefault("ASHEN_VEIL_SAVE",
                      str(Path(_PREVIEW_SAVE_DIR) / "progress.json"))

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

    combat_shots(game, out)
    skill_shots(game, out)
    phase5_shots(game, out)
    shutil.rmtree(_PREVIEW_SAVE_DIR, ignore_errors=True)
    pygame.quit()


def _place_duel(game) -> None:
    """Put the player and one fallen knight face to face on open plaza ground."""
    game.restart()
    game.hud.time = 9.0
    player = game.player
    player.x, player.y = 1660.0, 1210.0
    player.facing = "right"
    player.vx = player.vy = 0.0
    knight = next(e for e in game.combat.enemies if e.key == "fallen_knight")
    for index, other in enumerate(game.combat.enemies, start=1):
        if other is knight:
            continue
        other.x = other.home_x = 2800.0
        other.y = other.home_y = 1000.0 + index * 70.0
    knight.x = knight.home_x = 1724.0
    knight.y = knight.home_y = 1210.0
    knight.facing = "left"
    from scripts import enemy_ai
    knight.state = enemy_ai.CHASE
    knight.aggro_timer = 3.0
    knight.attack_cooldown = 5.0
    game.camera.snap(player.x + player.look[0], player.y + player.look[1])


def _place_pack(game) -> None:
    """Three knights ring the player on open plaza ground."""
    from scripts import enemy_ai

    _place_duel(game)
    player = game.player
    player.x, player.y = 1632.0, 1420.0
    player.facing = "right"
    spots = ((56.0, 0.0), (-54.0, 6.0), (2.0, -58.0))
    for enemy, (dx, dy) in zip(game.combat.enemies, spots):
        enemy.x = enemy.home_x = player.x + dx
        enemy.y = enemy.home_y = player.y + dy
        enemy.facing = "left"
        enemy.state = enemy_ai.IDLE
        enemy.aggro_timer = 3.0
        enemy.attack_cooldown = 5.0
    game.combat.crit_chance = 0.0
    game.camera.snap(player.x + player.look[0], player.y + player.look[1])


def combat_shots(game, out: Path) -> None:
    """Deterministic combat stills: combo, dash, impact and death."""
    from scripts.combat_config import COMBO_WINDOW
    from scripts.player_combat import IDLE

    _place_duel(game)
    player = game.player
    player.request_attack()
    for _ in range(9):                       # active hit frames
        game.update(1 / 60)
    game.draw()
    pygame.image.save(game.canvas, out / "combat_impact.png")
    print("  combat_impact  slash + damage number + critical flash")

    _place_pack(game)
    player = game.player
    combat = player.combat
    combat.state = IDLE
    combat.attack_stage = 4                  # next request starts the finisher
    combat.combo_window = COMBO_WINDOW
    player.request_attack()
    for _ in range(12):
        game.update(1 / 60)
    game.draw()
    pygame.image.save(game.canvas, out / "combat_finisher.png")
    print("  combat_finisher five-hit finisher, nova and enemy bars")

    _place_pack(game)
    player = game.player
    player.facing = "right"
    player.request_dash()
    for _ in range(7):
        game.update(1 / 60)
    game.draw()
    pygame.image.save(game.canvas, out / "combat_dash.png")
    print("  combat_dash    dash streak + impact")

    _place_duel(game)
    player = game.player
    knight = game.combat.enemies[0]
    knight.health.current = 15.0
    player.request_attack()
    for _ in range(26):                      # hit, then the death dissolve
        game.update(1 / 60)
    game.draw()
    pygame.image.save(game.canvas, out / "combat_kill.png")
    print("  combat_kill    ash dissolve + hit flash")

    _place_duel(game)
    player = game.player
    player.health = 15.0
    player.combat.invuln = 0.0
    player.take_damage(15.0, 1780.0, 1210.0)
    for _ in range(40):
        game.update(1 / 60)
    game.draw()
    pygame.image.save(game.canvas, out / "combat_death.png")
    print("  combat_death   the death veil")


def skill_shots(game, out: Path) -> None:
    """Deterministic VOID ESSENCE stills: burst, step, wave and eclipse."""
    _place_pack(game)
    player = game.player
    skills = game.skills
    skills.energy.regen = 0.0
    skills.energy.current = 100.0
    check = skills.cast_burst()
    for _ in range(7):                       # ring + shards mid-expansion
        game.update(1 / 60)
    game.draw()
    pygame.image.save(game.canvas, out / "skill_void_burst.png")
    print(f"  skill_void_burst  Q radial detonation ({check})")

    _place_pack(game)
    player = game.player
    skills = game.skills
    skills.energy.regen = 0.0
    skills.energy.current = 100.0
    player.input_x, player.input_y = 1.0, 0.0
    check = skills.cast_shadow()
    for _ in range(8):                       # afterimage trail mid-dash
        game.update(1 / 60)
    game.draw()
    pygame.image.save(game.canvas, out / "skill_shadow_step.png")
    print(f"  skill_shadow_step E dash through the Void ({check})")

    _place_pack(game)
    player = game.player
    skills = game.skills
    skills.energy.regen = 0.0
    skills.energy.current = 100.0
    player.facing = "right"
    for index, enemy in enumerate(game.combat.enemies):
        enemy.x = enemy.home_x = player.x + 130.0 + index * 64.0
        enemy.y = enemy.home_y = player.y
    game.camera.snap(player.x + player.look[0], player.y + player.look[1])
    check = skills.cast_slash()
    for _ in range(13):                      # crescent travelling forward
        game.update(1 / 60)
    game.draw()
    pygame.image.save(game.canvas, out / "skill_void_slash.png")
    print(f"  skill_void_slash  R travelling crescent ({check})")

    _place_pack(game)
    player = game.player
    skills = game.skills
    skills.energy.regen = 0.0
    skills.energy.current = 100.0
    check = skills.cast_eclipse()
    for _ in range(20):                      # sigil still gathering
        game.update(1 / 60)
    game.draw()
    pygame.image.save(game.canvas, out / "skill_eclipse_windup.png")
    print(f"  skill_eclipse_windup  F gathering darkness ({check})")
    for _ in range(16):                      # detonation + screen darkening
        game.update(1 / 60)
    game.draw()
    pygame.image.save(game.canvas, out / "skill_eclipse_blast.png")
    print("  skill_eclipse_blast  F ultimate detonation")


def _advance(game, seconds: float) -> None:
    for _ in range(max(1, int(round(seconds * 60.0)))):
        game.update(1.0 / 60.0)


def _snap_camera(game) -> None:
    game.camera.snap(game.player.x + game.player.look[0],
                     game.player.y + game.player.look[1])


def _save(game, out: Path, name: str, note: str) -> None:
    game.draw()
    pygame.image.save(game.canvas, out / f"{name}.png")
    print(f"  {name:24s} {note}")


def _clear_stage(game) -> None:
    game.level.stage_elapsed = 1.0
    for enemy in list(game.combat.enemies):
        enemy.removed = True
        enemy.health.current = 0.0
    game.update(1.0 / 60.0)


def _idle_player(game, x: float, y: float, facing: str = "up") -> None:
    player = game.player
    player.x, player.y = x, y
    player.facing = facing
    player.vx = player.vy = 0.0
    player.animator.current_name = f"idle_{facing}"
    player.animator.current = player.animator.animations[
        player.animator.current_name
    ]
    _snap_camera(game)


def phase5_shots(game, out: Path) -> None:
    """Title, level select, the four stages and the guardian boss HUD."""
    from scripts.bosses.hollow_guardian import IDLE, MAX_HEALTH, WINDUP
    from scripts.level_config import STAGE_03
    from scripts.village_layout import ARENA_PLAYER_SPAWN

    # --- Title screen ---------------------------------------------------
    game.open_menu()
    game.menu.time = 1.4
    _advance(game, 0.2)
    _save(game, out, "phase5_menu",
          "title screen over the living village")

    # --- Level select: fresh profile, the road is sealed ---------------
    game.open_level_select("02")
    game.level_select.time = 1.2
    _advance(game, 0.2)
    _save(game, out, "phase5_select_locked",
          "Level 02 SEALED, boss and preview visible")

    # --- Level select: Level 01 complete, Level 02 unlocked ------------
    game.progression.complete_level("01")
    game.open_level_select("02")
    game.level_select.time = 1.2
    _advance(game, 0.2)
    _save(game, out, "phase5_select_unlocked",
          "Level 01 COMPLETE, Level 02 UNLOCKED")

    # --- Stage 1: abandoned village ------------------------------------
    game.start_level("01")
    game.hud.time = 9.0
    game.level.banner_timer = 0.0
    _advance(game, 0.35)
    game.level.banner_timer = 0.0
    _save(game, out, "phase5_stage1",
          "STAGE 1 objective and opening trio")

    # --- Stage 2: the Corrupted Warden on the west road ----------------
    _clear_stage(game)
    for enemy in game.combat.enemies:
        enemy.update = lambda *args, **kwargs: None
    _idle_player(game, 1120.0, 1120.0, "left")
    game.level.banner_timer = 0.0
    _advance(game, 0.3)
    game.level.banner_timer = 0.0
    _save(game, out, "phase5_stage2_warden",
          "STAGE 2 elite Warden and escorts")

    # --- Stage 3: the veil gate ----------------------------------------
    _clear_stage(game)
    _idle_player(game, STAGE_03.x + 96.0, STAGE_03.y + 34.0, "left")
    game.level.banner_timer = 0.0
    _advance(game, 0.3)
    game.level.banner_timer = 0.0
    _save(game, out, "phase5_shrine_gate",
          "STAGE 3 pulsing veil-gate objective")

    # --- Boss arena: intro, phase 1 ------------------------------------
    _idle_player(game, STAGE_03.x, STAGE_03.y, "up")
    game.update(1.0 / 60.0)                 # step into the gate
    _advance(game, 1.0)                     # fade out + fade in + intro
    game.level.banner_timer = 0.0
    _save(game, out, "phase5_boss_intro",
          "arena fade-in, guardian intro and boss bar")

    boss = game.level.boss.boss
    game.player.combat.invuln = 600.0
    _idle_player(game, ARENA_PLAYER_SPAWN[0], ARENA_PLAYER_SPAWN[1], "up")
    _advance(game, 1.6)                     # finish the intro
    boss.state = IDLE
    boss.attack_timer = 90.0
    game.level.banner_timer = 0.0
    _save(game, out, "phase5_boss_phase1",
          "PHASE 1 AWAKENING, 1200 HP boss bar")

    # --- Phase 2: corruption roar --------------------------------------
    boss.health.current = MAX_HEALTH * 0.69
    boss.take_damage(1.0, boss.x, boss.y, 0.0)
    _advance(game, 0.25)
    _save(game, out, "phase5_boss_phase2",
          "PHASE 2 CORRUPTION banner")

    # --- Phase 3: signature attack warning -----------------------------
    _advance(game, 1.5)
    boss.health.current = MAX_HEALTH * 0.32
    boss.take_damage(1.0, boss.x, boss.y, 0.0)
    _advance(game, 1.5)
    boss.phase = 3
    boss.state = WINDUP
    boss.attack_kind = "signature"
    boss.attack_time = boss._spec("signature")["windup"] * 0.55
    boss.attack_target = (game.player.x, game.player.y)
    boss.phase_banner = 0.0
    _save(game, out, "phase5_boss_phase3",
          "PHASE 3 VEIL COLLAPSE telegraph and crimson bar")

    # --- Death beat, then the victory screen ---------------------------
    boss.take_damage(99999.0, boss.x, boss.y, 0.0)
    _advance(game, 1.0)
    _save(game, out, "phase5_boss_death",
          "guardian death animation, bar already gone")

    _advance(game, 2.6)                     # manager -> victory state
    _advance(game, 0.4)
    if game.state == "VICTORY":
        _save(game, out, "phase5_victory",
              "victory screen with return and continue")
    else:                                   # pragma: no cover - safety net
        print(f"  phase5_victory skipped (state={game.state})")


if __name__ == "__main__":
    main()
