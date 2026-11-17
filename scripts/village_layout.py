"""Hand-authored layout of Ashen Village.

This module is intentionally free of pygame so the same data can be used by
the offline ground baker (tools/bake_ground.py) and by the game itself.
All coordinates are in world pixels; every prop's (x, y) is the point where
the prop meets the ground (its visual anchor).
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Prop:
    name: str
    x: int
    y: int
    flip: bool = False
    scale: float = 1.0
    variant: str = ""


@dataclass(frozen=True)
class Road:
    x1: float
    y1: float
    x2: float
    y2: float
    width: float
    kind: str = "road"  # road | side | trail


@dataclass(frozen=True)
class Patch:
    kind: str  # cobble | dirt | dark_soil | purple_moss | ruin_moss
    x: float
    y: float
    rx: float
    ry: float
    angle: float = 0.0


@dataclass(frozen=True)
class Light:
    x: float
    y: float
    radius: float
    color: tuple[int, int, int]
    intensity: float = 0.55
    flicker: float = 0.0
    phase: float = 0.0


PLAZA = (1600.0, 1300.0, 396.0, 286.0)

# ---------------------------------------------------------------------------
# The Hollow Guardian's arena.  It lives in the north-east corner of the same
# world, beyond the graveyard, so it can reuse the baked ground and the shared
# camera/collision systems.  Props inside this rectangle are stripped from the
# village layout and replaced with the ruined-shrine set below.
# ---------------------------------------------------------------------------
ARENA_X0, ARENA_Y0, ARENA_X1, ARENA_Y1 = 2240, 168, 3036, 756
ARENA_RECT = (ARENA_X0, ARENA_Y0, ARENA_X1, ARENA_Y1)
ARENA_CENTER = (2638.0, 462.0)
ARENA_PLAYER_SPAWN = (2638.0, 682.0)
ARENA_BOSS_SPAWN = (2638.0, 372.0)
ARENA_PLAYER_BOUNDS = (2336.0, 232.0, 2940.0, 692.0)
ARENA_BOSS_BOUNDS = (2356.0, 252.0, 2920.0, 676.0)
# The arena hugs the north edge of the world, so a camera centred on the
# player would push the guardian's 300 px silhouette off the top of the
# screen.  During the encounter the camera aims this many pixels north of the
# player, keeping both fighters and the whole boss readable on screen.
ARENA_CAMERA_LIFT = 300.0


def _inside_arena(x: float, y: float, pad: float = 70.0) -> bool:
    return (ARENA_X0 - pad <= x <= ARENA_X1 + pad
            and ARENA_Y0 - pad <= y <= ARENA_Y1 + pad)


def _outside_arena(props: list[Prop], pad: float = 70.0) -> list[Prop]:
    return [prop for prop in props if not _inside_arena(prop.x, prop.y, pad)]


ROADS: list[Road] = [
    Road(1600, 2400, 1600, 760, 286),          # main north-south road
    Road(0, 1300, 3200, 1300, 246),            # east-west road
    Road(1600, 1290, 1135, 1115, 152, "side"),  # to the west house
    Road(1600, 1290, 2085, 1055, 150, "side"),  # to the east house
    Road(1510, 1300, 540, 1030, 158, "side"),   # to the purple tower
    Road(1755, 1288, 2455, 875, 156, "side"),   # to the graveyard
    Road(1715, 1375, 2505, 1770, 146, "side"),  # to the ruins
    Road(1460, 790, 1090, 385, 118, "trail"),   # around the church (west)
    Road(1740, 790, 2110, 385, 118, "trail"),   # around the church (east)
    Road(1090, 390, 2110, 390, 112, "trail"),   # church back trail
    Road(960, 1550, 1110, 1850, 110, "trail"),  # field trail
]

# Extra ground colour patches.  They are blended into the baked ground before
# the fine scatter is applied.
PATCHES: list[Patch] = [
    Patch("dark_soil", 2570, 840, 330, 210, -14),
    Patch("dark_soil", 2470, 900, 130, 120, 20),
    Patch("purple_moss", 520, 1100, 230, 165, 18),
    Patch("purple_moss", 430, 920, 145, 130, -25),
    Patch("purple_moss", 2620, 1880, 270, 170, 12),
    Patch("purple_moss", 540, 1590, 165, 105, -8),
    Patch("ruin_moss", 2510, 1860, 330, 170, -6),
    Patch("ruin_moss", 2720, 1940, 190, 120, 25),
    Patch("dirt", 840, 1710, 300, 190, -12),
    Patch("dirt", 1900, 2100, 250, 150, 8),
]

# ---------------------------------------------------------------------------
# Props — placed by hand for composition rather than dumped randomly.
# ---------------------------------------------------------------------------
CORE_PROPS: list[Prop] = [
    # --- plaza / market -----------------------------------------------------
    Prop("well", 1600, 1330),
    Prop("signpost", 1790, 1362),
    Prop("statue_great", 1362, 1452),
    Prop("cart", 1930, 1215),
    Prop("barrel_a", 2030, 1272),
    Prop("barrel_c", 2008, 1320),
    Prop("crate_a", 2072, 1316),
    Prop("crate_b", 1996, 1360),
    Prop("lamp_post", 1382, 1478),
    Prop("lamp_post", 1818, 1478),
    Prop("lamp_post", 1430, 1132),
    Prop("lamp_post", 1772, 1126),
    # --- west house / workshop ---------------------------------------------
    Prop("house_timber", 1075, 1062),
    Prop("woodpile", 1280, 1180),
    Prop("logs", 1318, 1235),
    Prop("barrel_d", 1286, 1100),
    Prop("barrel_e", 1326, 1144),
    Prop("crate_c", 1212, 1146),
    Prop("crate_d", 988, 1156),
    Prop("barrel_b", 944, 1100),
    Prop("well_small", 913, 1224),
    # --- east house / stable ------------------------------------------------
    Prop("house_long", 2140, 1035),
    Prop("barrel_f", 1965, 1080),
    Prop("crate_a", 2010, 1105),
    Prop("woodpile", 2050, 1130),
    Prop("cart", 2268, 1156, True),
    Prop("logs", 2340, 1096),
    # --- church -------------------------------------------------------------
    Prop("church", 1600, 748),
    Prop("stone_pillar_tall", 1415, 868),
    Prop("stone_pillar_tall", 1785, 868),
    Prop("grave_cross_b", 1330, 810),
    Prop("grave_cross_b", 1870, 810),
    Prop("lamp_post", 1480, 930),
    Prop("lamp_post", 1720, 930),
    # --- south entrance -----------------------------------------------------
    Prop("stone_gate", 1600, 2180),
    Prop("lantern_tall", 1456, 2132),
    Prop("lantern_tall", 1744, 2132),
    Prop("stone_wall_gate", 1330, 2145),
    Prop("stone_wall_gate", 1870, 2145, True),
    Prop("rock_c", 1398, 2260),
    Prop("rock_d", 1800, 2280, True),
    Prop("tree_dead", 1260, 2050),
    Prop("tree_dead_b", 1940, 2070, True),
    # --- purple tower / portal ---------------------------------------------
    Prop("tower_purple", 455, 962),
    Prop("portal", 566, 1138),
    Prop("statue", 372, 1174),
    Prop("stone_pillar_tall", 650, 1045),
    Prop("stone_pillar", 300, 1040),
    Prop("shrine", 690, 1138),
    Prop("lantern_tall", 505, 1245),
    Prop("bush_i", 625, 1200),
    Prop("bush_j", 680, 1216, True),
    # --- graveyard ----------------------------------------------------------
    Prop("stone_tower", 2840, 760),
    Prop("gravestone_a", 2330, 800),
    Prop("gravestone_b", 2416, 878, True),
    Prop("gravestone_c", 2494, 782),
    Prop("gravestone_d", 2580, 884),
    Prop("grave_cross", 2670, 760),
    Prop("gravestone_a", 2730, 930, True),
    Prop("grave_cross_b", 2278, 930),
    Prop("skull", 2468, 940),
    Prop("bones", 2564, 952, True),
    Prop("skull_b", 2380, 855),
    Prop("shrine", 2812, 1010),
    Prop("tree_dead", 2246, 690, True),
    Prop("tree_dead_b", 2870, 900),
    Prop("tree_dead_small", 2630, 1014),
    Prop("fence_rail_b", 2240, 1032),
    Prop("fence_rail_b", 2372, 1032),
    Prop("fence_rail_b", 2504, 1032),
    Prop("fence_rail_b", 2636, 1032),
    Prop("fence_rail_b", 2768, 1032),
    # --- south-east ruins ---------------------------------------------------
    Prop("stone_arch", 2530, 1818),
    Prop("stone_wall", 2300, 1908),
    Prop("stone_wall", 2750, 1934, True),
    Prop("stone_pillar_tall", 2380, 1848),
    Prop("rubble_b", 2432, 1954),
    Prop("rubble_a", 2650, 1988),
    Prop("rubble_c", 2708, 1856, True),
    Prop("bones", 2498, 1912),
    Prop("skull", 2596, 1872, True),
    Prop("tree_dead_tall", 2246, 1752),
    Prop("tree_dead", 2856, 1738, True),
    Prop("tree_dead_b", 2900, 1936),
    Prop("bush_f", 2344, 1972),
    # --- west field ---------------------------------------------------------
    Prop("fence_a", 520, 1600),
    Prop("fence_a", 634, 1600),
    Prop("fence_a", 748, 1600),
    Prop("fence_gate", 900, 1608),
    Prop("fence_b", 1130, 1600, True),
    Prop("fence_b", 1262, 1600, True),
    Prop("fence_rail", 520, 1730),
    Prop("fence_rail", 633, 1730),
    Prop("fence_rail_b", 828, 1740, True),
    Prop("bush_a", 690, 1670),
    Prop("bush_c", 820, 1700),
    Prop("bush_e", 1000, 1682),
    Prop("plant_c", 760, 1760),
    Prop("plant_a", 930, 1780),
    Prop("tree_dead_big", 268, 1490),
    Prop("tree_dead_tall", 952, 1492),
    Prop("rock_a", 420, 1810),
    Prop("rock_b", 1080, 1830),
    # --- outlier landmarks --------------------------------------------------
    Prop("stone_arch", 690, 470, True),
    Prop("stone_wall", 900, 520, True),
    Prop("rubble_b", 560, 540),
    Prop("tree_dead_tall", 300, 330),
    Prop("tree_dead_big", 2920, 340, True),
    Prop("tree_dead", 2200, 300),
    Prop("tree_dead_b", 960, 300),
]

# ---------------------------------------------------------------------------
# Ruined shrine arena — a sealed ring of broken masonry around the guardian.
# The interior stays deliberately clear: the boss needs room, and every attack
# telegraph must read against empty stone.
# ---------------------------------------------------------------------------
ARENA_PROPS: list[Prop] = [
    # Sealed north face, with the shrine and its dead gate at the centre.
    Prop("stone_wall", 2380, 236),
    Prop("stone_wall", 2900, 236, True),
    Prop("stone_pillar_tall", 2304, 250),
    Prop("stone_pillar_tall", 2972, 250),
    Prop("stone_gate", 2638, 250),
    Prop("shrine", 2638, 262),
    Prop("portal", 2638, 262),
    # Side colonnade, deliberately broken and uneven.
    Prop("stone_pillar_tall", 2310, 386),
    Prop("stone_pillar_tall", 2970, 386),
    Prop("stone_pillar", 2320, 566),
    Prop("stone_pillar", 2960, 566),
    Prop("stone_wall", 2308, 692, True),
    Prop("stone_wall", 2972, 692),
    # Broken guardians flanking the boss dais.
    Prop("statue_great", 2440, 318),
    Prop("statue_great", 2836, 318, True),
    Prop("rubble_b", 2372, 470),
    Prop("rubble_c", 2904, 470, True),
    Prop("rubble_a", 2450, 620),
    Prop("rubble_a", 2828, 620, True),
    # Braziers: the only warm-ish light in an otherwise purple room.
    Prop("lantern_tall", 2322, 314),
    Prop("lantern_tall", 2954, 314),
    Prop("lantern_tall", 2322, 646),
    Prop("lantern_tall", 2954, 646),
    # Debris and the bones of the last challengers.
    Prop("bones", 2520, 590),
    Prop("skull", 2560, 560, True),
    Prop("skull_b", 2720, 588),
    Prop("bones", 2760, 616, True),
    # The way in is a dead gate: visual only, the player arrives by the veil.
    Prop("stone_gate", 2638, 748),
    Prop("stone_wall_gate", 2450, 744, True),
    Prop("stone_wall_gate", 2826, 744),
]


# ---------------------------------------------------------------------------
# Deterministic scatter — clustered so it reads as growth, not noise.
# ---------------------------------------------------------------------------
def _scatter() -> list[Prop]:
    rng = random.Random(0xA5E)
    props: list[Prop] = []

    # Wild growth clusters in the corners and between landmarks.
    clusters = [
        (260, 700, 260, 300, "forest"),
        (780, 660, 220, 240, "brush"),
        (1180, 520, 210, 220, "forest"),
        (1990, 560, 200, 220, "brush"),
        (2300, 430, 250, 200, "forest"),
        (2960, 1260, 220, 300, "forest"),
        (2700, 1380, 260, 220, "brush"),
        (2200, 1480, 200, 170, "brush"),
        (1130, 1390, 180, 170, "brush"),
        (760, 1340, 180, 160, "brush"),
        (360, 1350, 240, 260, "forest"),
        (1480, 1740, 280, 210, "brush"),
        (1900, 1830, 260, 210, "brush"),
        (2080, 2070, 300, 200, "forest"),
        (820, 2050, 300, 210, "forest"),
        (2860, 2130, 260, 170, "forest"),
        (300, 2080, 240, 170, "forest"),
        (2890, 540, 190, 220, "brush"),
        (1600, 330, 300, 150, "forest"),
    ]
    brush = [
        "bush_a", "bush_b", "bush_c", "bush_d", "bush_e", "bush_f",
        "bush_g", "bush_h", "bush_k", "plant_a", "plant_b", "plant_c",
        "plant_d", "bush_i", "bush_j",
    ]
    rocks = ["rock_a", "rock_b", "rock_c", "rock_d", "rock_e", "rubble_c"]
    trees = ["tree_dead", "tree_dead_b", "tree_dead_small", "tree_dead_small_b"]

    for cx, cy, rx, ry, kind in clusters:
        count = rng.randint(5, 9) if kind == "forest" else rng.randint(6, 11)
        for _ in range(count):
            angle = rng.uniform(0, math.tau)
            dist = math.sqrt(rng.random())
            x = int(cx + math.cos(angle) * rx * dist)
            y = int(cy + math.sin(angle) * ry * dist)
            roll = rng.random()
            if kind == "forest":
                if roll < 0.42:
                    name = rng.choice(trees)
                elif roll < 0.7:
                    name = rng.choice(brush)
                elif roll < 0.88:
                    name = rng.choice(rocks)
                else:
                    name = "bush_f"
            else:
                if roll < 0.58:
                    name = rng.choice(brush)
                elif roll < 0.84:
                    name = rng.choice(rocks)
                else:
                    name = rng.choice(trees)
            props.append(Prop(name, x, y, rng.random() < 0.5))
    return props


SCATTER_PROPS: list[Prop] = _scatter()


def _forest_ring() -> list[Prop]:
    """Dead forest crowding the world border (masks the world edge)."""
    rng = random.Random(0xF0E5)
    props: list[Prop] = []
    kinds = ["tree_dead", "tree_dead_b", "tree_dead_tall", "tree_dead_big",
             "tree_dead_small", "tree_dead_small_b"]
    for x in range(90, 3160, 176):
        for y, spread in ((150, 150), (2290, 120)):
            if 1330 < x < 1870 and y > 2000:
                continue
            if abs(x - 1600) < 220 and y < 500:
                continue
            props.append(Prop(rng.choice(kinds),
                              int(x + rng.randint(-55, 55)),
                              int(y + rng.randint(-70, 70)),
                              rng.random() < 0.5))
    for y in range(300, 2260, 176):
        for x, spread in ((120, 130), (3080, 130)):
            props.append(Prop(rng.choice(kinds),
                              int(x + rng.randint(-70, 70)),
                              int(y + rng.randint(-50, 50)),
                              rng.random() < 0.5))
    return props


FOREST_PROPS: list[Prop] = _forest_ring()

ALL_PROPS: list[Prop] = (
    _outside_arena(CORE_PROPS)
    + ARENA_PROPS
    + _outside_arena(SCATTER_PROPS)
    + _outside_arena(FOREST_PROPS)
)


# ---------------------------------------------------------------------------
# Lights — authored, with a few tied to landmark windows.
# ---------------------------------------------------------------------------
LIGHTS: list[Light] = [
    Light(1456, 2022, 280, (150, 108, 232), 0.65, 0.16, 0.4),
    Light(1744, 2022, 280, (150, 108, 232), 0.65, 0.16, 2.1),
    Light(1480, 852, 260, (139, 121, 222), 0.52, 0.10, 1.3),
    Light(1720, 852, 260, (139, 121, 222), 0.52, 0.10, 3.7),
    Light(1430, 1052, 240, (145, 121, 225), 0.50, 0.12, 2.8),
    Light(1772, 1046, 240, (145, 121, 225), 0.50, 0.12, 5.1),
    Light(1382, 1398, 240, (148, 126, 232), 0.48, 0.14, 0.9),
    Light(1818, 1398, 240, (148, 126, 232), 0.48, 0.14, 4.2),
    Light(505, 1135, 270, (160, 106, 240), 0.58, 0.18, 0.3),
    Light(566, 1100, 320, (170, 104, 250), 0.62, 0.25, 2.0),
    Light(455, 752, 190, (135, 84, 210), 0.38, 0.10, 1.8),
    Light(455, 812, 190, (135, 84, 210), 0.38, 0.10, 1.8),
    Light(2812, 990, 230, (132, 156, 220), 0.36, 0.12, 4.8),
    Light(1600, 640, 300, (125, 145, 210), 0.26, 0.03, 0.0),
    Light(2530, 1740, 220, (150, 116, 214), 0.34, 0.10, 3.2),
    Light(1600, 2070, 240, (150, 116, 214), 0.32, 0.10, 5.5),
    # Hollow Guardian arena: cold purple brazier light and a shrine bloom.
    Light(2322, 634, 300, (150, 92, 232), 0.62, 0.22, 0.8),
    Light(2954, 634, 300, (150, 92, 232), 0.62, 0.22, 3.1),
    Light(2322, 314, 250, (176, 104, 250), 0.52, 0.18, 1.9),
    Light(2954, 314, 250, (176, 104, 250), 0.52, 0.18, 4.6),
    Light(2638, 286, 360, (196, 112, 255), 0.58, 0.26, 2.4),
    Light(2638, 520, 420, (108, 62, 176), 0.28, 0.08, 5.7),
]

SPAWN = (1500.0, 1080.0)
SPAWN_FACING = "down"
PLAYER_LIGHT_RADIUS = 150.0

# A few explicit collision boxes that don't follow a prop's bounding box.
# (cx, cy, w, h) in world coordinates.
EXTRA_SOLIDS: list[tuple[float, float, float, float]] = [
    # Stone gate: two piers leave a walkable central archway.
    (1509, 2160, 54, 54),
    (1691, 2160, 54, 54),
    # Arches at the ruins.
    (2458, 1802, 48, 44),
    (2602, 1802, 48, 44),
    (618, 454, 48, 44),
    (762, 454, 48, 44),
    # Fence rows in the graveyard are broken into rail sections; they are
    # already handled by the prop collider, but these seal small gaps.
    (2240, 1032, 14, 16),
    # Sealed arena shell.  Four continuous solids keep the player and the boss
    # inside the shrine regardless of how hard a dash or knockback pushes.
    (2300, 462, 28, 588),
    (2976, 462, 28, 588),
    (2638, 196, 704, 28),
    (2638, 728, 704, 28),
]

# Props that should never block movement.
NON_SOLID = {
    "bones", "skull", "skull_b", "plant_a", "plant_b", "plant_c", "plant_d",
    "bush_i", "bush_j", "bush_h", "shrine", "lantern_tall", "lamp_post",
}

# Validated enemy outposts.  (x, y, initial facing)
#
# The spawner never places an enemy here blindly: every candidate is checked
# against static solids, the player's current position and the other enemies.
# The list is deliberately larger than the active cap so a blocked point can be
# skipped instead of stacking a body inside a house.
ENEMY_SPAWN_POINTS: list[tuple[float, float, str]] = [
    (1740.0, 1200.0, "left"),
    (1180.0, 1390.0, "down"),
    (2380.0, 1130.0, "down"),
    (1780.0, 1950.0, "up"),
    (2000.0, 1380.0, "left"),
    (1840.0, 1980.0, "up"),
    (980.0, 1180.0, "right"),
    (2100.0, 1080.0, "left"),
    (1260.0, 1760.0, "up"),
    (2520.0, 1250.0, "left"),
    (1600.0, 1660.0, "up"),
    (900.0, 1560.0, "up"),
    (2260.0, 1640.0, "left"),
    (1120.0, 1020.0, "down"),
]
ENEMY_SPAWN_RADIUS = 82.0

# Backwards-compatible view used by older tooling: (x, y, radius, facing).
ENEMY_SPAWNS: list[tuple[float, float, float, str]] = [
    (x, y, ENEMY_SPAWN_RADIUS, facing) for x, y, facing in ENEMY_SPAWN_POINTS
]
