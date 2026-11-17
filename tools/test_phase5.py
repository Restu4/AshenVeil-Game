#!/usr/bin/env python3
"""Headless Phase 5 acceptance tests for ASHEN VEIL.

Run from the project root:

    python tools/test_phase5.py

Phase 5 adds the level-select flow, a JSON progression save, the four-stage
Level 01 script and the three-phase Hollow Guardian.  Every check below is a
real assertion against the shipped code; no browser is claimed to have run.

Sections:
 1  save manager: defaults, corruption, roundtrip, atomic write, env override
 2  level configuration: four entries, one playable, lock chain metadata
 3  progression: locks, completion, persistence, status labels
 4  Level 01 stage flow: village -> warden -> shrine gate -> sealed arena
 5  Hollow Guardian: scale, stats, phases, warnings, hurtboxes, walls
 6  HUD: stage indicator geometry and boss bar visibility/placement
 7  victory: unlock, save, no auto-teleport, both buttons
 8  UI screens: menu, level select cards, previews, victory overlay
 9  integration hygiene: font coverage, arena sealing, async/web constraints
"""
from __future__ import annotations

import json
import math
import os
import shutil
import sys
import tempfile
from pathlib import Path

# All save writes go to a throw-away directory.  This must be set before any
# script module resolves the default profile path.
TEMP_ROOT = Path(tempfile.mkdtemp(prefix="ashen_veil_phase5_"))
GAME_SAVE = TEMP_ROOT / "game" / "progress.json"
os.environ["ASHEN_VEIL_SAVE"] = str(GAME_SAVE)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pygame  # noqa: E402

from main import SELECT, VICTORY, Game  # noqa: E402
from scripts.boss_manager import VICTORY_DELAY  # noqa: E402
from scripts.bosses.hollow_guardian import (  # noqa: E402
    ATTACK_TABLE,
    DEATH,
    IDLE,
    MAX_HEALTH,
    PHASE_NAMES,
    PHASE_ROAR,
    PHASE_SPEED,
    PHASE_THRESHOLDS,
    WINDUP,
    HollowGuardian,
)
from scripts.enemy_config import (  # noqa: E402
    ARCHETYPES,
    ENEMY_START_GROUP,
    get_archetype,
)
from scripts.hud import VOID_H, VOID_Y  # noqa: E402
from scripts.level_config import (  # noqa: E402
    LEVELS,
    STAGE_01,
    STAGE_02,
    STAGE_03,
    STAGE_04,
    get_level,
    level_index,
    next_level_id,
)
from scripts.level_manager import PORTAL_RADIUS, STAGE_TOTAL, WARDEN  # noqa: E402
from scripts.pixel_font import GLYPHS  # noqa: E402
from scripts.progression_manager import ProgressionManager  # noqa: E402
from scripts.save_manager import (  # noqa: E402
    SAVE_VERSION,
    SaveManager,
    canonical_data,
    default_data,
    default_save_file,
)
from scripts.ui.boss_hud import (  # noqa: E402
    BAR_H,
    BAR_W,
    BAR_X,
    BAR_Y,
    BossHUD,
)
from scripts.ui.level_select import CARD_H, CARD_W, CARD_Y, LevelSelect  # noqa: E402
from scripts.ui.main_menu import ITEMS, MainMenu  # noqa: E402
from scripts.ui.preview_art import PREVIEW_H, PREVIEW_W, preview_surface  # noqa: E402
from scripts.ui.stage_hud import PANEL as STAGE_PANEL  # noqa: E402
from scripts.ui.victory_screen import PANEL as VICTORY_PANEL  # noqa: E402
from scripts.ui.victory_screen import VictoryScreen  # noqa: E402
from scripts.village_layout import (  # noqa: E402
    ALL_PROPS,
    ARENA_BOSS_BOUNDS,
    ARENA_BOSS_SPAWN,
    ARENA_CAMERA_LIFT,
    ARENA_PLAYER_BOUNDS,
    ARENA_PLAYER_SPAWN,
    ARENA_PROPS,
    ARENA_RECT,
    ENEMY_SPAWN_POINTS,
    EXTRA_SOLIDS,
    SPAWN,
)
from settings import SCREEN_H, SCREEN_W  # noqa: E402

DT = 1.0 / 60.0
PASSED = 0


class Keys:
    def __init__(self, *pressed: int) -> None:
        self.pressed = set(pressed)

    def __getitem__(self, key: int) -> bool:
        return key in self.pressed


EMPTY = Keys()


def check(condition: bool, message: str) -> None:
    global PASSED
    if not condition:
        raise AssertionError(message)
    PASSED += 1
    print(f"  ok  {message}")


def section(title: str) -> None:
    print(f"\n[{title}]")


def new_progression(name: str) -> ProgressionManager:
    path = TEMP_ROOT / name / "progress.json"
    return ProgressionManager(SaveManager(path=path))


def advance(game: Game, seconds: float) -> None:
    """Advance the real game loop without reading a keyboard."""
    for _ in range(max(1, int(round(seconds / DT)))):
        game.update(DT)


def advance_boss(boss, player, collision, seconds: float) -> None:
    for _ in range(max(1, int(round(seconds / DT)))):
        boss.update(DT, player, collision)


def freeze_enemies(game: Game) -> None:
    for enemy in game.combat.enemies:
        enemy.update = lambda *args, **kwargs: None


def clear_scripted_group(game: Game) -> None:
    """Mark the current scripted group dead, then let the flow notice."""
    game.level.stage_elapsed = 1.0
    for enemy in list(game.combat.enemies):
        enemy.removed = True
        enemy.health.current = 0.0
    game.update(DT)


def reset_player(player, x: float, y: float, facing: str = "up") -> None:
    player.reset(x, y, facing)
    player.x, player.y = x, y
    player.combat.invuln = 0.0


def alpha_pixels(surface: pygame.Surface, rect: pygame.Rect | None = None) -> int:
    alpha = pygame.surfarray.array_alpha(surface)
    if rect is not None:
        alpha = alpha[rect.x:rect.right, rect.y:rect.bottom]
    return int((alpha > 0).sum())


def alpha_diff(a: pygame.Surface, b: pygame.Surface) -> int:
    aa = pygame.surfarray.array_alpha(a)
    bb = pygame.surfarray.array_alpha(b)
    return int((aa != bb).sum())


def colour_stats(surface: pygame.Surface) -> tuple[int, float]:
    """(unique sampled colours, sampled luminance std) for screen checks."""
    arr = pygame.surfarray.array3d(surface)[::5, ::5].reshape(-1, 3).astype(int)
    unique = len(np.unique(arr, axis=0))
    return unique, float(arr.std())


def font_supported(text: str) -> bool:
    return all(ch.isspace() or ch.upper() in GLYPHS for ch in text)


def telegraph_surface(boss, state: str, kind: str = "") -> pygame.Surface:
    boss.state = state
    boss.attack_kind = kind
    boss.attack_time = (boss._spec(kind)["windup"] * 0.5
                        if kind else 0.0)
    boss.attack_target = (boss.x, boss.y + 90.0)
    surface = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    boss.draw(surface, (int(boss.x) - SCREEN_W // 2,
                        int(boss.y) - SCREEN_H // 2))
    return surface


def main() -> None:
    pygame.init()
    pygame.display.set_mode((SCREEN_W, SCREEN_H))

    # ==================================================================
    section("1. Save manager: safe JSON profile")
    clean = SaveManager(path=TEMP_ROOT / "save" / "clean.json",
                        use_local_storage=False)
    fresh = clean.load()
    check(fresh == canonical_data(default_data()),
          "a missing save loads the canonical default profile")
    check(fresh["version"] == SAVE_VERSION and fresh["levels"] == {},
          "the default profile has a version and no fake completions")
    check(not clean.exists(), "loading a missing save does not create it")

    payload = {
        "version": SAVE_VERSION,
        "levels": {
            "01": {"completed": True, "boss_defeated": True,
                   "stages_cleared": 4},
            "02": {"completed": False, "boss_defeated": False,
                   "stages_cleared": 2},
        },
        "player": {"level": 9},
    }
    check(clean.save(payload), "the profile saves successfully")
    check(clean.exists(), "the save file appears on disk")
    check(not list(clean.path.parent.glob("*.tmp")),
          "the atomic write leaves no temporary file behind")
    on_disk = json.loads(clean.path.read_text(encoding="utf-8"))
    check(on_disk["levels"]["01"]["completed"] is True,
          "completion is stored as JSON")
    check(clean.load() == canonical_data(payload),
          "a save roundtrip preserves the canonical profile")

    corrupt = TEMP_ROOT / "save" / "corrupt.json"
    corrupt.parent.mkdir(parents=True, exist_ok=True)
    corrupt.write_text('{"version": 1, "levels": {', encoding="utf-8")
    broken = SaveManager(path=corrupt, use_local_storage=False)
    check(broken.load() == canonical_data(default_data()),
          "truncated JSON falls back to a clean profile")
    corrupt.write_text("[1, 2, 3]", encoding="utf-8")
    check(broken.load()["levels"] == {},
          "a wrong-shaped save never crashes the loader")
    corrupt.write_text("", encoding="utf-8")
    check(broken.load()["levels"] == {},
          "an empty save file is treated as a new profile")

    weird = canonical_data({
        "version": "nope",
        "player": {"level": "150"},
        "levels": {
            "01": {"completed": 1, "stages_cleared": "9"},
            "02": {"completed": False, "stages_cleared": -5},
            "03": "not a dict",
        },
    })
    check(weird["version"] == 1 and weird["player"]["level"] == 99,
          "corrupt numeric fields are clamped to valid values")
    check(weird["levels"]["01"]["completed"] is True
          and weird["levels"]["01"]["stages_cleared"] == 9,
          "valid fields are preserved through canonicalisation")
    check(weird["levels"]["02"]["stages_cleared"] == 0
          and "03" not in weird["levels"],
          "negative stages clamp to zero and junk entries are dropped")

    env_path = TEMP_ROOT / "env" / "custom.json"
    original_env = os.environ.get("ASHEN_VEIL_SAVE")
    os.environ["ASHEN_VEIL_SAVE"] = str(env_path)
    try:
        check(default_save_file() == env_path,
              "ASHEN_VEIL_SAVE overrides the profile path")
        env_save = SaveManager(use_local_storage=False)
        check(env_save.path == env_path,
              "the save manager honours the environment override")
        check(env_save.save(payload) and env_path.is_file(),
              "the overridden profile is written where expected")
        check(env_save._storage() is None,
              "desktop builds do not pretend to have localStorage")
    finally:
        if original_env is None:
            os.environ.pop("ASHEN_VEIL_SAVE", None)
        else:
            os.environ["ASHEN_VEIL_SAVE"] = original_env

    # ==================================================================
    section("2. Level configuration: four roads, one open")
    check(len(LEVELS) == 4, "there are exactly four level entries")
    check([lv.level_id for lv in LEVELS] == ["01", "02", "03", "04"],
          "levels are ordered 01 through 04")
    check([lv.number for lv in LEVELS] == [1, 2, 3, 4],
          "display numbers match the level ids")
    check([lv.name for lv in LEVELS] == [
        "ASHEN VILLAGE", "HOLLOW FOREST", "FORGOTTEN DUNGEON",
        "BLACKTHORN CASTLE",
    ], "every level has the required name")
    check([lv.playable for lv in LEVELS] == [True, False, False, False],
          "only Level 01 is playable in this build")
    check(all(lv.coming_soon == "MAP NOT YET FORGED"
              for lv in LEVELS[1:]),
          "levels 02-04 advertise that their maps are not forged")
    check(all(not lv.stages for lv in LEVELS[1:]),
          "levels 02-04 generate no unfinished stage data")

    level_01 = get_level("01")
    check(len(level_01.stages) == 4 and STAGE_TOTAL == 4,
          "Level 01 has four stages")
    check(tuple(s.name for s in level_01.stages) == (
        "ABANDONED VILLAGE", "CORRUPTED PATH", "FORGOTTEN SHRINE",
        "BOSS ARENA",
    ), "the four Level 01 stage names are exact")
    check(tuple(s.objective for s in level_01.stages) == (
        "CUT DOWN THE RISEN DEAD", "BREAK THE CORRUPTED WARDEN",
        "STEP INTO THE VEIL GATE", "DEFEAT THE HOLLOW GUARDIAN",
    ), "each stage exposes one clear objective")
    check(level_01.boss_name == "THE HOLLOW GUARDIAN",
          "Level 01 names the Hollow Guardian")
    check(all(s.summary for s in level_01.stages),
          "stage entries carry atmospheric summaries")
    check(math.isclose(math.hypot(STAGE_03.x - SPAWN[0],
                                  STAGE_03.y - SPAWN[1]),
                       0.0) is False,
          "the veil gate is a real world location, not the spawn")
    check(math.isclose(STAGE_04.x, ARENA_BOSS_SPAWN[0])
          and math.isclose(STAGE_04.y, ARENA_BOSS_SPAWN[1] + 318),
          "the arena objective sits inside the boss arena")

    previews = [lv.preview for lv in LEVELS]
    check(len(set(previews)) == 4
          and set(previews) == {"village", "forest", "dungeon", "castle"},
          "each level has a distinct preview diorama key")
    accents = [lv.accent for lv in LEVELS]
    check(len(set(accents)) == 4
          and all(len(c) == 3 and all(0 <= v <= 255 for v in c)
                  for c in accents),
          "each level has a distinct, valid accent colour")
    check([next_level_id(lv.level_id) for lv in LEVELS]
          == ["02", "03", "04", None],
          "the unlock chain terminates after Level 04")
    check([level_index(lv.level_id) for lv in LEVELS] == [0, 1, 2, 3],
          "level_index matches the configured order")
    check(get_level("99").level_id == "01",
          "an unknown level id safely resolves to Level 01")
    check(STAGE_01.x == SPAWN[0] and STAGE_01.y == SPAWN[1],
          "stage 1 starts where the player spawns")

    # ==================================================================
    section("3. Progression: completion unlocks the next road")
    prog = new_progression("progression")
    check(prog.is_unlocked("01") and prog.is_playable("01"),
          "Level 01 is open on a fresh profile")
    check(not prog.is_unlocked("02") and not prog.is_playable("02"),
          "Level 02 is locked on a fresh profile")
    check(prog.unlock_hint("02") == "CLEAR LEVEL 01 TO UNLOCK",
          "a locked level explains exactly how to open it")
    check(prog.status_label("01") == "AVAILABLE",
          "the open level reads AVAILABLE")
    check(prog.status_label("02") == "LOCKED",
          "the sealed level reads LOCKED")
    check(prog.stages_cleared("01") == 0,
          "a fresh profile has no stage records")

    prog.record_stage("01", 3)
    check(prog.stages_cleared("01") == 3,
          "stage progress is recorded")
    prog.record_stage("01", 1)
    check(prog.stages_cleared("01") == 3,
          "stage progress never regresses")
    check(prog.save.path.is_file(),
          "recording a stage writes the profile immediately")

    check(prog.complete_level("01") is True,
          "completing Level 01 reports a new completion")
    check(prog.is_completed("01") and prog.boss_defeated("01"),
          "completion and the boss flag are both set")
    check(prog.stages_cleared("01") == 4,
          "completing a level records all four stages")
    check(prog.is_unlocked("02") and not prog.is_unlocked("03"),
          "completion unlocks exactly the next level")
    check(prog.is_playable("02") is False,
          "an unlocked but unbuilt level is still not playable")
    check(prog.status_label("02") == "UNLOCKED",
          "an unlocked unbuilt level reads UNLOCKED")
    check(prog.status_label("01") == "COMPLETE",
          "a finished level reads COMPLETE")
    check(prog.complete_level("01") is False,
          "completing the same level twice is not a new unlock")

    reloaded = ProgressionManager(SaveManager(path=prog.save.path))
    check(reloaded.is_completed("01") and reloaded.is_unlocked("02"),
          "completion survives a reload (desktop restart/browser refresh)")
    check(reloaded.stages_cleared("01") == 4,
          "stage records survive a reload")
    check(reloaded.selection_after_victory("01") == "02",
          "victory selection prefers the newly opened level")
    check(reloaded.next_unplayed_level() == "02",
          "the next unplayed unlocked level is Level 02")

    reloaded.complete_level("02")
    check(reloaded.is_unlocked("03") and not reloaded.is_unlocked("04"),
          "the unlock chain advances one link at a time")
    reloaded.complete_level("03")
    check(reloaded.is_unlocked("04"),
          "completing Level 03 opens Level 04")

    saved_level = new_progression("level_preserved")
    saved_level.record_player_level(12)
    again = ProgressionManager(SaveManager(path=saved_level.save.path))
    check(again.player_level == 12,
          "player progress is preserved independently of level unlocks")

    reset = new_progression("reset")
    reset.complete_level("01")
    reset.reset_progress()
    check(reset.is_completed("01") is False
          and not reset.is_unlocked("02"),
          "resetting a profile closes the unlock chain again")

    corrupt_prog_path = TEMP_ROOT / "corrupt_prog" / "progress.json"
    corrupt_prog_path.parent.mkdir(parents=True, exist_ok=True)
    corrupt_prog_path.write_text("not json at all", encoding="utf-8")
    corrupt_prog = ProgressionManager(SaveManager(path=corrupt_prog_path))
    check(corrupt_prog.is_unlocked("01")
          and not corrupt_prog.is_unlocked("02"),
          "a corrupt profile is safe and starts at Level 01")

    # ==================================================================
    section("4. Level 01 stage flow")
    game = Game()
    check(game.state == "PLAY", "Game opens directly into the live run")
    check(game.level.stage_number == 1
          and game.level.stage_name == "ABANDONED VILLAGE",
          "the run starts on stage 1 ABANDONED VILLAGE")
    check(len(game.combat.enemies) == len(ENEMY_START_GROUP)
          and {e.key for e in game.combat.enemies}
          == set(ENEMY_START_GROUP),
          "stage 1 starts with the authored opening trio")
    check(game.combat.spawner.enabled is False,
          "the stage script disables the endless reinforcement trickle")
    check(game.combat.spawner.total_spawned == len(ENEMY_START_GROUP),
          "only the starting group has spawned")
    check(game.player.x == SPAWN[0] and game.player.y == SPAWN[1],
          "the player starts at the authored spawn")

    freeze_enemies(game)
    spawn_total = game.combat.spawner.total_spawned
    advance(game, 4.0)
    check(game.combat.spawner.total_spawned == spawn_total,
          "no reinforcements trickle in during a scripted stage")
    check(game.level.stage_number == 1,
          "the stage does not advance while its group lives")
    check(game.level.objective_detail.startswith("FOES REMAIN 03"),
          "the objective details the remaining foes")

    clear_scripted_group(game)
    check(game.level.stage_number == 2
          and game.level.stage_name == "CORRUPTED PATH",
          "clearing the trio advances to stage 2")
    keys = [e.key for e in game.combat.enemies]
    check("corrupted_warden" in keys,
          "stage 2 spawns the Corrupted Warden")
    check(keys.count("void_stalker") == 1
          and keys.count("ashen_cultist") == 1,
          "the Warden is accompanied by exactly two escorts")
    check(set(ARCHETYPES) == {"fallen_knight", "void_stalker",
                              "ashen_cultist"},
          "the Warden is an elite variant, not a fourth archetype")
    warden = next(e for e in game.combat.enemies
                  if e.key == "corrupted_warden")
    check(warden.name == "CORRUPTED WARDEN"
          and warden.health.maximum == WARDEN.max_health == 320.0,
          "the Warden uses its own name and 320 HP")
    check(warden.health.maximum > get_archetype("fallen_knight").max_health,
          "the Warden is tougher than a regular Fallen Knight")
    check(warden.damage > get_archetype("fallen_knight").damage,
          "the Warden hits harder than a regular Fallen Knight")
    check(math.hypot(warden.x - 902.0, warden.y - 1122.0) <= 90.0,
          "the Warden spawns on the western corrupted path")
    check(game.level.objective_detail.startswith("FOES REMAIN 03"),
          "stage 2 counts the Warden and both escorts")

    clear_scripted_group(game)
    check(game.level.stage_number == 3
          and game.level.stage_name == "FORGOTTEN SHRINE",
          "clearing the Warden opens the Forgotten Shrine stage")
    check(not game.combat.enemies,
          "no leftovers block the shrine approach")
    check(game.level.objective == "STEP INTO THE VEIL GATE",
          "stage 3 asks for the veil gate")
    check(game.level.objective_detail.startswith("VEIL GATE "),
          "stage 3 shows a distance to the gate")

    distance = math.hypot(game.player.x - STAGE_03.x,
                          game.player.y - STAGE_03.y)
    check(distance > PORTAL_RADIUS,
          "the player is not already standing in the gate")
    game.player.x, game.player.y = STAGE_03.x, STAGE_03.y
    game.update(DT)
    check(game.level.transition_phase == "out",
          "entering the veil gate starts the fade transition")
    check(game.level.boss.boss is None,
          "the boss does not exist before the fade completes")
    game.update(DT)
    check(game.level.transition_alpha > 0,
          "the veil fade is visibly active")

    advance(game, 0.5)
    check(game.level.stage_number == 4
          and game.level.stage_name == "BOSS ARENA",
          "the fade delivers the player to the boss arena")
    check(game.level.transition_phase == "in",
          "the arena opens with a fade-in")
    boss_manager = game.level.boss
    check(boss_manager.boss is not None and boss_manager.in_fight,
          "the Hollow Guardian encounter is now active")
    check(math.isclose(game.player.x, ARENA_PLAYER_SPAWN[0])
          and math.isclose(game.player.y, ARENA_PLAYER_SPAWN[1]),
          "the player arrives at the arena spawn")
    check(sum(1 for e in game.combat.enemies if getattr(e, "is_boss", False))
          == 1,
          "exactly one guardian exists")
    check(game.combat.spawner.enabled is False,
          "reinforcements stay disabled inside the arena")
    check(game.level.objective_detail == "NO RETREAT  ·  NO MERCY",
          "stage 4 tells the player the arena is sealed")

    advance(game, 0.5)
    check(game.level.transition_phase == "",
          "the arena fade finishes and normal play resumes")

    # The arena hugs the north edge of the world; the camera lift must frame
    # the whole guardian below the boss bar instead of clipping its horns.
    guardian = boss_manager.boss
    foot_y = guardian.y - game.camera.offset[1]
    sprite_top = foot_y - guardian.animator.foot_line
    check(ARENA_CAMERA_LIFT >= 200.0,
          "the arena camera aims far enough north for the tall guardian")
    check(sprite_top >= BAR_Y + BAR_H - 8,
          "the guardian's full silhouette clears the boss HUD")
    check(foot_y < SCREEN_H - 80,
          "the guardian's feet stay inside the play field")

    # The arena shell and the two clamp rectangles are the containment rules.
    collision = game.world.collision
    check(all(collision.segment_blocked(*a, *b, 4.0) for a, b in (
        ((2638.0, 300.0), (2638.0, 150.0)),   # north wall
        ((2638.0, 600.0), (2638.0, 800.0)),   # south wall
        ((2400.0, 462.0), (2200.0, 462.0)),   # west wall
        ((2900.0, 462.0), (3060.0, 462.0)),   # east wall
    )), "the shrine arena is sealed on all four sides")
    check(not collision.segment_blocked(ARENA_PLAYER_SPAWN[0],
                                       ARENA_PLAYER_SPAWN[1], 2638.0, 300.0,
                                       4.0),
          "the arena interior remains walkable")
    check(len(EXTRA_SOLIDS) >= 4, "the seal is built from explicit solids")

    probe = pygame.Rect(ARENA_RECT[0], ARENA_RECT[1],
                        ARENA_RECT[2] - ARENA_RECT[0],
                        ARENA_RECT[3] - ARENA_RECT[1])
    check(game.world.arena_rect == probe,
          "the world lays the shrine floor over the arena rect")
    check(game.world.arena_floor.get_size() == probe.size,
          "the baked arena floor matches the arena size")
    check(game.world.arena_floor.get_width() > 0,
          "the arena floor surface is real")

    allowed = {id(prop) for prop in ARENA_PROPS}
    inside = [prop for prop in ALL_PROPS
              if probe.collidepoint(prop.x, prop.y)]
    check(inside and all(id(prop) in allowed for prop in inside),
          "village props are stripped out of the arena, shrine props remain")
    check(any(prop.name == "shrine" for prop in inside),
          "the sealed shrine itself is present in the arena")
    check(any(prop.name == "portal" for prop in inside),
          "the dead veil gate is present in the arena")
    check(not any(probe.collidepoint(x, y)
                  for x, y, _facing in ENEMY_SPAWN_POINTS),
          "random village spawn points never point inside the arena")

    # Player cannot leave through dash/knockback: the manager clamps them.
    game.player.x, game.player.y = 100.0, 100.0
    game.update(DT)
    px0, py0, px1, py1 = ARENA_PLAYER_BOUNDS
    check(px0 <= game.player.x <= px1 and py0 <= game.player.y <= py1,
          "the boss encounter clamps the player inside the arena")
    reset_player(game.player, *ARENA_PLAYER_SPAWN)

    # ==================================================================
    section("5. The Hollow Guardian: stats, phases, warnings")
    boss = boss_manager.boss
    knight = get_archetype("fallen_knight")
    check(boss.health.maximum == MAX_HEALTH == 1200.0,
          "the guardian has exactly 1200 HP")
    check(boss.is_boss and boss.key == "hollow_guardian",
          "the guardian identifies itself as the boss")
    check(boss.half_w > knight.half_w * 2
          and boss.half_h > knight.half_h * 2,
          "the guardian's body is visibly larger than a knight")
    check(boss.animator.frame_size >= 96,
          "the guardian sprite frame is large on screen")
    check(max(PHASE_SPEED.values()) < knight.chase_speed,
          "even the last phase moves slower than a Fallen Knight")
    check(PHASE_SPEED[1] < PHASE_SPEED[2] < PHASE_SPEED[3],
          "speed rises across the three phases")
    check(boss.attack_range > knight.attack_range * 3,
          "the guardian threatens a much larger range")
    check(PHASE_THRESHOLDS == (0.70, 0.35),
          "phase thresholds are 70% and 35%")
    check(PHASE_NAMES == {1: "AWAKENING", 2: "CORRUPTION",
                          3: "LAST RESOLVE"},
          "the phase names match the design")

    reset_player(game.player, 2638.0, 600.0)
    mech = HollowGuardian(game.assets, *ARENA_BOSS_SPAWN,
                          effects=game.effects, camera=None)
    mech._collision = collision
    check(mech.state == "INTRO" and mech.phase == 1,
          "the guardian starts in its intro, phase 1")

    mech.health.current = MAX_HEALTH * 0.70
    mech.take_damage(1.0, mech.x, mech.y, 0.0)
    check(mech.phase == 2 and mech.state == PHASE_ROAR,
          "crossing 70% begins phase 2 with a roar")
    check("CORRUPTION" in mech.phase_banner_text,
          "the phase 2 banner names CORRUPTION")
    check(font_supported(mech.phase_banner_text),
          "the phase banner uses only glyphs the bitmap font owns")
    advance_boss(mech, game.player, collision, 1.4)
    check(mech.state != PHASE_ROAR,
          "the phase roar ends and the fight resumes")

    mech.health.current = MAX_HEALTH * 0.35
    mech.take_damage(1.0, mech.x, mech.y, 0.0)
    check(mech.phase == 3 and mech.state == PHASE_ROAR,
          "crossing 35% begins phase 3 LAST RESOLVE")
    advance_boss(mech, game.player, collision, 1.4)

    # Phase 1 only knows the slow sweep and slam; phase 2 adds the combo,
    # wave and mark; phase 3 adds the signature when its timer is ready.
    mech.phase = 1
    mech.rng.seed(11)
    p1 = {mech._choose_attack(150.0) for _ in range(60)}
    check(p1 <= {"sweep", "slam"},
          "phase 1 draws only from the slow sweep/slam pool")
    mech.phase = 2
    mech.rng.seed(22)
    p2 = {mech._choose_attack(150.0) for _ in range(80)}
    check(p2 <= {"sweep", "slam", "combo", "wave", "area"}
          and "combo" in p2,
          "phase 2 adds the twin sweep, void wave and veil mark")
    mech.phase = 3
    mech.signature_timer = 5.0
    mech.rng.seed(33)
    p3 = {mech._choose_attack(150.0) for _ in range(90)}
    check(p3 <= {"sweep", "slam", "combo", "wave", "area"}
          and "combo" in p3,
          "phase 3 keeps the phase 2 toolkit")
    mech.signature_timer = 0.0
    check(mech._choose_attack(150.0) == "signature",
          "phase 3 spends the ready timer on VEIL COLLAPSE")
    mech.signature_timer = 11.0

    check(set(ATTACK_TABLE) == {"sweep", "slam", "combo", "wave", "area",
                               "signature"},
          "the boss has six distinct attacks")
    check(all(spec["label"] and spec["label"] == spec["label"].upper()
              for spec in ATTACK_TABLE.values()),
          "every attack has a readable uppercase warning label")
    check(all(font_supported(spec["label"])
              for spec in ATTACK_TABLE.values()),
          "every warning label is renderable by the pixel font")
    check(all(spec["windup"] >= 0.55 for spec in ATTACK_TABLE.values()),
          "every attack has at least a 0.55 s warning window")
    check(ATTACK_TABLE["signature"]["windup"] >= 1.5,
          "the signature attack telegraphs for at least 1.5 s")
    check(all(spec["active"] > 0.0 and spec["recovery"] > 0.0
              for spec in ATTACK_TABLE.values()),
          "every attack has an active window and a recovery")
    check(ATTACK_TABLE["slam"]["radius"] >= 180.0
          and ATTACK_TABLE["sweep"]["reach"] >= 170.0,
          "the guardian's ground attacks cover a large area")

    mech.phase = 1
    mech.state = IDLE
    baseline = telegraph_surface(mech, IDLE)
    for kind in ATTACK_TABLE:
        warning = telegraph_surface(mech, WINDUP, kind)
        check(alpha_diff(baseline, warning) > 600,
              f"the {kind} wind-up paints a visible floor/ring warning")

    # Recovery shortens each phase; phase 3 is visibly more aggressive.
    mech.phase = 1
    mech.rng.seed(44)
    c1 = [mech._cooldown_after_attack() for _ in range(40)]
    mech.phase = 3
    mech.rng.seed(44)
    c3 = [mech._cooldown_after_attack() for _ in range(40)]
    check(min(c1) > max(c3),
          "phase 3 recovery pauses are shorter than phase 1")
    check(mech._spec("sweep")["windup"] < ATTACK_TABLE["sweep"]["windup"],
          "phase 3 wind-ups are faster than the phase 1 baseline")

    # Hurtboxes are fair: in front and in reach hurts, out of reach or
    # behind the facing does not.
    mech.phase = 1
    mech.x, mech.y = 2638.0, 462.0
    mech.facing = "right"
    spec = mech._spec("sweep")
    reset_player(game.player, mech.x + spec["reach"] - 20.0, mech.y)
    before = game.player.health
    mech._resolve_sweep(game.player, collision, spec, 20.0)
    check(game.player.health < before,
          "a sweep in front and in reach lands fairly")

    reset_player(game.player, mech.x + spec["reach"] + 60.0, mech.y)
    before = game.player.health
    mech._resolve_sweep(game.player, collision, spec, 20.0)
    check(game.player.health == before,
          "a sweep just out of reach misses")

    reset_player(game.player, mech.x - spec["reach"] + 20.0, mech.y)
    before = game.player.health
    mech._resolve_sweep(game.player, collision, spec, 20.0)
    check(game.player.health == before,
          "a sweep behind the guardian's facing misses")

    # Dodge/dash i-frames are authoritative for direct and hazard damage.
    reset_player(game.player, mech.x, mech.y + 120.0)
    game.player.combat.invuln = 0.8
    before = game.player.health
    mech._resolve_slam(game.player, collision, mech._spec("slam"), 26.0)
    check(game.player.health == before,
          "a slam cannot hurt a player inside dodge i-frames")

    blast = {
        "kind": "blast", "x": game.player.x, "y": game.player.y,
        "radius": 120.0, "delay": 0.0, "life": 0.5, "max_life": 0.5,
        "damage": 21.0, "hit": False, "signature": False,
    }
    mech._collision = collision
    mech.hazards = [dict(blast)]
    game.player.combat.invuln = 0.8
    before = game.player.health
    mech._update_hazards(DT, game.player)
    check(game.player.health == before,
          "a ground blast respects dodge i-frames")

    mech.hazards = [dict(blast)]
    game.player.combat.invuln = 0.0
    before = game.player.health
    mech._update_hazards(DT, game.player)
    check(game.player.health < before,
          "the same ground blast hurts once i-frames end")

    # Wall fairness: a slam radius may overlap through masonry, but the
    # segment check stops the damage from crossing the sealed shell.
    mech.x, mech.y = 2638.0, 300.0
    reset_player(game.player, 2638.0, 150.0)
    before = game.player.health
    mech._resolve_slam(game.player, collision, mech._spec("slam"), 26.0)
    check(game.player.health == before,
          "a slam never damages through the arena's north wall")

    reset_player(game.player, 2638.0, 450.0)
    before = game.player.health
    mech._resolve_slam(game.player, collision, mech._spec("slam"), 26.0)
    check(game.player.health < before,
          "the same slam damages a player on the open arena floor")

    # Area marks lock their target at cast time instead of tracking.
    mech.x, mech.y = 2638.0, 462.0
    mech.phase = 2
    mech.state = WINDUP
    mech.attack_kind = "area"
    mech.attack_time = ATTACK_TABLE["area"]["windup"] - 0.05
    mech.attack_target = (2500.0, 400.0)
    mech.hazards.clear()
    reset_player(game.player, 2800.0, 400.0)
    mech._update_attack(0.06, game.player, collision)
    check(len(mech.hazards) == 1
          and math.isclose(mech.hazards[0]["x"], 2500.0)
          and math.isclose(mech.hazards[0]["y"], 400.0),
          "a veil mark lands where it was telegraphed, not on the player")

    # The guardian stays inside the arena even when the player is far away.
    mech.x, mech.y = ARENA_BOSS_SPAWN
    mech.phase = 1
    mech.state = "CHASE"
    mech.attack_timer = 99.0
    game.player.x, game.player.y = 100.0, 100.0
    for _ in range(300):
        mech.update(DT, game.player, collision)
    bx0, by0, bx1, by1 = ARENA_BOSS_BOUNDS
    check(bx0 <= mech.x <= bx1 and by0 <= mech.y <= by1,
          "the guardian is clamped to the arena bounds while chasing")

    # A debug/loaded zero-health state must always die, never keep attacking.
    mech.health.current = 0.0
    mech.state = "CHASE"
    mech.update(DT, game.player, collision)
    check(mech.state == DEATH and mech.health.dead,
          "zero health always transitions the guardian into death")
    check(not mech.hazards,
          "death clears every pending ground hazard")
    for _ in range(int(3.6 / DT)):
        mech.update(DT, game.player, collision)
    check(mech.removed,
          "the corpse leaves the combat list after its death animation")
    reset_player(game.player, *ARENA_PLAYER_SPAWN)

    # ==================================================================
    section("6. HUD: stage indicator and boss bar")
    check(BAR_W == 620 and BAR_H == 64,
          "the boss bar is large but compact (620 x 64)")
    check(BAR_X == (SCREEN_W - BAR_W) // 2 and BAR_Y == 8,
          "the boss bar is centred at the top of the screen")
    check(BAR_Y + BAR_H < SCREEN_H * 0.2,
          "the boss bar never reaches into the play field")
    check(BAR_X > STAGE_PANEL.right,
          "the boss bar does not overlap the stage indicator")
    check(STAGE_PANEL.y > VOID_Y + VOID_H,
          "the stage indicator sits below the vitality bars")
    check(STAGE_PANEL.w <= 320 and STAGE_PANEL.h <= 48,
          "the stage indicator stays a small HUD element")

    hud = BossHUD()
    blank = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    hud.draw(blank, boss_manager)
    check(alpha_pixels(blank, pygame.Rect(BAR_X, BAR_Y, BAR_W, BAR_H)) > 8000,
          "the boss bar draws while the encounter is live")

    hidden = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    was_defeated = boss_manager.defeated
    boss_manager.defeated = True
    hud.draw(hidden, boss_manager)
    boss_manager.defeated = was_defeated
    check(alpha_pixels(hidden, pygame.Rect(BAR_X, BAR_Y, BAR_W, BAR_H)) == 0,
          "the boss bar disappears as soon as the guardian is defeated")

    dead = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    saved_health = boss.health.current
    boss.health.current = 0.0
    hud.draw(dead, boss_manager)
    boss.health.current = saved_health
    check(alpha_pixels(dead, pygame.Rect(BAR_X, BAR_Y, BAR_W, BAR_H)) == 0,
          "the boss bar also hides once the boss health pool is empty")

    stage_draw = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    game.level.stage_hud.draw(stage_draw, game.level)
    check(alpha_pixels(stage_draw, STAGE_PANEL) > 1000,
          "the stage HUD draws the stage, objective and pips")
    check(font_supported(f"STAGE {game.level.stage_number}/{STAGE_TOTAL}  ·  "
                         f"{game.level.stage_name}"),
          "the stage HUD line is fully renderable")
    check(font_supported(game.level.objective),
          "the objective line is fully renderable")

    # HUD is absent outside a boss fight.
    outside = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    hud.draw(outside, None)
    check(alpha_pixels(outside) == 0,
          "no boss bar is drawn without a boss manager")

    # ==================================================================
    section("7. Victory: animation, unlock, save, no auto-teleport")
    check(2.0 <= VICTORY_DELAY <= 3.2,
          "the victory beat is a short animation, not an instant cut")
    encounter = boss_manager.boss
    reset_player(game.player, *ARENA_PLAYER_SPAWN)
    victory_spot = (game.player.x, game.player.y)
    encounter.take_damage(99999.0, encounter.x, encounter.y, 0.0)
    check(encounter.state == DEATH and encounter.health.dead,
          "lethal damage drops the guardian into its death animation")
    check(encounter.hazards == [] and encounter.pending_swipe is None,
          "all guardian attacks stop when it dies")

    for _ in range(int((VICTORY_DELAY + 1.8) / DT)):
        game.update(DT)
        if game.state == VICTORY:
            break
    check(game.state == VICTORY,
          "the encounter hands off to the victory screen")
    check(game.progression.is_completed("01"),
          "victory marks Level 01 complete")
    check(game.progression.boss_defeated("01"),
          "victory records the boss kill")
    check(game.progression.is_unlocked("02"),
          "victory unlocks Level 02")
    check(get_level("02").playable is False,
          "the unlocked Level 02 is still a selection entry only")
    check(GAME_SAVE.is_file(),
          "victory writes the profile to the save location")
    check(game.level.last_save_ok is True,
          "the victory screen receives a successful save result")
    check(boss_manager.defeated and not boss_manager.in_fight,
          "the encounter is marked defeated")
    check(math.isclose(game.player.x, victory_spot[0])
          and math.isclose(game.player.y, victory_spot[1]),
          "victory does not teleport or reset the player")

    persisted = json.loads(GAME_SAVE.read_text(encoding="utf-8"))
    check(persisted["levels"]["01"]["completed"] is True
          and persisted["levels"]["02"]["completed"] is False,
          "the saved JSON contains the completion and the untouched next road")

    advance(game, 5.0)
    check(game.state == VICTORY,
          "the victory screen waits for the player (no auto-continue)")
    check(game.level.level_id == "01",
          "victory never silently loads the next level")

    check(game.victory.index == 0 and game.victory.selected == "continue",
          "CONTINUE is the default victory choice")
    game.handle_event(pygame.event.Event(
        pygame.KEYDOWN, {"key": pygame.K_RETURN, "mod": 0,
                         "unicode": "\r", "scancode": 0}))
    check(game.state == SELECT and game.level_select.selected_id == "02",
          "CONTINUE opens level select focused on the unlocked road")
    check(game.level_select.can_play("02") is False,
          "the focused Level 02 cannot be started (map not forged)")
    locked_action = game.level_select._try_play()
    check(locked_action == "locked"
          and game.level_select.message != "",
          "pressing Play on an unbuilt level explains the lock")
    check(game.start_level("02") is False and game.state == SELECT,
          "start_level refuses a level without a map")

    # Return path: preselect the level just completed.
    game.state = VICTORY
    game.victory.open(get_level("01"), get_level("02"))
    game.victory.index = 1
    game.handle_event(pygame.event.Event(
        pygame.KEYDOWN, {"key": pygame.K_RETURN, "mod": 0,
                         "unicode": "\r", "scancode": 0}))
    check(game.state == SELECT and game.level_select.selected_id == "01",
          "RETURN TO LEVEL SELECT focuses the completed level")

    # Replaying Level 01 starts a clean stage 1 while keeping progression.
    check(game.start_level("01") is True,
          "a completed level can be replayed")
    check(game.level.stage_number == 1
          and len(game.combat.enemies) == len(ENEMY_START_GROUP),
          "a replay restarts at stage 1 with the opening trio")
    check(game.progression.is_completed("01"),
          "replaying does not erase the saved completion")

    game.restart()
    check(game.level.stage_number == 1
          and math.isclose(game.player.x, SPAWN[0])
          and math.isclose(game.player.y, SPAWN[1]),
          "restart returns to Level 01 stage 1 at the spawn")
    check(game.level.boss.boss is None,
          "restart clears any boss encounter")
    check(len(game.combat.enemies) == len(ENEMY_START_GROUP),
          "restart rebuilds exactly the opening trio")
    check(game.combat.spawner.enabled is False,
          "restart re-locks the scripted stage spawner")

    # ==================================================================
    section("8. UI screens: menu, level select, previews, victory")
    ui_prog = new_progression("ui")
    menu = MainMenu(ui_prog)
    check(ITEMS == ("BEGIN DESCENT", "LEVEL SELECT", "QUIT"),
          "the title menu offers begin, level select and quit")
    check(menu.selected == "BEGIN DESCENT",
          "BEGIN DESCENT is the default menu item")
    menu.handle_event(pygame.event.Event(
        pygame.KEYDOWN, {"key": pygame.K_DOWN, "mod": 0,
                         "unicode": "", "scancode": 0}))
    check(menu.selected == "LEVEL SELECT",
          "keyboard navigation reaches LEVEL SELECT")
    menu.handle_event(pygame.event.Event(
        pygame.KEYDOWN, {"key": pygame.K_RETURN, "mod": 0,
                         "unicode": "\r", "scancode": 0}))
    check(menu.selected == "LEVEL SELECT",
          "ENTER activates the highlighted menu entry")
    backdrop = pygame.Surface((SCREEN_W, SCREEN_H))
    game._draw_world()
    backdrop.blit(game.canvas, (0, 0))

    menu_surface = backdrop.copy()
    menu.draw(menu_surface)
    unique, spread = colour_stats(menu_surface)
    check(unique > 40 and spread > 12,
          "the title screen renders over live atmospheric art, not a blank list")

    select = LevelSelect(game.assets, ui_prog)
    check(select.selected_id == "01",
          "level select starts on Level 01")
    check(select.can_play("01") and not select.can_play("02"),
          "level select obeys the lock state")
    rects = [select.card_rect(i) for i in range(len(LEVELS))]
    check(all(0 <= r.x and r.right <= SCREEN_W and r.bottom <= SCREEN_H
              for r in rects),
          "all four level cards fit on screen")
    check(all(rects[i].right <= rects[i + 1].x for i in range(3)),
          "the four cards do not overlap")
    check(all(r.h == CARD_H and r.w == CARD_W and r.y == CARD_Y
              for r in rects),
          "the cards share a consistent large size")

    for index, level in enumerate(LEVELS):
        surface = backdrop.copy()
        select.index = index
        select.draw(surface)
        unique, spread = colour_stats(surface)
        check(unique > 60 and spread > 10,
              f"the Level {level.level_id} card screen renders full art")
    select.index = 0

    preview_surfaces = {key: preview_surface(game.assets, key)
                        for key in ("village", "forest", "dungeon", "castle")}
    check(all(s.get_size() == (PREVIEW_W, PREVIEW_H)
              for s in preview_surfaces.values()),
          "each preview is a 288 x 178 diorama")
    fingerprints = set()
    for key, surf in preview_surfaces.items():
        unique, spread = colour_stats(surf)
        check(unique > 80 and spread > 8,
              f"the {key} preview is detailed atlas art, not a flat rectangle")
        fingerprints.add(pygame.image.tostring(surf, "RGB"))
    check(len(fingerprints) == 4,
          "the four previews are visually distinct")
    check(preview_surface(game.assets, "village") is
          preview_surface(game.assets, "village"),
          "baked previews are cached for the browser frame budget")

    check(select.handle_event(pygame.event.Event(
        pygame.KEYDOWN, {"key": pygame.K_ESCAPE, "mod": 0,
                         "unicode": "", "scancode": 0})) == "back",
          "ESC leaves level select")
    check(select.handle_event(pygame.event.Event(
        pygame.KEYDOWN, {"key": pygame.K_RETURN, "mod": 0,
                         "unicode": "\r", "scancode": 0})) == ("play", "01"),
          "ENTER starts the open level")
    select.index = 1
    check(select._try_play() == "locked",
          "a locked card cannot start a level")

    victory_screen = VictoryScreen(ui_prog)
    victory_screen.open(get_level("01"), get_level("02"))
    check(victory_screen.selected == "continue",
          "the victory overlay defaults to CONTINUE")
    vic_surface = backdrop.copy()
    victory_screen.draw(vic_surface)
    unique, spread = colour_stats(vic_surface)
    check(unique > 30 and spread > 8,
          "the victory overlay renders its full panel and art")
    check(0 <= VICTORY_PANEL.x and VICTORY_PANEL.right <= SCREEN_W
          and 0 <= VICTORY_PANEL.y and VICTORY_PANEL.bottom <= SCREEN_H,
          "the victory panel fits inside the screen")
    victory_screen.handle_event(pygame.event.Event(
        pygame.KEYDOWN, {"key": pygame.K_RIGHT, "mod": 0,
                         "unicode": "", "scancode": 0}))
    check(victory_screen.selected == "select",
          "the victory overlay can switch to RETURN")
    check(victory_screen.handle_event(pygame.event.Event(
        pygame.KEYDOWN, {"key": pygame.K_RETURN, "mod": 0,
                         "unicode": "\r", "scancode": 0})) == "select",
        "the victory overlay reports the chosen action")

    # Mouse coordinates are mapped through the same letterbox as present().
    old_size = pygame.display.get_surface().get_size()
    try:
        pygame.display.set_mode((1280, 800), pygame.RESIZABLE)
        mapped = game._ui_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, {"pos": (640, 400), "button": 1}))
        check(mapped.pos == (640, 360),
              "letterboxed mouse clicks map onto the internal canvas")
        pygame.display.set_mode((1920, 1080), pygame.RESIZABLE)
        mapped = game._ui_event(pygame.event.Event(
            pygame.MOUSEMOTION, {"pos": (960, 540), "rel": (0, 0),
                                 "buttons": (0, 0, 0)}))
        check(mapped.pos == (640, 360),
              "scaled window mouse motion maps onto the internal canvas")
        game.present()
    finally:
        pygame.display.set_mode(old_size)

    # ==================================================================
    section("9. Integration hygiene")
    rendered_strings = []
    for level in LEVELS:
        rendered_strings.extend([level.name, level.subtitle,
                                 level.description, level.boss_name,
                                 level.boss_subtitle, level.coming_soon])
        for stage in level.stages:
            rendered_strings.extend([stage.name, stage.objective,
                                     stage.summary])
    rendered_strings.extend(ITEMS)
    rendered_strings.extend(spec["label"] for spec in ATTACK_TABLE.values())
    rendered_strings.extend(PHASE_NAMES.values())
    rendered_strings.extend([
        "PHASE 2 · CORRUPTION", "THE HOLLOW GUARDIAN FALLS",
        "LEVEL 01 COMPLETE", "THE ROAD CONTINUES · ITS MAP IS NOT YET FORGED",
        "STAGES CLEARED 4/4   ·   BOSS DEFEATED",
        "CLEAR LEVEL 01 TO UNLOCK", "MAP NOT YET FORGED",
    ])
    check(all(font_supported(text) for text in rendered_strings),
          "every rendered Phase 5 string uses glyphs the bitmap font owns")
    check(all(font_supported(text) for text in (
        "CHOOSE YOUR DESCENT", "ONLY THE ASHEN VILLAGE STANDS OPEN",
        "ARROWS SELECT   ENTER PLAY   ESC BACK",
        "ARROWS CHOOSE   ENTER CONFIRM", "CONTINUE",
        "RETURN TO LEVEL SELECT", "THE VEIL WAITS",
    )), "the menu/select/victory control strings are renderable")

    for relative in (
        "scripts/save_manager.py",
        "scripts/progression_manager.py",
        "scripts/level_config.py",
        "scripts/level_manager.py",
        "scripts/bosses/hollow_guardian.py",
        "scripts/bosses/guardian_art.py",
        "scripts/ui/main_menu.py",
        "scripts/ui/level_select.py",
        "scripts/ui/preview_art.py",
        "scripts/ui/boss_hud.py",
        "scripts/ui/stage_hud.py",
        "scripts/ui/victory_screen.py",
        "scripts/arena_art.py",
    ):
        check((ROOT / relative).is_file(),
              f"{relative} ships with the game")

    main_source = (ROOT / "main.py").read_text(encoding="utf-8")
    check("async def main" in main_source and "await game.run()" in main_source,
          "the Phase 5 entry point keeps the Pygbag async loop")
    check("await asyncio.sleep(0)" in main_source,
          "the frame loop still yields to the browser")
    check(all(state in main_source for state in
              ("MENU", "SELECT", "PLAY", "VICTORY")),
          "main.py routes all four screen states")
    check("game.open_menu()" in main_source,
          "only main() opens the title screen (tests keep a live Game)")
    check("json" not in main_source,
          "saving stays isolated behind the save manager")

    # The arena must be reachable only through the scripted veil transition:
    # no spawn point and no stage-1 enemy lives inside it.
    check(bool(ENEMY_SPAWN_POINTS) and all(
        not (ARENA_RECT[0] <= x <= ARENA_RECT[2]
             and ARENA_RECT[1] <= y <= ARENA_RECT[3])
        for x, y, _facing in ENEMY_SPAWN_POINTS),
        "no random enemy spawn point sits inside the boss arena")

    print(f"\nALL PHASE 5 CHECKS PASSED ({PASSED} assertions).")


if __name__ == "__main__":
    try:
        main()
    finally:
        pygame.quit()
        shutil.rmtree(TEMP_ROOT, ignore_errors=True)
