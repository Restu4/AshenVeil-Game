#!/usr/bin/env python3
"""Headless Phase 7 acceptance tests for ASHEN VEIL character progression.

Run from the project root:

    python tools/test_phase7.py

Sections:
  1  configuration: EXP curve, rewards, attribute and skill grants
  2  ExpManager: multi-level-ups, cap, points, allocation and reset
  3  kill rewards: tiers, once-only guards, quest EXP, reload safety
  4  attributes: real live stat effects and idempotent recompute
  5  skill tree: 12 nodes, locks, prerequisites, purchase and modifiers
  6  Q/E/R/F: original abilities still work with upgrades applied
  7  character and tree screens: controls, clicks, drawing and font safety
  8  level-up feedback: pause, burst, notification and guarded audio
  9  HUD: compact EXP bar without moving HP/VOID/DASH geometry
 10  save schema: validation, legacy upgrades, additive roundtrip
 11  source tree and Pygbag web archive completeness
"""
from __future__ import annotations

import json
import math
import os
import sys
import tarfile
import tempfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TMP_ROOT = Path(tempfile.mkdtemp(prefix="ashen_veil_phase7_"))
os.environ["ASHEN_VEIL_SAVE"] = str(TMP_ROOT / "progress.json")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame  # noqa: E402

from main import (  # noqa: E402
    CHARACTER, INVENTORY, PLAY, SKILL_TREE, Game,
)
from scripts.exp_manager import ExpManager  # noqa: E402
from scripts.hud import (  # noqa: E402
    DASH_H, DASH_W, DASH_X, DASH_Y, EXP_H, EXP_W, EXP_X, EXP_Y,
    HP_H, HP_W, HP_X, HP_Y, VOID_H, VOID_W, VOID_X, VOID_Y,
)
from scripts.pixel_font import GLYPHS  # noqa: E402
from scripts.progression_config import (  # noqa: E402
    ATTRIBUTE_POINTS_PER_LEVEL, EXP_REWARDS, MAX_LEVEL, START_LEVEL,
    attribute_points_for_level, defeated_key, enemy_tier, exp_for_enemy,
    exp_for_level, skill_points_for_level,
)
from scripts.save_manager import (  # noqa: E402
    SAVE_VERSION, canonical_data, default_data,
)
from scripts.skill_config import (  # noqa: E402
    BURST_COST, BURST_DAMAGE, ECLIPSE_COST, ECLIPSE_DAMAGE, ECLIPSE_RADIUS,
    SHADOW_COST, SLASH_COST, SLASH_DAMAGE,
    VOID_ENERGY_MAX, VOID_REGEN_PER_SEC,
)
from scripts.skill_modifiers import compute_modifiers  # noqa: E402
from scripts.skill_tree_config import (  # noqa: E402
    BRANCHES, NODES, nodes_for_branch,
)
from scripts.skill_tree_manager import (  # noqa: E402
    AVAILABLE, LOCKED, OWNED, SkillTreeManager,
)
from scripts.skills.eclipse import eclipse_damage, eclipse_radius  # noqa: E402
from scripts.skills.void_burst import burst_damage  # noqa: E402
from scripts.skills.void_slash import slash_damage  # noqa: E402
from scripts.ui.character_screen import (  # noqa: E402
    CLOSE_RECT as CHAR_CLOSE, PLUS_RECTS, RESET_RECT, CharacterScreen,
)
from scripts.ui.skill_tree_screen import (  # noqa: E402
    CARD_RECTS, CLOSE_RECT as TREE_CLOSE, SkillTreeScreen,
)

PASSED = 0
FAILED: list[str] = []


def check(condition: bool, message: str) -> None:
    global PASSED
    if condition:
        PASSED += 1
        print(f"  ok  {message}")
    else:
        FAILED.append(message)
        print(f"  FAIL  {message}")


def section(title: str) -> None:
    print(f"\n[{title}]")


def font_ok(text) -> bool:
    return all(ch.isspace() or ch.upper() in GLYPHS for ch in str(text))


def fake_enemy(enemy_id: int, key: str = "void_stalker",
               boss: bool = False, subtitle: str = "",
               alive: bool = False):
    return SimpleNamespace(id=enemy_id, key=key, is_boss=boss,
                           subtitle=subtitle, alive=alive, x=1000.0,
                           y=1000.0)


def fresh_game() -> Game:
    """Construct a Game with a brand new temporary profile."""
    folder = Path(tempfile.mkdtemp(prefix="ashen_veil_p7_game_",
                                   dir=str(TMP_ROOT)))
    os.environ["ASHEN_VEIL_SAVE"] = str(folder / "progress.json")
    return Game()


def key_event(key: int) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN,
                              {"key": key, "mod": 0, "unicode": "",
                               "scancode": 0})


def click_event(pos) -> pygame.event.Event:
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                              {"pos": pos, "button": 1})


def main() -> None:
    # ==================================================================
    section("1. Progression configuration and reward tuning")
    check(START_LEVEL == 1 and MAX_LEVEL == 30,
          "a fresh wanderer starts at 1 and progression caps at 30")
    check(ATTRIBUTE_POINTS_PER_LEVEL == 3, "each level grants 3 attribute points")
    curve = [exp_for_level(level) for level in range(1, MAX_LEVEL + 1)]
    check(curve[0] == 60 and curve[1] == 68 and curve[2] == 77,
          f"EXP curve follows round(60 * 1.13 ** (level-1)) {curve[:3]}")
    check(all(right > left for left, right in zip(curve, curve[1:])),
          "the EXP requirement rises strictly every level")
    check(curve[-1] > curve[0] * 20, "late levels are meaningfully harder")
    check(attribute_points_for_level(1) == 0
          and attribute_points_for_level(2) == 3
          and attribute_points_for_level(MAX_LEVEL) == 87,
          "attribute grants scale from zero to 87 points")
    check(skill_points_for_level(1) == 0
          and skill_points_for_level(2) == 0
          and skill_points_for_level(3) == 1
          and skill_points_for_level(MAX_LEVEL) == 14,
          "one skill point is granted every two levels")
    check(EXP_REWARDS == {"regular": 20, "strong": 40,
                          "elite": 100, "boss": 500},
          "all four enemy reward tiers are configurable")
    check(enemy_tier(fake_enemy(1, "void_stalker")) == "regular"
          and enemy_tier(fake_enemy(2, "fallen_knight")) == "strong"
          and enemy_tier(fake_enemy(3, "corrupted_warden")) == "elite"
          and enemy_tier(fake_enemy(4, "void_stalker", subtitle="VOID ELITE")) == "elite"
          and enemy_tier(fake_enemy(5, boss=True)) == "boss",
          "enemy tiers reuse existing keys, subtitles and the boss flag")
    check([exp_for_enemy(fake_enemy(i, key)) for i, key in enumerate(
        ("void_stalker", "fallen_knight", "corrupted_warden"))] == [20, 40, 100]
        and exp_for_enemy(fake_enemy(9, boss=True)) == 500,
        "EXP rewards resolve from the configured tier table")
    check(defeated_key(fake_enemy(42), "01") == "01:42"
          and defeated_key(fake_enemy(1, boss=True), "01") == "01:boss",
          "anti-farm markers are stable per level and enemy")

    # ==================================================================
    section("2. EXP manager: levels, points and allocation")
    manager = ExpManager()
    check(manager.level == START_LEVEL and manager.exp == 0
          and manager.total_exp == 0 and not manager.defeated,
          "a new manager owns a clean level-1 snapshot")
    events = manager.award_exp(300)
    check(len(events) >= 3 and [e["level"] for e in events] ==
          list(range(2, 2 + len(events))),
          f"one reward resolves multiple sequential levels {events}")
    check(all(e["attribute_points"] == 3 for e in events)
          and sum(e["skill_points"] for e in events) >= 1,
          "each level-up grants points, including skill points on even levels")
    expected_exp = 300 - sum(exp_for_level(level)
                             for level in range(1, manager.level))
    check(manager.exp == expected_exp and manager.total_exp == 300,
          "leftover EXP and lifetime EXP are tracked separately")
    check(manager.exp_required == exp_for_level(manager.level)
          and 0.0 <= manager.exp_ratio <= 1.0,
          "the HUD ratio reflects the manager's current level")
    before = manager.attribute_points
    check(manager.allocate_attribute("STR")
          and manager.attributes["str"] == 1
          and manager.attribute_points == before - 1,
          "attribute allocation is case-insensitive and spends one point")
    check(not manager.allocate_attribute("luck")
          and not manager.allocate_attribute("")
          and not manager.allocate_attribute(None),
          "unknown attribute names are rejected without spending points")
    check(manager.reset_attributes()
          and sum(manager.attributes.values()) == 0
          and manager.attribute_points == before,
          "reset refunds every allocated attribute point")
    check(not manager.reset_attributes(),
          "resetting an empty build is a no-op")
    manager.attributes["str"] = 10
    manager.attribute_points = 5
    check(not manager.allocate_attribute("str")
          and manager.attribute_points == 5,
          "attributes stop at rank 10 and never overspend")
    manager.award_exp(10 ** 7)
    check(manager.level == MAX_LEVEL and manager.exp == 0
          and manager.is_max and manager.exp_ratio == 1.0,
          "EXP at the cap is discarded and the bar reads full")
    check(manager.award_exp(500) == [] and manager.level == MAX_LEVEL,
          "extra EXP past level 30 has no effect")
    fresh = ExpManager()
    check(isinstance(fresh.award_quest_exp(20), list)
          and fresh.total_exp == 20,
          "future quests have a direct configurable EXP API")

    # ==================================================================
    section("3. Kill rewards, once-only guards and reload safety")
    game = fresh_game()
    check(game.exp.level == START_LEVEL and game.player.level == START_LEVEL
          and game.stats.level == START_LEVEL,
          "Game, player and stats all begin at level 1")
    total_before = game.exp.total_exp
    regular = fake_enemy(101)
    game.combat.on_kill(regular)
    check(game.exp.total_exp == total_before + 20,
          "a regular kill grants 20 EXP through the shared kill hook")
    game.combat.on_kill(regular)
    game.combat.on_kill(fake_enemy(101))
    check(game.exp.total_exp == total_before + 20,
          "repeat deaths of the same enemy cannot be farmed")
    game.combat.on_kill(fake_enemy(102, alive=True))
    check(game.exp.total_exp == total_before + 20,
          "a live enemy never grants EXP")
    game.combat.on_kill(fake_enemy(9001, "hollow_guardian", boss=True))
    check(game.exp.total_exp == total_before + 520,
          "the Hollow Guardian grants the configured boss reward")
    game.combat.on_kill(fake_enemy(200, "corrupted_warden"))
    check(game.exp.total_exp == total_before + 620,
          "the Corrupted Warden grants the elite reward")
    game.combat.on_kill(fake_enemy(201, "fallen_knight"))
    check(game.exp.total_exp == total_before + 660,
          "Fallen Knights grant the strong reward")
    game.exp.award_quest_exp(7)
    check(game.exp.total_exp == total_before + 667,
          "quest EXP stacks on top of kill EXP")
    saved_level = game.exp.level
    saved_total = game.exp.total_exp
    game._save_progression()
    reloaded = Game()
    check(reloaded.exp.level == saved_level
          and reloaded.exp.total_exp == saved_total,
          "a new Game restores the saved level and lifetime EXP")
    reloaded.combat.on_kill(fake_enemy(101))
    reloaded.combat.on_kill(fake_enemy(9001, "hollow_guardian", boss=True))
    check(reloaded.exp.total_exp == saved_total,
          "reloading the level does not re-award defeated enemies")
    check("01:101" in reloaded.exp.defeated
          and "01:boss" in reloaded.exp.defeated,
          "kill markers use level-qualified enemy and boss keys")
    reloaded.restart()
    check(reloaded.exp.level == saved_level
          and reloaded.exp.total_exp == saved_total,
          "restarting a level preserves character progression")

    # ==================================================================
    section("4. Attributes change real gameplay statistics")
    game = fresh_game()
    game.exp.award_exp(300)
    base = game.stats.as_dict()
    game.exp.allocate_attribute("str")
    check(math.isclose(game.stats.attack, base["attack"] + 2.0),
          "one STR adds exactly 2 real attack damage")
    game.exp.allocate_attribute("vit")
    check(math.isclose(game.stats.max_hp, base["max_hp"] + 12.0)
          and math.isclose(game.player.health_max, game.stats.max_hp),
          "one VIT adds 12 maximum HP to the live player pool")
    game.exp.allocate_attribute("agi")
    check(math.isclose(game.stats.speed, base["speed"] + 2.0)
          and math.isclose(game.stats.crit_chance, base["crit_chance"] + 0.01),
          "one AGI adds 2 speed and 1 PCT critical chance")
    game.exp.allocate_attribute("int")
    check(math.isclose(game.stats.max_void, base["max_void"] + 4.0)
          and math.isclose(game.skills.energy.maximum, game.stats.max_void),
          "one INT adds 4 maximum Void to the live energy pool")
    check(math.isclose(game.stats.void_power, 1.02)
          and math.isclose(game.skills.mods.void_power, 1.02),
          "one INT adds 2 PCT Void power to the skill modifiers")
    game.equipment.recompute()
    game.equipment.recompute()
    check(math.isclose(game.stats.attack, base["attack"] + 2.0)
          and math.isclose(game.stats.max_hp, base["max_hp"] + 12.0)
          and math.isclose(game.stats.speed, base["speed"] + 2.0),
          "equipment recomputes never discard attribute bonuses")
    game.exp.reset_attributes()
    check(game.stats.as_dict() == base
          and math.isclose(game.skills.mods.void_power, 1.0),
          "resetting attributes restores the exact base snapshot")

    # ==================================================================
    section("5. Void skill tree: nodes, locks and upgrades")
    check(len(NODES) == 12 and len(BRANCHES) == 3
          and all(len(nodes_for_branch(code)) == 4
                  for code, _, _ in BRANCHES),
          "the tree has three balanced branches of four nodes each")
    check(len({node.node_id for node in NODES}) == 12
          and all(font_ok(node.name) and font_ok(node.effect)
                  for node in NODES),
          "node IDs are unique and all tree text is font-safe")
    locked = fresh_game()
    check(locked.tree.state("a1") == LOCKED
          and not locked.tree.purchase("a1")[0],
          "level 1 cannot unlock a level-2 node")
    check("LEVEL" in locked.tree.reason("a1")
          and "LEVEL" in locked.tree.can_purchase("a1")[1],
          "locked cards explain their level requirement")
    game = fresh_game()
    game.exp.award_exp(10 ** 7)
    check(game.exp.level == MAX_LEVEL and game.tree.points == 14,
          "a maxed profile has enough points for the whole tree")
    check(game.tree.state("a1") == AVAILABLE
          and game.tree.state("a3") == LOCKED,
          "availability respects level and prerequisite gates")
    check(not game.tree.purchase("a3")[0]
          and "PREREQUISITE" in game.tree.can_purchase("a3")[1],
          "prerequisites cannot be skipped with spare points")
    ok, message = game.tree.purchase("a1")
    check(ok and game.tree.state("a1") == OWNED
          and game.exp.skill_points == 13 and "UNLOCKED" in message,
          "buying a node spends exactly one point and marks it owned")
    check(not game.tree.purchase("a1")[0],
          "the same node cannot be bought twice")
    for node_id in ("a2", "a3", "a4", "b1", "b2", "b3", "b4",
                    "c1", "c2", "c3", "c4"):
        ok, _ = game.tree.purchase(node_id)
        check(ok, f"node {node_id} unlocks with its prerequisites met")
    check(all(game.tree.state(node.node_id) == OWNED for node in NODES)
          and game.tree.points == 2,
          "all twelve nodes can be purchased with 14 granted points")
    mods = game.tree.modifiers()
    check(math.isclose(mods.burst_damage, 1.30)
          and math.isclose(mods.slash_damage, 1.30)
          and math.isclose(mods.crit_damage, 1.25)
          and math.isclose(mods.elite_damage, 1.25),
          "Void Offense nodes raise burst, slash, crit and elite damage")
    check(math.isclose(mods.shadow_cooldown, 0.75)
          and math.isclose(mods.shadow_distance, 1.30)
          and math.isclose(mods.dodge_recovery, 0.80)
          and math.isclose(mods.dodge_surge, 0.20),
          "Shadow Mobility nodes affect cooldown, travel and dodge recovery")
    check(math.isclose(mods.eclipse_damage, 1.30)
          and math.isclose(mods.eclipse_radius, 1.25)
          and math.isclose(mods.void_regen, 1.50)
          and math.isclose(mods.skill_cost, 0.80),
          "Eclipse Mastery nodes affect damage, radius, regen and cost")
    check(math.isclose(game.combat.elite_damage_mult, 1.25)
          and math.isclose(game.combat.crit_multiplier,
                           game.stats.crit_damage * 1.25),
          "offense modifiers reach the live combat authority")
    check(math.isclose(game.skills.shadow.effective_cooldown(game.skills),
                       game.skills.shadow.cooldown * 0.75)
          and math.isclose(game.skills.energy.regen,
                           VOID_REGEN_PER_SEC * 1.5),
          "mobility and regen modifiers reach live skill systems")
    check(math.isclose(game.player.combat.shadow_speed_mult, 1.30)
          and math.isclose(game.player.combat.dodge_duration_mult, 0.80)
          and math.isclose(game.player.combat.speed_surge_mult, 0.20),
          "movement modifiers reach the player controller")
    check(math.isclose(burst_damage(game.skills), BURST_DAMAGE * 1.30)
          and math.isclose(slash_damage(game.skills), SLASH_DAMAGE * 1.30)
          and math.isclose(eclipse_damage(game.skills), ECLIPSE_DAMAGE * 1.30)
          and math.isclose(eclipse_radius(game.skills), ECLIPSE_RADIUS * 1.25),
          "damage and radius helpers use the purchased modifiers")
    other = compute_modifiers({"int": 5}, {"c1"})
    check(math.isclose(other.void_power, 1.10)
          and math.isclose(other.eclipse_damage, 1.30),
          "attribute and node effects compose in one modifier snapshot")
    check(len(game.skills.skills) == 4
          and {skill.key for skill in game.skills.skills} == {"Q", "E", "R", "F"}
          and len({skill.name for skill in game.skills.skills}) == 4,
          "upgrades never add or duplicate an active Q/E/R/F ability")

    # ==================================================================
    section("6. Q/E/R/F still work with every upgrade applied")
    game = fresh_game()
    game.exp.award_exp(10 ** 7)
    for node_id in ("c1", "c3", "c4"):
        game.tree.purchase(node_id)
    game.tree.apply(skills=game.skills, combat=game.combat, player=game.player)
    check(game.skill_keys == {"Q": pygame.K_q, "E": pygame.K_e,
                              "R": pygame.K_r, "F": pygame.K_f},
          "the four skill bindings remain Q/E/R/F")
    game.skills.energy.reset()
    game.handle_event(key_event(pygame.K_q))
    check(math.isclose(game.skills.energy.current,
                       VOID_ENERGY_MAX - BURST_COST * 0.8)
          and game.skills.burst.timer > 0.0,
          "Q still casts Burst and honours the reduced energy cost")
    game.restart()
    game.handle_event(key_event(pygame.K_e))
    check(math.isclose(game.skills.energy.current,
                       VOID_ENERGY_MAX - SHADOW_COST * 0.8)
          and game.player.combat.shadow_step,
          "E still casts Shadow Step through the new modifiers")
    game.restart()
    game.handle_event(key_event(pygame.K_r))
    check(math.isclose(game.skills.energy.current,
                       VOID_ENERGY_MAX - SLASH_COST * 0.8)
          and len(game.skills.slash.waves) == 1,
          "R still casts one Void Slash wave")
    game.restart()
    game.handle_event(key_event(pygame.K_f))
    check(math.isclose(game.skills.energy.current,
                       VOID_ENERGY_MAX - ECLIPSE_COST * 0.8)
          and game.skills.eclipse.charging,
          "F still begins the Eclipse wind-up once")
    check(game.player.combat.speed_surge_mult == 0.0,
          "level-up surge timing is independent of the dodge-surge node")

    # ==================================================================
    section("7. Character and skill tree screens")
    game = fresh_game()
    game.exp.award_exp(300)
    check(CHAR_CLOSE.center[0] > 0 and RESET_RECT.right <= 1200,
          "character screen controls stay inside the fixed canvas")
    char_rects = (PLUS_RECTS[0], PLUS_RECTS[-1], RESET_RECT, CHAR_CLOSE)
    check(all(0 <= rect.x and rect.right <= 1280
              and 0 <= rect.y and rect.bottom <= 720 for rect in char_rects),
          "all clickable character controls are on-screen")
    char = CharacterScreen(game.player, game.exp, game.stats,
                           game.equipment, notify=game.notify)
    game.character_screen = char
    char.open()
    surface = pygame.Surface((1280, 720), pygame.SRCALPHA)
    char.draw(surface)
    char.update(0.5)
    check(math.isclose(char.reveal, 1.0),
          "the character overlay finishes its short reveal animation")
    game.handle_event(key_event(pygame.K_p))
    check(game.state == CHARACTER, "P opens the character screen")
    attack_before = game.stats.attack
    game.handle_event(click_event(PLUS_RECTS[0].center))
    check(game.exp.attributes["str"] == 1
          and math.isclose(game.stats.attack, attack_before + 2.0),
          "clicking STR allocates a point and refreshes live stats at once")
    game.handle_event(key_event(pygame.K_p))
    check(game.state == PLAY, "P closes the character screen again")
    game.handle_event(key_event(pygame.K_t))
    check(game.state == SKILL_TREE, "T opens the skill tree")
    tree_screen = SkillTreeScreen(game.player, game.tree, notify=game.notify)
    game.tree_screen = tree_screen
    tree_screen.draw(surface)
    tree_screen.update(0.5)
    check(len(CARD_RECTS) == 12
          and all(rect.right <= 1200 and rect.bottom <= 628
                  for rect in CARD_RECTS.values()),
          "all twelve node cards fit their three columns")
    nodes_before = len(game.exp.purchased_nodes)
    game.handle_event(click_event(CARD_RECTS["a1"].center))
    check(len(game.exp.purchased_nodes) == nodes_before + 1
          and game.tree.has("a1"),
          "clicking an available node buys it through the manager")
    game.handle_event(key_event(pygame.K_ESCAPE))
    check(game.state == PLAY, "ESC closes the skill tree")
    game.handle_event(key_event(pygame.K_i))
    check(game.state == INVENTORY,
          "the existing inventory overlay still opens")
    game.handle_event(key_event(pygame.K_ESCAPE))
    check(game.state == PLAY, "ESC closes the inventory as before")
    check(all(font_ok(label) for _, label in
              (("level", "CHARACTER LEVEL"), ("points", "SKILL POINTS"))),
          "screen labels use only glyphs shipped in the pixel font")

    # ==================================================================
    section("8. Level-up feedback")
    game = fresh_game()
    game.combat.hit_stop = 0.0
    game.effects.clear()
    events = game.exp.award_exp(300)
    check(len(events) >= 3, "one large reward produced several level-ups")
    messages = [toast.text for toast in game.notifications.items]
    check(any("LEVEL UP" in text for text in messages)
          and any("SKILL POINT" in text for text in messages),
          "polished level and skill-point toasts are shown")
    check(game.combat.hit_stop > 0.0,
          "a brief hit stop pauses the action on level-up")
    check(len(game.effects.novas) > 0 and len(game.effects.particles) > 0,
          "a gold/violet burst effect is spawned")
    check(game.player.combat.speed_surge_timer > 0.0,
          "a short movement surge rewards the level-up")
    game._level_up_sound()
    check(not (ROOT / "assets" / "audio").is_dir(),
          "no audio is invented; the guarded sound cue is a no-op here")

    # ==================================================================
    section("9. HUD compactness with the EXP strip")
    check((HP_X, HP_Y, HP_W, HP_H) == (20, 20, 204, 13)
          and (VOID_X, VOID_Y, VOID_W, VOID_H) == (20, 44, 172, 9)
          and (DASH_X, DASH_Y, DASH_W, DASH_H) == (20, 57, 120, 3),
          "existing HP, VOID and DASH geometry is unchanged")
    check((EXP_X, EXP_Y, EXP_W, EXP_H) == (20, 63, 172, 3)
          and EXP_Y + EXP_H <= 70,
          "the new EXP bar stays a slim three pixels tall")
    check(font_ok(f"EXP {game.exp.exp}/{game.exp.exp_required}")
          and font_ok("EXP MAX"),
          "EXP labels render with the shipped bitmap font")
    game.hud.draw(surface, game.player, game.combat, game.camera,
                  game.skills, stage=game.level, boss=game.level.boss,
                  exp=game.exp)
    check(True, "the HUD draws with the live progression snapshot")
    game.hud.draw(surface, game.player, game.combat, game.camera,
                  game.skills, stage=game.level, boss=game.level.boss)
    check(True, "the HUD still draws without the optional EXP argument")

    # ==================================================================
    section("10. Additive save schema and validation")
    fresh = default_data()
    check(fresh["version"] == SAVE_VERSION
          and fresh["player"]["level"] == START_LEVEL
          and fresh["player"]["exp"] == 0
          and fresh["player"]["attributes"] == {
              "str": 0, "vit": 0, "agi": 0, "int": 0}
          and fresh["player"]["skill_nodes"] == []
          and fresh["defeated_enemies"] == [],
          "the default save carries every additive Phase 7 field")
    raw = {
        "version": SAVE_VERSION,
        "player": {
            "level": 7, "exp": -5, "total_exp": -9,
            "attributes": {"str": -3, "vit": 99, "agi": "junk", "int": 5},
            "attribute_points": -5, "skill_points": -2,
            "skill_nodes": ["a1", "not_a_node", "a1"],
        },
        "defeated_enemies": ["01:1", "01:1", 5, None, ""],
        "inventory": {"gold": 321},
    }
    clean = canonical_data(raw)
    player = clean["player"]
    check(player["level"] == 7 and player["exp"] == 0
          and player["total_exp"] == 0,
          "invalid EXP fields clamp to zero")
    check(player["attributes"] == {"str": 0, "vit": 10, "agi": 0, "int": 5},
          "attribute ranks clamp to 0..10 and junk text is discarded")
    check(player["attribute_points"] == 0 and player["skill_points"] == 0,
          "negative point counters are rejected")
    check(player["skill_nodes"] == ["a1"],
          "unknown and duplicate skill node IDs are dropped")
    check(clean["defeated_enemies"] == ["01:1"],
          "defeated markers are deduplicated and type-checked")
    check(clean["inventory"]["gold"] == 321,
          "Phase 6 inventory data survives progression canonicalisation")
    legacy = canonical_data({
        "player": {"level": 7, "attributes": {"str": 2}},
    })
    check(legacy["player"]["attribute_points"] == 16
          and legacy["player"]["skill_points"] == 3,
          "old level-7 profiles receive their earned point grants")
    check(canonical_data({"player": {"level": 999}})["player"]["level"] == 99,
          "the historical numeric clamp remains compatible with old tests")
    game = fresh_game()
    game.exp.award_exp(300)
    game.exp.allocate_attribute("str")
    game.tree.purchase("a1")
    game.inventory.add("rusted_blade", 1)
    game.equipment.equip("rusted_blade")
    game.progression.complete_level("01")
    game.progression.save_inventory(game.inventory, game.equipment)
    game._save_progression()
    path = Path(os.environ["ASHEN_VEIL_SAVE"])
    saved = json.loads(path.read_text(encoding="utf-8"))
    check(saved["player"]["level"] == game.exp.level
          and saved["player"]["attributes"]["str"] == 1
          and saved["player"]["skill_nodes"] == ["a1"],
          "the save contains level, attributes and purchased nodes")
    check(saved["inventory"]["equipped"]["weapon"] == "rusted_blade"
          and saved["levels"]["01"]["completed"] is True,
          "inventory and level completion share the save without loss")
    again = Game()
    check(again.exp.level == game.exp.level
          and again.exp.attributes == game.exp.attributes
          and again.exp.purchased_nodes == game.exp.purchased_nodes,
          "a new Game restores the full progression snapshot")
    check(again.equipment.equipped["weapon"] == "rusted_blade"
          and again.progression.boss_defeated("01")
          and math.isclose(again.stats.attack, game.stats.attack),
          "equipment, boss completion and derived stats survive reload")
    check(again.tree.modifiers().burst_damage > 1.0
          and again.skills.mods.burst_damage > 1.0,
          "purchased node effects are live again after reload")

    # ==================================================================
    section("11. Source tree and web archive")
    expected_sources = (
        "scripts/progression_config.py", "scripts/skill_tree_config.py",
        "scripts/skill_modifiers.py", "scripts/exp_manager.py",
        "scripts/skill_tree_manager.py", "scripts/ui/character_screen.py",
        "scripts/ui/skill_tree_screen.py",
        "scripts/ui/skill_tree_manager_view.py",
    )
    check(all((ROOT / name).is_file() for name in expected_sources),
          "every Phase 7 source module is present")
    main_source = (ROOT / "main.py").read_text(encoding="utf-8")
    check("pygame.K_p" in main_source and "pygame.K_t" in main_source
          and "award_enemy_kill" in main_source
          and "exp=self.exp" in main_source,
          "main.py wires P/T, kill EXP and the HUD snapshot")
    archive = ROOT / "build" / "web" / "game.tar.gz"
    if archive.is_file():
        with tarfile.open(archive, "r:gz") as bundle:
            names = bundle.getnames()
        check(any(name.endswith("main.py") for name in names),
              "the web archive contains main.py")
        check(all(any(name.endswith(source) for name in names)
                  for source in expected_sources),
              "the web archive ships all Phase 7 progression modules")
        check(any("data/items/loot_tables.json" in name for name in names),
              "Phase 6 item data is still shipped")
        check(not any(name.startswith("./tools") for name in names),
              "development tools remain excluded from the web build")
    else:
        check(False, "the Pygbag archive exists (run the web build first)")

    if FAILED:
        print(f"\nFAILED {len(FAILED)} CHECK(S):")
        for message in FAILED:
            print(f"  - {message}")
        raise SystemExit(1)
    print(f"\nALL PHASE 7 CHECKS PASSED ({PASSED} assertions).")


if __name__ == "__main__":
    main()
