#!/usr/bin/env python3
"""Phase 8 verification: Ashen Village safe hub, NPCs, trade and forge.

Run after the web build so the archive checks are meaningful::

    python tools/test_phase8.py

The suite is headless and writes only to a temporary profile, so it never
touches a real desktop or browser save.
"""
from __future__ import annotations

import json
import os
import sys
import tarfile
import tempfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TMP_ROOT = Path(tempfile.mkdtemp(prefix="ashen_veil_phase8_"))
os.environ["ASHEN_VEIL_SAVE"] = str(TMP_ROOT / "progress.json")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame  # noqa: E402

from main import (  # noqa: E402
    BLACKSMITH, DIALOGUE, PLAY, SHOP, Game,
)
from scripts.blacksmith_manager import BlacksmithManager  # noqa: E402
from scripts.collision import CollisionWorld  # noqa: E402
from scripts.dialogue_manager import DialogueManager  # noqa: E402
from scripts.interaction_manager import InteractionManager  # noqa: E402
from scripts.item_database import get_item  # noqa: E402
from scripts.npc_manager import NPCManager  # noqa: E402
from scripts.pixel_font import GLYPHS  # noqa: E402
from scripts.safe_zone import contains as in_safe_zone  # noqa: E402
from scripts.safe_zone import push_out  # noqa: E402
from scripts.save_manager import (  # noqa: E402
    SAVE_VERSION, canonical_data, load_profile,
)
from scripts.shop_manager import ShopManager  # noqa: E402
from scripts.village_data import (  # noqa: E402
    DIALOGUE_IDS, MAX_UPGRADE_LEVEL, NPC_IDS,
)
from scripts.village_layout import (  # noqa: E402
    SAFE_ZONE_CENTER, SAFE_ZONE_RECT, SPAWN,
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


def fresh_game() -> Game:
    folder = Path(tempfile.mkdtemp(prefix="p8_", dir=str(TMP_ROOT)))
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
    section("1. Source tree and Phase 8 data files")
    expected_sources = (
        "scripts/village_data.py", "scripts/safe_zone.py",
        "scripts/npc_manager.py", "scripts/dialogue_manager.py",
        "scripts/shop_manager.py", "scripts/blacksmith_manager.py",
        "scripts/interaction_manager.py",
        "scripts/ui/dialogue_screen.py", "scripts/ui/merchant_screen.py",
        "scripts/ui/blacksmith_screen.py", "tools/generate_npc_sprites.py",
    )
    check(all((ROOT / name).is_file() for name in expected_sources),
          "every Phase 8 source module is present")
    for npc_id in NPC_IDS:
        check((ROOT / "data" / "npcs" / f"{npc_id}.json").is_file(),
              f"NPC data file for {npc_id} exists")
    for dialogue_id in DIALOGUE_IDS:
        check((ROOT / "data" / "dialogue" /
               f"{dialogue_id}_dialogue.json").is_file(),
              f"dialogue data file for {dialogue_id} exists")
    check((ROOT / "data" / "shops" / "merchant_stock.json").is_file(),
          "merchant stock data file exists")
    check((ROOT / "data" / "blacksmith" / "upgrades.json").is_file(),
          "blacksmith upgrade data file exists")
    manifest = json.loads(
        (ROOT / "assets" / "sliced" / "manifest.json").read_text("utf-8")
    )
    check("campfire" in json.dumps(manifest),
          "campfire prop is registered in the sliced manifest")
    main_source = (ROOT / "main.py").read_text("utf-8")
    check(all(token in main_source for token in (
        "DIALOGUE", "SHOP", "BLACKSMITH", "pygame.K_g",
        "_context_interact", "npcs=self.npcs.npcs", "save_village",
    )), "main.py wires hub states, G interaction, NPC drawing and village save")
    check("pygame.K_e" in main_source and "pygame.K_f" in main_source,
          "E Shadow Step and F Eclipse remain bound")

    # ==================================================================
    section("2. NPC sprites and hub art")
    game = fresh_game()
    sprites = {}
    for npc_id in NPC_IDS:
        path = ROOT / "assets" / "npcs" / f"{npc_id}.png"
        check(path.is_file(), f"{npc_id} sprite sheet exists")
        img = pygame.image.load(str(path)).convert_alpha()
        sprites[npc_id] = img
        check(img.get_size() == (256, 256),
              f"{npc_id} sprite is a 256x256 4x4 sheet")
    def pixels(npc_id):
        return (ROOT / "assets" / "npcs" / f"{npc_id}.png").read_bytes()

    check(pixels("merchant") != pixels("blacksmith")
          and pixels("blacksmith") != pixels("veil_keeper"),
          "the three NPCs use distinct recoloured sprites, not one shared frame")
    cache_a = game.assets.npc_sheet("npcs/merchant.png")
    cache_b = game.assets.npc_sheet("npcs/merchant.png")
    check(cache_a is cache_b, "Assets.npc_sheet caches loaded sheets")
    check((ROOT / "assets" / "sliced" / "props" / "campfire.png").is_file(),
          "campfire art asset exists")

    # ==================================================================
    section("3. Safe-zone geometry and hostile exclusion")
    check(SAFE_ZONE_RECT == (1320.0, 890.0, 1740.0, 1230.0),
          "safe zone occupies the authored village corner")
    check(in_safe_zone(*SAFE_ZONE_CENTER), "safe-zone center is inside the hub")
    check(in_safe_zone(*SPAWN), "player spawn stays inside the safe hub")
    check(not in_safe_zone(2600.0, 1200.0), "graveyard is outside the safe hub")
    px, py = push_out(SAFE_ZONE_CENTER[0], SAFE_ZONE_CENTER[1], 24.0)
    check(not in_safe_zone(px, py, 0.0),
          "push_out moves a point just outside the padded safe zone")
    spawner_source = (ROOT / "scripts" / "spawner.py").read_text("utf-8")
    check("in_safe_zone" in spawner_source,
          "spawner rejects candidate positions inside the hub")
    # A live enemy that somehow enters the hub is expelled on the next tick.
    if game.combat.enemies:
        enemy = game.combat.enemies[0]
        enemy.x = enemy.home_x = SAFE_ZONE_CENTER[0]
        enemy.y = enemy.home_y = SAFE_ZONE_CENTER[1]
        game.combat._enforce_safe_zone()
        check(not in_safe_zone(enemy.x, enemy.y, 8.0),
              "a chasing enemy is pushed out of the safe zone")
    else:                                   # pragma: no cover - safety net
        check(False, "the opening enemy group exists for the exclusion test")

    # ==================================================================
    section("4. NPC identities, positions, collision and prompts")
    ids = [npc.id for npc in game.npcs.npcs]
    check(ids == list(NPC_IDS), "exactly the three survivors are created")
    by_id = {npc.id: npc for npc in game.npcs.npcs}
    for npc_id, expected_pos in {
        "merchant": (1662.0, 1058.0),
        "blacksmith": (1388.0, 1090.0),
        "veil_keeper": (1578.0, 966.0),
    }.items():
        npc = by_id[npc_id]
        check((npc.x, npc.y) == expected_pos,
              f"{npc_id} stands at its authored stall/workshop/shrine position")
        check(in_safe_zone(npc.x, npc.y),
              f"{npc_id} is placed inside the safe hub")
    check(by_id["merchant"].prompt == "G  TRADE"
          and by_id["blacksmith"].prompt == "G  FORGE"
          and by_id["veil_keeper"].prompt == "G  TALK",
          "each service shows the contextual G prompt")
    check(by_id["veil_keeper"].accent != by_id["merchant"].accent,
          "the Veil Keeper has a distinct violet accent")
    # NPC foot boxes join the existing collision hash.
    for npc in game.npcs.npcs:
        check(any(rect == npc.solid_rect() for rect in game.world.collision.rects),
              f"{npc.id} foot box is registered as a solid")
    # Reachability and wall blocking with a deterministic empty world.
    empty = CollisionWorld([], lambda name: (64, 64))
    fake_npc = SimpleNamespace(x=1000.0, y=1000.0, radius=100.0,
                               id="test", prompt="G  TALK", name="TEST",
                               accent=(200, 200, 200))
    fake_npcs = SimpleNamespace(npcs=[fake_npc])
    interaction = InteractionManager(fake_npcs, empty)
    player = SimpleNamespace(x=1060.0, y=1000.0)
    check(interaction.visible(player, fake_npc) is True,
          "an unobstructed survivor is visible for interaction")
    empty.add_rect(pygame.Rect(1028, 940, 8, 120))
    check(interaction.visible(player, fake_npc) is False,
          "a wall between player and survivor blocks interaction")
    check(interaction.find(player) is None,
          "G does not target a survivor standing behind a wall")
    # Facing while interacting.
    keeper = by_id["veil_keeper"]
    keeper.facing = "down"
    keeper.face_player(SimpleNamespace(x=keeper.x, y=keeper.y - 80))
    check(keeper.facing == "up", "survivors face the player when approached")

    # ==================================================================
    section("5. Data-driven dialogue, choices, flags and keyboard")
    dialogue = DialogueManager()
    check(dialogue.open("does_not_exist") is False,
          "unknown dialogue IDs are rejected safely")
    check(dialogue.open("merchant", "merchant") is True,
          "merchant conversation opens from data")
    check(dialogue.has_choices and font_ok(dialogue.text),
          "opening page has pixel-font-safe text and choices")
    action = dialogue.choose(0)
    check(action == "open_shop" and not dialogue.active,
          "the SHOW ME YOUR WARES choice opens trade and closes dialogue")
    dialogue.open("veil_keeper", "veil_keeper")
    check("veil" in dialogue.text.lower(),
          "Veil Keeper opens with original mysterious dialogue")
    check("hollow_forest_hint" not in dialogue.flags,
          "no story flag is set before the forest hint page")
    dialogue.choose(1)
    check(dialogue.flags.get("hollow_forest_hint") is True,
          "the Hollow Forest hint flag fires when its page is read")
    dialogue.choose(0)
    check(dialogue.flags.get("veil_keeper_lore") is True,
          "deeper lore sets a second forward-compatible flag")
    dialogue.choose(0)
    check(dialogue.page_index == 0 and dialogue.active,
          "the BACK choice returns to the opening page")
    # Keyboard navigation: arrows move the cursor, SPACE activates, ESC closes.
    screen_game = fresh_game()
    screen_game.open_dialogue(screen_game.npcs.get("blacksmith"))
    assert screen_game.state == DIALOGUE
    screen_game.dialogue_screen.handle_event(key_event(pygame.K_DOWN))
    check(screen_game.dialogue_screen.cursor == 1,
          "DOWN moves the highlighted dialogue choice")
    action = screen_game.dialogue_screen.handle_event(key_event(pygame.K_SPACE))
    check(action == "" and screen_game.dialogue.page_index == 1,
          "SPACE activates the highlighted choice")
    action = screen_game.dialogue_screen.handle_event(key_event(pygame.K_ESCAPE))
    screen_game._route_dialogue_action(action)
    check(screen_game.state == PLAY and not screen_game.dialogue.active,
          "ESC closes the conversation and returns to play")
    # Mouse click on a choice, routed through Game exactly like a real event.
    screen_game.open_dialogue(screen_game.npcs.get("merchant"))
    rects = screen_game.dialogue_screen.choice_rects()
    check(len(rects) == 3, "the merchant opening page exposes three choices")
    action = screen_game.dialogue_screen.handle_event(click_event(rects[0].center))
    screen_game._route_dialogue_action(action)
    check(screen_game.state == SHOP,
          "clicking a choice routes through the same dialogue action")

    # ==================================================================
    section("6. Merchant trade: stock, gold, validation and sales")
    shop_game = fresh_game()
    shop = shop_game.shop
    check(len(shop.entries) == 13 and len(shop.categories) == 5,
          "thirteen stock entries span five named categories")
    check(shop.sell_rate == 0.5 and shop.max_quantity == 10,
          "configurable sell rate and quantity cap load from data")
    entry = shop.entry("rusted_blade")
    check(entry is not None and entry.limited and entry.stock == 1,
          "unique equipment has a limited stock of one")
    consumable = shop.entry("minor_health_potion")
    check(consumable is not None and not consumable.limited,
          "consumables are unlimited restock")
    shop_game.inventory.gold = 5000
    gold_before = shop_game.inventory.gold
    check(shop.buy("rusted_blade", 1) is True,
          "a valid purchase succeeds")
    check(shop_game.inventory.gold == gold_before - entry.price,
          "the exact catalogue price is deducted from real gold")
    check(shop.bought("rusted_blade") == 1 and shop.remaining("rusted_blade") == 0,
          "limited stock decreases and cannot be re-bought")
    check(shop.buy("rusted_blade", 1) is False and "SOLD" in shop.last_message,
          "a second purchase of sold-out stock is refused")
    shop_game.inventory.gold = 0
    check(shop.buy("minor_health_potion", 1) is False
          and "GOLD" in shop.last_message,
          "insufficient gold produces a clear notification")
    check(shop.buy("nonexistent_item", 1) is False,
          "unknown item IDs cannot be purchased")
    # Sales use the real inventory index and protect equipped gear.
    shop_game.inventory.gold = 0
    shop_game.inventory.add("ash_shard", 3)
    idx = next(i for i, e in enumerate(shop_game.inventory.entries)
               if e.item_id == "ash_shard")
    expected = shop.sell_price("ash_shard", 2)
    check(shop.sell(idx, 2) is True and shop_game.inventory.gold == expected,
          "selling a stack pays the computed 50 percent value")
    check(shop_game.inventory.count("ash_shard") == 1,
          "selling removes exactly the requested quantity")
    shop_game.equipment.equip("rusted_blade")
    check(shop.can_sell("rusted_blade") is False,
          "equipped items are protected from sale")
    shop_idx = next(i for i, e in enumerate(shop_game.inventory.entries)
                    if e.item_id == "rusted_blade")
    check(shop.sell(shop_idx, 1) is False,
          "a sale of equipped gear is rejected, not silently duplicated")
    # Descriptions and prices are pixel-font-safe and populated.
    check(all(font_ok(get_item(e.item_id).description) for e in shop.entries),
          "every stocked item has a font-safe description")
    check(all(shop.buy_price(e.item_id) > 0 for e in shop.entries),
          "every stocked item has a positive price")
    # Full-screen draw must not crash with the real overlay.
    shop_game.state = SHOP
    shop_game.merchant_screen.open()
    shop_game.draw()
    check(True, "merchant overlay draws without error")

    # ==================================================================
    section("7. Blacksmith costs, real stats and no duplicate bonuses")
    forge_game = fresh_game()
    forge = forge_game.blacksmith
    check(forge.max_level == MAX_UPGRADE_LEVEL == 5,
          "forge is bounded to levels +0..+5")
    expected_costs = {
        1: (80, {"ash_shard": 2}),
        2: (160, {"ash_shard": 4}),
        3: (300, {"ash_shard": 3, "guardian_ember": 1}),
        4: (520, {"ash_shard": 5, "guardian_ember": 2}),
        5: (820, {"ash_shard": 8, "guardian_ember": 3}),
    }
    for level, (gold, materials) in expected_costs.items():
        cost = forge.costs[level]
        check(cost["gold"] == gold and cost["materials"] == materials,
              f"+{level} costs {gold} gold and the right materials")
    check(forge.eligible("rusted_blade") is True
          and forge.eligible("minor_health_potion") is False,
          "only weapons and armor are forgeable")
    forge_game.inventory.gold = 6000
    forge_game.inventory.add("ash_shard", 40)
    forge_game.inventory.add("guardian_ember", 20)
    forge_game.equipment.equip("rusted_blade")
    forge_game.equipment.recompute()
    attack_before = forge_game.stats.attack
    base_item = get_item("rusted_blade")
    check(forge.upgrade("rusted_blade") is True and forge.level("rusted_blade") == 1,
          "the first forge succeeds and records level +1")
    forge_game.equipment.recompute()
    check(abs((forge_game.stats.attack - attack_before) - 2.0) < 1e-6,
          "weapon +1 adds exactly +2 attack to live stats")
    eff = forge.effective_item(base_item)
    check(eff is not None and eff.name == "RUSTED BLADE +1",
          "effective gear displays the +1 suffix")
    check(eff.item_id == base_item.item_id and eff.rarity == base_item.rarity,
          "forging preserves item identity and rarity")
    preview = forge.preview_item(base_item)
    check(preview is not None
          and abs(preview.stats["attack"] - eff.stats["attack"] - 2.0) < 1e-6,
          "the preview matches the next real stat step")
    # Drive all the way to +5 with the higher-level materials.
    for _ in range(4):
        check(forge.upgrade("rusted_blade") is True,
              f"forging to +{forge.level('rusted_blade')} succeeds with materials")
    check(forge.is_max("rusted_blade") is True,
          "the forge stops at +5")
    ok, reason = forge.can_upgrade("rusted_blade")
    check(ok is False and "MAX" in reason.upper() or ok is False,
          "no upgrade is possible past the maximum level")
    final = forge.effective_item(base_item)
    check(abs(final.stats["attack"] - (base_item.stats["attack"] + 10.0)) < 1e-6,
          "a +5 weapon has exactly five attack steps, never doubled")
    snapshot = forge_game.stats.attack
    forge_game.equipment.recompute()
    check(abs(forge_game.stats.attack - snapshot) < 1e-6,
          "recomputing equipment twice never double-applies forge bonuses")
    check(forge.invested_gold("rusted_blade") == sum(c[0] for c in expected_costs.values()),
          "invested gold reflects every forge level")
    check(forge.resale_bonus("rusted_blade") == forge.invested_gold("rusted_blade") // 2,
          "a forged item sells back with a bounded upgrade resale bonus")
    check(forge.can_upgrade("rusted_blade")[0] is False,
          "maxed gear reports no further upgrade")
    # Changing callback fired on a successful forge.
    changes = []
    tracker = BlacksmithManager(forge_game.inventory, on_change=lambda: changes.append(1))
    tracker.load_state({"levels": {"rusted_blade": 1}})
    tracker.inventory.gold = 1000
    tracker.inventory.add("ash_shard", 10)
    tracker.upgrade("rusted_blade")
    check(len(changes) >= 1, "successful forging notifies the save callback")
    forge_game.state = BLACKSMITH
    forge_game.blacksmith_screen.open()
    forge_game.draw()
    check(True, "blacksmith overlay draws without error")

    # ==================================================================
    section("8. Veil Keeper story, future quest flags and Level 02")
    story_game = fresh_game()
    keeper = story_game.npcs.get("veil_keeper")
    story_game.player.x, story_game.player.y = keeper.x + 40, keeper.y
    story_game._context_interact()
    check(story_game.state == DIALOGUE
          and story_game.dialogue.dialogue_id == "veil_keeper",
          "pressing G near the Keeper opens her unique dialogue")
    check(keeper.talked and keeper.interactions == 1,
          "talking records NPC state for future quests")
    story_game.dialogue.choose(1)   # Hollow Forest hint
    story_game.dialogue.choose(0)   # deeper lore
    check("hollow_forest_hint" in story_game.dialogue.flags
          and "veil_keeper_lore" in story_game.dialogue.flags,
          "the Keeper sets both story flags without a quest system")
    check(story_game.progression.is_unlocked("01") is True,
          "Level 01 remains available")
    check(story_game.progression.is_unlocked("02") is False,
          "the Keeper never directly unlocks Level 02")
    check(story_game.set_quest_flag("hollow_forest_path", True) is True
          and story_game.quest_flags["hollow_forest_path"] is True,
          "a forward-compatible quest flag can be set safely")

    # ==================================================================
    section("9. Additive save schema and validation")
    clean = canonical_data({})
    for key in ("npc_state", "dialogue", "shop", "upgrades", "quest_flags"):
        check(key in clean, f"clean profile contains the additive {key} section")
    check(clean["version"] == SAVE_VERSION == 1,
          "save version stays 1 for backward compatibility")
    legacy = {
        "version": 1, "levels": {}, "player": {}, "inventory": {},
        "defeated_enemies": [],
    }
    loaded = canonical_data(legacy)
    check(all(loaded[k] == clean[k] for k in (
        "npc_state", "dialogue", "shop", "upgrades", "quest_flags")),
        "a Phase 5/6/7 save without new keys loads with clean defaults")
    hostile = canonical_data({
        "npc_state": {"merchant": {"talked": "yes", "interactions": -50},
                      "not_a_npc": {"talked": True}},
        "dialogue": {"seen": ["veil_keeper", "bogus"],
                     "flags": {"hollow_forest_hint": 1}},
        "shop": {"purchases": {"rusted_blade": 999999, "nope": 4}},
        "upgrades": {"levels": {"rusted_blade": 99, "minor_health_potion": 3}},
        "quest_flags": {"future": "truthy"},
    })
    check("not_a_npc" not in hostile["npc_state"],
          "unknown NPC IDs are stripped on load")
    check(hostile["npc_state"]["merchant"]["interactions"] == 0,
          "negative NPC counters are clamped to zero")
    check(hostile["dialogue"]["seen"] == ["veil_keeper"],
          "unknown seen dialogue IDs are discarded")
    check(hostile["shop"]["purchases"].get("nope") is None,
          "unknown shop item counters are discarded")
    check(hostile["upgrades"]["levels"] == {"rusted_blade": MAX_UPGRADE_LEVEL},
          "forge levels are clamped and non-equipment entries rejected")
    check(hostile["quest_flags"].get("future") is True,
          "future quest flags survive as booleans")
    # Full round trip through a second Game instance on the same profile.
    save_game = fresh_game()
    save_path = Path(os.environ["ASHEN_VEIL_SAVE"])
    save_game.inventory.gold = 4321
    save_game.shop.buy("rusted_blade", 1)
    save_game.blacksmith.inventory.add("ash_shard", 20)
    save_game.blacksmith.inventory.add("guardian_ember", 10)
    save_game.blacksmith.upgrade("rusted_blade")
    save_game.npcs.get("merchant").talked = True
    save_game.dialogue.set_flag("hollow_forest_hint", True)
    save_game.set_quest_flag("future_quest", True)
    save_game._save_inventory()
    save_game._save_village()
    disk = load_profile(save_path)
    check(disk["inventory"]["gold"] == save_game.inventory.gold,
          "gold is persisted with the inventory")
    check(disk["shop"]["purchases"].get("rusted_blade") == 1,
          "limited shop purchases persist")
    check(disk["upgrades"]["levels"].get("rusted_blade") == 1,
          "forge levels persist keyed by real item ID")
    check(disk["npc_state"]["merchant"]["talked"] is True,
          "NPC conversation state persists")
    check(disk["dialogue"]["flags"].get("hollow_forest_hint") is True,
          "dialogue story flags persist")
    check(disk["quest_flags"].get("future_quest") is True,
          "future quest flags persist additively")
    os.environ["ASHEN_VEIL_SAVE"] = str(save_path)
    restored = Game()
    check(restored.inventory.gold == save_game.inventory.gold,
          "a new Game restores persisted gold")
    check(restored.blacksmith.level("rusted_blade") == 1,
          "a new Game restores forge levels")
    check(restored.shop.bought("rusted_blade") == 1,
          "a new Game restores shop purchases")
    check(restored.dialogue.flags.get("hollow_forest_hint") is True,
          "a new Game restores dialogue flags")
    check(restored.quest_flags.get("future_quest") is True,
          "a new Game restores future quest flags")
    check(restored.npcs.get("merchant").talked is True,
          "a new Game restores NPC state")
    # Equipped forged item must restore with live bonus stats too.
    restored.equipment.equip("rusted_blade")
    check(restored.equipment.equipped_item("weapon").name == "RUSTED BLADE +1",
          "equipped forged gear restores with its +1 bonus")

    # ==================================================================
    section("10. Existing systems remain intact")
    regression = fresh_game()
    check(regression.progression.is_unlocked("01")
          and not regression.progression.is_unlocked("02"),
          "level unlock rules are unchanged")
    start_attack = regression.stats.attack
    regression.inventory.add("ashfang_saber", 1)
    regression.equipment.equip("ashfang_saber")
    check(regression.stats.attack >= start_attack,
          "equipment still changes live stats")
    check(len(regression.equipment.comparison(get_item("veilcleaver"))) > 0,
          "item comparison still works alongside forge previews")
    regression.exp.award_exp(4000)
    check(regression.exp.total_exp >= 4000,
          "EXP progression still accumulates")
    regression.tree.purchase("a1")
    check(regression.tree.has("a1"),
          "Void skill tree purchases still work")
    regression.player.request_attack()
    for _ in range(5):
        regression.update(1 / 60)
    check(regression.player.combat is not None,
          "player combat still ticks with the hub present")
    regression.inventory.spend_gold(20)
    check(regression.inventory.gold == 100,
          "inventory gold bookkeeping still starts from 120 and spends correctly")
    regression.state = PLAY
    regression.draw()
    check(True, "the full world draws with NPCs, HUD, loot and overlays")

    # ==================================================================
    section("11. Web archive contents")
    archive = ROOT / "build" / "web" / "game.tar.gz"
    if archive.is_file():
        with tarfile.open(archive, "r:gz") as bundle:
            names = bundle.getnames()
        check(any(name.endswith("main.py") for name in names),
              "the web archive contains main.py")
        expected_archive = tuple(s for s in expected_sources
                                 if not s.startswith("tools/")) + (
            "data/npcs/merchant.json",
            "data/dialogue/veil_keeper_dialogue.json",
            "data/shops/merchant_stock.json",
            "data/blacksmith/upgrades.json",
            "assets/npcs/merchant.png", "assets/npcs/blacksmith.png",
            "assets/npcs/veil_keeper.png",
        )
        check(all(any(name.endswith(source) for name in names)
                  for source in expected_archive),
              "the web archive ships every Phase 8 module, data file and sprite")
        check(not any(name.startswith("./tools") for name in names),
              "development tools remain excluded from the web build")
    else:
        check(False, "the Pygbag archive exists (run the web build first)")

    if FAILED:
        print(f"\nFAILED {len(FAILED)} CHECK(S):")
        for message in FAILED:
            print(f"  - {message}")
        raise SystemExit(1)
    print(f"\nALL PHASE 8 CHECKS PASSED ({PASSED} assertions).")


if __name__ == "__main__":
    main()
