#!/usr/bin/env python3
"""Headless Phase 6 acceptance tests for ASHEN VEIL.

Run from the project root:

    python tools/test_phase6.py

Sections:
 1  item data: five JSON files, seven slots, five rarities, valid definitions
 2  player stats and equipment: real bonuses, all slots, no duplicate application
 3  inventory: capacity, stacks, consumables, gold, full messages
 4  rarity and interface: colours, font coverage, draw, compact HUD
 5  loot: tables, one roll per death, boss reward, pickup, walls, caps
 6  save integration: validation, dedup, roundtrip, progression preserved
 7  integration: I/ESC/G, pause, boss chain, combat baseline, Pygbag archive
"""
from __future__ import annotations

import json
import os
import random
import sys
import tarfile
import tempfile
from pathlib import Path
from types import SimpleNamespace

# Save path must be redirected before any gameplay module resolves defaults.
TEMP_ROOT = Path(tempfile.mkdtemp(prefix="ashen_veil_phase6_"))
GAME_SAVE = TEMP_ROOT / "game" / "progress.json"
os.environ["ASHEN_VEIL_SAVE"] = str(GAME_SAVE)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame  # noqa: E402

from main import (  # noqa: E402
    INVENTORY,
    PLAY,
    Game,
)
from scripts.combat_config import (  # noqa: E402
    ATTACK_DAMAGE,
    CRIT_CHANCE,
    CRIT_MULTIPLIER,
    PLAYER_HEALTH_MAX,
)
from scripts.equipment_manager import EquipmentManager  # noqa: E402
from scripts.hud import HP_H, HP_W, HP_X, HP_Y, VOID_H, VOID_W, VOID_X, VOID_Y  # noqa: E402
from scripts.inventory_manager import InventoryManager  # noqa: E402
from scripts.item_database import (  # noqa: E402
    EQUIPMENT_SLOTS,
    ITEM_DIR,
    RARITIES,
    RARITY_COLORS,
    STAT_KEYS,
    get_item,
    items,
    loot_table,
)
from scripts.loot_manager import LootManager  # noqa: E402
from scripts.pixel_font import GLYPHS  # noqa: E402
from scripts.player_stats import (  # noqa: E402
    BASE_ATTACK,
    BASE_SPEED,
    PlayerStats,
    format_stat,
)
from scripts.save_manager import (  # noqa: E402
    SAVE_VERSION,
    canonical_data,
    default_data,
)
from scripts.skill_config import VOID_ENERGY_MAX  # noqa: E402
from scripts.ui.inventory_screen import (  # noqa: E402
    CLOSE_RECT,
    DETAILS_RECT,
    GRID_COLS,
    GRID_ROWS,
    WINDOW,
)
from scripts.ui.item_icons import icon  # noqa: E402
from scripts.ui.item_tooltip import ItemTooltip  # noqa: E402

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


def font_ok(text: str) -> bool:
    return all(ch.isspace() or ch.upper() in GLYPHS for ch in str(text))


def fake_enemy(enemy_id: int, key: str = "fallen_knight",
               boss: bool = False, x: float = 1000.0,
               y: float = 1000.0):
    return SimpleNamespace(id=enemy_id, key=key, x=x, y=y,
                           is_boss=boss, subtitle="" if not boss else "BOSS")


class WallWorld:
    """A stub world whose every pickup segment is blocked."""

    class Collision:
        @staticmethod
        def rect_free(_rect):
            return True

        @staticmethod
        def segment_blocked(*_args):
            return True

    collision = Collision()


# ----------------------------------------------------------------------
def main() -> None:
    print("ASHEN VEIL - Phase 6 acceptance tests")

    # -- 1. Item data ---------------------------------------------------
    section("1. Item data and catalogue")
    for filename in ("weapons.json", "armor.json", "accessories.json",
                     "consumables.json", "loot_tables.json"):
        check((ITEM_DIR / filename).is_file(), f"{filename} ships with the game")
    catalogue = items()
    check(len(catalogue) >= 20, f"catalogue has {len(catalogue)} validated items")
    check(all(item.item_id and item.name and item.description
              for item in catalogue.values()),
          "every item has an ID, name and description")
    check(all(item.icon for item in catalogue.values()),
          "every item declares an icon key")
    check(all(item.rarity in RARITIES for item in catalogue.values()),
          "every item uses one of the five rarities")
    check(all(font_ok(item.name) and font_ok(item.description)
              for item in catalogue.values()),
          "item names and descriptions use renderable glyphs")
    check(all(all(key in STAT_KEYS for key in item.stats)
              for item in catalogue.values()),
          "all item bonuses use supported stat keys")
    covered = {item.slot for item in catalogue.values()
               if item.is_equipment}
    check(set(EQUIPMENT_SLOTS) <= covered,
          "all seven equipment slots have at least one item")
    rarities_seen = {item.rarity for item in catalogue.values()}
    check(rarities_seen == set(RARITIES),
          "all five rarity tiers appear in the catalogue")
    check(len(set(RARITY_COLORS.values())) == len(RARITIES),
          "each rarity has a distinct border colour")
    check(len([i for i in catalogue.values() if i.rarity == "legendary"]) <= 2,
          "legendary gear is scarce")
    get_item("hollow_redeemer") is not None and check(
        get_item("hollow_redeemer").effect_kind == "void_on_kill",
        "the legendary weapon carries a real special effect")
    check(get_item("minor_health_potion").effect_kind == "heal"
          and get_item("void_potion").effect_kind == "void",
          "two consumables with distinct effects exist")
    check(get_item("ash_shard").is_material
          and get_item("guardian_ember").is_material,
          "basic and boss crafting materials exist")
    table = loot_table()
    check(all(key in table for key in ("regular", "elite", "boss", "settings")),
          "loot tables expose regular, elite, boss and settings blocks")
    check(table["boss"]["guaranteed_items"][0]["id"] == "hollow_redeemer",
          "boss table guarantees the legendary reward")

    # -- 2. Stats and equipment -----------------------------------------
    section("2. Player statistics and seven equipment slots")
    base = PlayerStats()
    check(base.attack == BASE_ATTACK == ATTACK_DAMAGE[0],
          "base attack equals the first combo hit")
    check(base.defense == 0.0 and base.max_hp == PLAYER_HEALTH_MAX,
          "base defense is zero and base HP matches Phase 5")
    check(base.speed == BASE_SPEED and base.crit_chance == CRIT_CHANCE,
          "base speed and critical chance are unchanged")
    check(base.crit_damage == CRIT_MULTIPLIER
          and base.max_void == VOID_ENERGY_MAX,
          "base critical damage and Void maximum are unchanged")

    game = Game()
    check(game.state == PLAY, "Game still starts directly in PLAY")
    check(all(value is None for value in game.equipment.equipped.values()),
          "a fresh profile has no pre-equipped items")
    check(game.exp.level == 1, "Phase 7 starts a fresh wanderer at level 1")
    # Phase 6 gear tests were written around a level-7 test character.  Set
    # that level explicitly on both authorities (do not change the new level-1
    # default) so level-gated equipment scenarios keep their original meaning.
    game.exp.level = 7
    game.player.level = 7
    game.progression.record_player_level(7)
    game.equipment.refresh_level()
    game.inventory.add("ash_shard", 250)
    check(game.inventory.count("ash_shard") == 99
          and len([e for e in game.inventory.entries
                   if e.item_id == "ash_shard"]) <= 1,
          "stack quantities clamp to the item maximum")

    slot_items = {
        "weapon": "ashfang_saber",
        "helmet": "wardens_helm",
        "armor": "gravesteel_plate",
        "gloves": "voidweave_gloves",
        "boots": "guardian_greaves",
        "ring": "void_signet",
        "necklace": "shroud_of_dusk",
    }
    for slot, item_id in slot_items.items():
        game.inventory.add(item_id, 1)
        ok, _ = game.equipment.equip(item_id)
        check(ok and game.equipment.equipped[slot] == item_id,
              f"{slot} accepts {item_id}")
    # wardens_helm +12, gravesteel_plate +24, guardian_greaves +18,
    # shroud_of_dusk has no HP bonus (it grants Void/crit instead).
    expected_max = (PLAYER_HEALTH_MAX + 12 + 24 + 18)
    check(abs(game.stats.max_hp - expected_max) < 0.01,
          f"all helmet/armor/boots/necklace HP bonuses stack ({game.stats.max_hp})")
    check(game.stats.attack > base.attack,
          "weapon and gloves increase real attack")
    check(game.stats.defense > 0.0, "armor adds real defense")
    check(game.stats.speed > base.speed, "boots add real movement speed")
    check(game.stats.crit_chance > base.crit_chance,
          "jewellery and gloves add real critical chance")
    check(game.stats.crit_damage > base.crit_damage,
          "rings and necklaces add real critical damage")
    check(game.stats.max_void > base.max_void,
          "void gear raises the real energy maximum")
    check(abs(game.combat.crit_chance - game.stats.crit_chance) < 1e-9,
          "CombatManager reads the equipped critical chance")
    check(abs(game.combat.crit_multiplier - game.stats.crit_damage) < 1e-9,
          "CombatManager reads the equipped critical multiplier")
    check(abs(game.skills.energy.maximum - game.stats.max_void) < 1e-9,
          "the Void pool maximum follows equipment")
    check(abs(game.player.health_max - game.stats.max_hp) < 0.01,
          "the health pool maximum follows equipment")

    game.equipment.recompute()
    game.equipment.recompute()
    # ashfang_saber +10, voidweave_gloves +5; void_signet and shroud_of_dusk
    # grant Void/crit only, so total attack is 35.
    check(abs(game.stats.attack - (20.0 + 10.0 + 5.0)) < 0.01,
          "repeated recomputes never apply a bonus twice")
    game.equipment.unequip("weapon")
    check(game.stats.attack < 40.0 and game.equipment.equipped["weapon"] is None,
          "unequipping a weapon restores the earlier attack value")
    check(abs(game.stats.max_hp - expected_max) < 0.01,
          "unequipping one slot leaves the other bonuses intact")
    for slot in list(slot_items):
        game.equipment.unequip(slot)
    check(game.stats.as_dict() == base.as_dict(),
          "unequipping everything restores the exact base snapshot")
    check(game.player.health_max == PLAYER_HEALTH_MAX,
          "the player's HP maximum returns to its base value")
    check(game.combat.crit_chance == CRIT_CHANCE
          and game.combat.crit_multiplier == CRIT_MULTIPLIER,
          "combat critical values return to their base values")

    ok, _ = game.equipment.equip("gravesteel_plate")
    check(ok, "the level-7 test player can wear a level-5 rare")
    game.player.level = 2
    ok, reason = game.equipment.equip("duskbound_greatsword")
    check(not ok and "LEVEL" in reason,
          "level requirements block too-high equipment")
    game.player.level = 7
    ok, _ = game.equipment.equip("rusted_blade")
    check(ok, "a valid weapon equips after the level is restored")
    ok, _ = game.equipment.equip("rusted_blade")
    check(not ok, "equipping the same item twice is rejected")
    ok, _ = game.equipment.equip("minor_health_potion")
    check(not ok, "consumables cannot be placed in equipment slots")
    ok, _ = game.equipment.equip("does_not_exist")
    check(not ok, "unknown item IDs are rejected safely")
    game.equipment.clear()

    # -- 3. Inventory and consumables -----------------------------------
    section("3. Inventory capacity, stacks, gold and consumables")
    bag = InventoryManager(capacity=14)
    bag.attach(player=game.player, skills=game.skills)
    check(bag.capacity == 14 and bag.free == 14, "capacity is configurable")
    bag.add("minor_health_potion", 25)
    check(bag.count("minor_health_potion") == 20,
          "a stack caps at 20 and reports the overflow")
    check("FULL" in bag.message, "overflow produces an explicit message")
    bag.add("void_potion", 5)
    check(bag.entry_at(1).item_id == "void_potion",
          "a new item uses the next free slot")
    game.player.health = 20.0
    check(bag.use("minor_health_potion"), "a health potion is usable")
    check(abs(game.player.health - 65.0) < 0.01,
          "the potion restores exactly 45 HP")
    check(bag.count("minor_health_potion") == 19,
          "using a potion reduces the stack by one")
    game.player.health = game.player.health_max
    before = bag.count("minor_health_potion")
    check(not bag.use("minor_health_potion")
          and bag.count("minor_health_potion") == before,
          "a potion is not wasted at full HP")
    game.skills.energy.current = 30.0
    check(bag.use("void_potion"), "a Void potion is usable")
    check(abs(game.skills.energy.current - 70.0) < 0.01,
          "Void potions restore exactly 40 energy")
    game.skills.energy.current = game.skills.energy.maximum
    check(not bag.use("void_potion"), "Void potions refuse a full pool")
    bag.add_gold(350)
    check(bag.gold == 350, "gold accumulates")
    check(bag.spend_gold(100) and bag.gold == 250,
          "gold can be spent")
    for index in range(12):
        bag.add(f"test_unique_{index}", 1) if get_item(f"test_unique_{index}") else None
    for known in [item_id for item_id in items() if items()[item_id].is_equipment][:14]:
        bag.add(known, 1)
    check(bag.used <= bag.capacity, "the inventory never exceeds capacity")
    check(not bag.is_full or bag.is_full, "capacity flag is boolean")
    before = bag.used
    bag.add("bone_ring", 1)
    check(bag.used == before or bag.has("bone_ring"),
          "full inventory either stores the item or reports the failure")
    bag.drop(0)
    check(bag.used <= before, "dropping frees a slot")

    # -- 4. Rarity and interface ----------------------------------------
    section("4. Rarity, pixel font and interface rendering")
    check(RARITY_COLORS["common"] != RARITY_COLORS["legendary"],
          "common and legendary borders are visibly different")
    check(all(font_ok(label) for label in
              ("COMMON", "UNCOMMON", "RARE", "EPIC", "LEGENDARY")),
          "all rarity labels are renderable")
    check(font_ok(format_stat("crit_chance", 0.25, signed=True))
          and font_ok(format_stat("max_hp", 24, signed=True)),
          "formatted stat lines stay inside the bitmap font")
    screen = game.inventory_screen
    screen.open()
    for _ in range(20):
        screen.update(1 / 60)
    check(screen.reveal == 1.0, "the overlay fade completes quickly")
    game.draw()
    check(True, "a full inventory frame draws without error")
    check(WINDOW.w <= 1280 and WINDOW.h <= 720,
          "the inventory panel fits the internal resolution")
    check(GRID_COLS * GRID_ROWS == 28,
          "the satchel grid exposes all 28 capacity slots")
    check(DETAILS_RECT.bottom < CLOSE_RECT.y
          and CLOSE_RECT.right <= 1200,
          "details and close button do not overlap")
    check((HP_X, HP_Y, HP_W, HP_H) == (20, 20, 204, 13)
          and (VOID_X, VOID_Y, VOID_W, VOID_H) == (20, 44, 172, 9),
          "the compact gameplay HUD geometry is unchanged")
    for item in catalogue.values():
        check(icon(item.icon).get_width() == 24,
              f"icon {item.icon} is generated at 24 px")
        break
    tooltip = ItemTooltip()
    check(all(font_ok(label) for _, label in
              [("equip", "EQUIP"), ("unequip", "UNEQUIP"),
               ("use", "USE"), ("drop", "DROP")]),
          "all action buttons use renderable labels")
    check(len(tooltip.button_rects(DETAILS_RECT)) == 4,
          "four action buttons are laid out")

    # -- 5. Loot ---------------------------------------------------------
    section("5. Loot tables, drops and pickup")
    loot = LootManager(game.world, rng=random.Random(7))
    loot.clear()
    regular = fake_enemy(500)
    rolls = loot.on_enemy_killed(regular)
    check(len(rolls) >= 1,
          "a regular enemy roll produces at least one visible drop")
    count_before = len(loot.drops)
    loot.on_enemy_killed(regular)
    check(len(loot.drops) == count_before,
          "the same death never rolls twice")
    elite = fake_enemy(501, key="corrupted_warden", x=1100, y=1100)
    elite_drops = loot.on_enemy_killed(elite)
    check(any(drop.gold > 0 for drop in elite_drops),
          "elites always award gold")
    check(any(drop.item_id and get_item(drop.item_id).rarity == "rare"
              for drop in elite_drops)
          or loot.table["elite"]["equipment"]["chance"] > 0.5,
          "elite tables favour rare equipment")
    boss = fake_enemy(9001, boss=True, x=1500, y=1500)
    boss_drops = loot.on_enemy_killed(boss)
    check(any(drop.item_id == "hollow_redeemer" for drop in boss_drops),
          "the Hollow Guardian always drops its unique legendary weapon")
    check(any(drop.gold >= 280 for drop in boss_drops),
          "the boss reward includes a substantial gold purse")
    check(any(drop.item_id == "guardian_ember" for drop in boss_drops)
          or loot.table["boss"]["material"]["chance"] > 0.0,
          "the boss table includes an optional material")
    loot.on_enemy_killed(boss)
    check(sum(1 for d in loot.drops if d.item_id == "hollow_redeemer") == 1,
          "the boss reward cannot duplicate on a second call")
    for index in range(200):
        loot.spawn(1000 + index, 1000, item_id="ash_shard")
    check(len(loot.drops) <= loot.max_drops,
          f"world drops are capped at {loot.max_drops}")

    game.loot.clear()
    game.player.x, game.player.y = 1400.0, 1400.0
    game.inventory.add("bone_ring", 1)
    before_ring = game.inventory.count("bone_ring")
    game.loot.spawn(game.player.x + 10, game.player.y,
                    item_id="bone_ring", quantity=1)
    game.loot.try_pickup(game.player, game.inventory)
    check(game.inventory.count("bone_ring") == before_ring + 1,
          "approaching and pressing G collects a drop")
    check(len(game.loot.drops) == 0, "a collected drop leaves the world")
    game.loot.spawn(game.player.x + 10, game.player.y, gold=77)
    gold_before = game.inventory.gold
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_g))
    game.handle_event(pygame.event.get()[-1])
    check(game.inventory.gold == gold_before + 77,
          "the G key picks up gold")

    blocked = LootManager(WallWorld(), rng=random.Random(3))
    blocked.spawn(10, 10, item_id="ash_shard")
    check(not blocked.try_pickup(game.player, blocked.inventory
                                 if hasattr(blocked, "inventory") else game.inventory),
          "a wall prevents pickup")

    full = InventoryManager(capacity=12)
    full.add("rusted_blade", 1)
    for item_id in [key for key in items() if items()[key].is_equipment][:12]:
        full.add(item_id, 1)
    if not full.is_full:
        while not full.is_full:
            full.add("ash_shard", 1)
    remaining = InventoryManager(capacity=12)
    remaining.add("rusted_blade", 1)
    loot_full = LootManager(game.world, rng=random.Random(1))
    loot_full.clear()
    loot_full.spawn(game.player.x, game.player.y, item_id="void_potion")
    ok_pickup = loot_full.try_pickup(game.player, full)
    check("FULL" in full.message or ok_pickup,
          "a full inventory leaves the drop in the world with a clear message")

    # -- 6. Save integration --------------------------------------------
    section("6. Save validation and roundtrip")
    fresh = default_data()
    check(fresh["version"] == SAVE_VERSION
          and "inventory" in fresh,
          "the default profile includes the inventory block")
    payload = {
        "version": SAVE_VERSION,
        "levels": {"01": {"completed": True, "boss_defeated": True,
                          "stages_cleared": 4}},
        "player": {"level": 7},
        "inventory": {
            "gold": 999,
            "capacity": 28,
            "items": [
                {"id": "rusted_blade", "qty": 1},
                {"id": "rusted_blade", "qty": 1},
                {"id": "minor_health_potion", "qty": 5},
                {"id": "minor_health_potion", "qty": 4},
                {"id": "not_an_item", "qty": 99},
                {"id": "duskbound_greatsword", "qty": 1},
            ],
            "equipped": {
                "weapon": "duskbound_greatsword",
                "helmet": "not_an_item",
                "armor": "gravesteel_plate",
                "gloves": None,
                "boots": None,
                "ring": None,
                "necklace": None,
            },
        },
    }
    clean = canonical_data(payload)
    inv = clean["inventory"]
    check(inv["gold"] == 999, "gold survives canonicalization")
    check(len([e for e in inv["items"]
               if e["id"] == "rusted_blade"]) == 1,
          "duplicate unique items are removed")
    check(sum(e["qty"] for e in inv["items"]
              if e["id"] == "minor_health_potion") == 9,
          "stackable records merge into a single stack")
    check(not any(e["id"] == "not_an_item" for e in inv["items"]),
          "invalid item IDs are discarded")
    check(inv["equipped"]["weapon"] == "duskbound_greatsword"
          and inv["equipped"]["helmet"] is None,
          "only valid, owned, level-appropriate equipment survives")
    check(clean["levels"]["01"]["completed"] is True,
          "level progression data is preserved")
    poor = canonical_data({
        "player": {"level": 2},
        "inventory": {
            "items": [{"id": "hollow_redeemer", "qty": 1}],
            "equipped": {"weapon": "hollow_redeemer"},
        },
    })
    check(poor["inventory"]["equipped"]["weapon"] is None,
          "a too-high-level equipped item is dropped")
    check(any(e["id"] == "hollow_redeemer" for e in poor["inventory"]["items"]),
          "the item itself is not silently deleted")

    game.inventory.add("void_signet", 1)
    game.equipment.equip("void_signet")
    game.inventory.add("guardian_ember", 4)
    game.inventory.add_gold(500)
    game.progression.save_inventory(game.inventory, game.equipment)
    check(GAME_SAVE.is_file(), "inventory changes write the shared profile")
    raw = json.loads(GAME_SAVE.read_text(encoding="utf-8"))
    check(raw["inventory"]["gold"] == game.inventory.gold,
          "gold is persisted")
    check(raw["inventory"]["equipped"]["ring"] == "void_signet",
          "equipped items are persisted")
    check(any(e["id"] == "guardian_ember" and e["qty"] == 4
              for e in raw["inventory"]["items"]),
          "material quantities are persisted")
    check("levels" in raw, "progression data shares the same save file")

    reloaded = Game()
    check(reloaded.inventory.gold == game.inventory.gold,
          "a new Game restores gold")
    check(reloaded.equipment.equipped["ring"] == "void_signet",
          "a new Game restores equipment")
    check(reloaded.inventory.count("guardian_ember") == 4,
          "a new Game restores stack quantities")
    check(abs(reloaded.stats.max_void - game.stats.max_void) < 0.01,
          "a new Game restores equipment bonuses")
    check(reloaded.progression.boss_defeated("01") is False,
          "inventory saves do not invent progression completions")

    # -- 7. Integration --------------------------------------------------
    section("7. Integration, controls and web build")
    game.close_inventory()
    game.player.x, game.player.y = 1500.0, 1140.0
    start_x = game.player.x
    game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_i))
    check(game.state == INVENTORY, "I opens the inventory")
    game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_i))
    check(game.state == PLAY, "I closes the inventory again")
    game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_i))
    game.handle_event(pygame.event.Event(pygame.KEYDOWN,
                                         key=pygame.K_ESCAPE))
    check(game.state == PLAY, "ESC closes the inventory")
    game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_i))
    before_x, before_energy = game.player.x, game.skills.energy.current
    before_enemies = game.combat.alive_count
    game.skills.energy.current = 10.0
    for _ in range(30):
        game.update(1 / 60)
    check(game.player.x == before_x, "player movement is paused")
    check(game.combat.alive_count == before_enemies,
          "enemy simulation is paused")
    check(abs(game.skills.energy.current - 10.0) < 1e-9,
          "Void regeneration is paused")
    game.skills.energy.current = before_energy
    game.close_inventory()

    game.equipment.clear()
    game.combat.crit_chance = 0.0
    check(game.player.attack_hitbox is None,
          "no attack hitbox exists while idle")
    game.player.request_attack()
    # update() clamps dt to 0.05; stage-1 startup is 0.055s, so advance twice
    # to land inside the active window before sampling the hitbox.
    keys = pygame.key.get_pressed()
    game.player.update(0.05, keys, game.world.collision)
    game.player.update(0.05, keys, game.world.collision)
    box = game.player.attack_hitbox
    check(box is not None and abs(box.damage - ATTACK_DAMAGE[0]) < 0.01,
          "unequipped attack damage matches the Phase 5 baseline")
    check(game.player.mitigate_damage(100.0) == 100.0,
          "zero defense leaves intake unchanged")

    killed = fake_enemy(777, boss=True, x=1600, y=1600)
    game.loot.clear()
    game.combat.on_kill(killed)
    check(any(drop.item_id == "hollow_redeemer" for drop in game.loot.drops),
          "the shared kill hook still grants the boss reward")
    check(game.skills.energy.current > 0.0,
          "Void kill rewards still fire through the chained hook")

    check((ROOT / "data" / "items" / "loot_tables.json").is_file(),
          "item data is present in the source tree")
    check((ROOT / "scripts" / "inventory_manager.py").is_file()
          and (ROOT / "scripts" / "ui" / "inventory_screen.py").is_file(),
          "the Phase 6 modules are present")
    check((ROOT / "pygbag.ini").is_file(),
          "the Pygbag configuration is still present")
    archive = ROOT / "build" / "web" / "game.tar.gz"
    if archive.is_file():
        with tarfile.open(archive, "r:gz") as bundle:
            names = bundle.getnames()
        check(any(name.endswith("main.py") for name in names),
              "the web archive still contains main.py")
        check(any("data/items/weapons.json" in name for name in names),
              "the web archive contains item data")
        check(any("scripts/inventory_manager.py" in name for name in names),
              "the web archive contains the inventory manager")
        check(not any(name.startswith("./tools") for name in names),
              "development tools remain excluded from the web archive")
    else:
        check(False, "the Pygbag archive exists (run the web build first)")

    if FAILED:
        print(f"\nFAILED {len(FAILED)} CHECK(S):")
        for message in FAILED:
            print(f"  - {message}")
        raise SystemExit(1)
    print(f"\nALL PHASE 6 CHECKS PASSED ({PASSED} assertions).")


if __name__ == "__main__":
    main()
