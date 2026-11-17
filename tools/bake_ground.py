#!/usr/bin/env python3
"""Bake the Ashen Village ground into a single world-sized image.

The source concept atlas is not a tile sheet, so we first turn the inspected
ground samples into seamless 192x192 textures by mirroring them, then scatter
those patches with random rolls/tints.  Road and plaza masks are drawn with
soft, noise-warped edges; fine detail (grass blades, pebbles, cracks, moss,
puddles) and static prop shadows are painted on top.  The result is one PNG
the game can blit cheaply, which also keeps the browser build fast.

Run from the project root:
    python tools/bake_ground.py
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SLICED = ROOT / "assets" / "sliced"
OUT = ROOT / "assets" / "generated"

import sys

sys.path.insert(0, str(ROOT))
from scripts.village_layout import ALL_PROPS, PATCHES, PLAZA, ROADS  # noqa: E402

W, H = 3200, 2400
CELL = 192
PAD_W, PAD_H = 3264, 2496

MANIFEST = json.loads((SLICED / "manifest.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def load_tile(name: str) -> np.ndarray:
    return np.asarray(Image.open(SLICED / "ground" / f"{name}.png").convert("RGB"), dtype=np.float32)


def seamless(tile: np.ndarray) -> np.ndarray:
    top = np.concatenate([tile, tile[:, ::-1]], axis=1)
    return np.concatenate([top, top[::-1, :]], axis=0)


def smoothstep(edge0, edge1, x):
    t = np.clip((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def value_noise(cells_x: int, cells_y: int, rng: np.random.Generator) -> np.ndarray:
    small = rng.random((max(2, cells_y), max(2, cells_x)), dtype=np.float32)
    img = Image.fromarray((small * 255).astype(np.uint8), "L")
    img = img.resize((PAD_W, PAD_H), Image.BICUBIC)
    arr = np.asarray(img, dtype=np.float32) / 255.0
    return arr


def noise_stack(seed: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    fine = value_noise(96, 72, rng)
    mid = value_noise(28, 21, rng)
    coarse = value_noise(9, 7, rng)
    return fine, mid, coarse


def material(cells: list[np.ndarray], seed: int, tint=(1.0, 1.0, 1.0)) -> np.ndarray:
    rng = random.Random(seed)
    out = np.empty((PAD_H, PAD_W, 3), dtype=np.float32)
    for gy in range(0, PAD_H, CELL):
        for gx in range(0, PAD_W, CELL):
            tile = cells[rng.randrange(len(cells))]
            tile = np.roll(tile, (rng.randrange(CELL), rng.randrange(CELL)), axis=(0, 1))
            if rng.random() < 0.5:
                tile = tile[::-1, :]
            if rng.random() < 0.5:
                tile = tile[:, ::-1]
            bright = rng.uniform(0.975, 1.025)
            block = tile * bright
            out[gy:gy + CELL, gx:gx + CELL] = block
    out *= np.asarray(tint, dtype=np.float32)
    return out


def capsule_distance(x1, y1, x2, y2, X, Y):
    vx, vy = x2 - x1, y2 - y1
    length2 = vx * vx + vy * vy
    if length2 == 0:
        return np.hypot(X - x1, Y - y1)
    t = np.clip(((X - x1) * vx + (Y - y1) * vy) / length2, 0.0, 1.0)
    return np.hypot(X - (x1 + t * vx), Y - (y1 + t * vy))


def ellipse_mask(x, y, rx, ry, angle, X, Y, warp):
    ca, sa = math.cos(angle), math.sin(angle)
    dx, dy = X - x, Y - y
    ux = (dx * ca + dy * sa) / rx
    uy = (-dx * sa + dy * ca) / ry
    q = np.sqrt(ux * ux + uy * uy) + warp * 0.075
    return q


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    print("baking ASHEN VEIL ground ...")

    fine, mid, coarse = noise_stack(17)
    warp = (mid - 0.5) * 2.0

    yy, xx = np.mgrid[0:PAD_H, 0:PAD_W].astype(np.float32)

    # -- material textures ---------------------------------------------------
    grass_src = seamless(load_tile("grass"))
    grass_cells = []
    for i in range(6):
        rng = np.random.default_rng(100 + i)
        rot = grass_src
        # Roll and slightly shift the colour so repeated mirror blocks vanish.
        rot = np.roll(rot, (int(rng.integers(0, CELL)), int(rng.integers(0, CELL))), axis=(0, 1))
        grass_cells.append(rot)
    dirt_cells = [seamless(load_tile("dirt")), seamless(load_tile("dirt_b"))]
    stone_cells = [seamless(load_tile("stone")), seamless(load_tile("stone_b"))]
    moss_cells = [seamless(load_tile("moss_purple")), seamless(load_tile("moss_purple_b"))]

    ground = material(grass_cells, 201, tint=(0.87, 1.01, 0.81))
    ground *= (0.90 + 0.13 * fine + 0.06 * coarse)[..., None]

    # -- masks ---------------------------------------------------------------
    dirt_mask = np.zeros((PAD_H, PAD_W), dtype=np.float32)
    cobble_mask = np.zeros((PAD_H, PAD_W), dtype=np.float32)
    moss_mask = np.zeros((PAD_H, PAD_W), dtype=np.float32)
    dark_mask = np.zeros((PAD_H, PAD_W), dtype=np.float32)
    purple_mask = np.zeros((PAD_H, PAD_W), dtype=np.float32)
    rut_mask = np.zeros((PAD_H, PAD_W), dtype=np.float32)

    for road in ROADS:
        d = capsule_distance(road.x1, road.y1, road.x2, road.y2, xx, yy)
        jitter = warp * 14.0
        feather = 22.0 if road.kind != "trail" else 16.0
        m = 1.0 - smoothstep(road.width * 0.5 - feather, road.width * 0.5 + jitter, d)
        dirt_mask = np.maximum(dirt_mask, m)

        if road.kind == "road":
            cw = road.width * 0.32
            cm = 1.0 - smoothstep(cw - 18.0, cw + jitter * 0.8, d)
            cobble_mask = np.maximum(cobble_mask, cm)
            # Wheel ruts along the dirt shoulders.
            for side in (-1.0, 1.0):
                rd = np.abs(d - (road.width * 0.40)) * (d < road.width * 0.5)
                rut = 1.0 - smoothstep(2.0, 8.0, rd)
                rut_mask = np.maximum(rut_mask, rut * m)
        elif road.kind == "side":
            # A worn pale strip down the middle.
            rut_mask = np.maximum(rut_mask, (1.0 - smoothstep(3.0, 14.0, d)) * m * 0.55)

    cx, cy, prx, pry = PLAZA
    q = ellipse_mask(cx, cy, prx, pry, 0.0, xx, yy, warp)
    plaza_cobble = 1.0 - smoothstep(0.93, 1.02, q)
    plaza_rim = 1.0 - smoothstep(1.0, 1.16, q)
    cobble_mask = np.maximum(cobble_mask, plaza_cobble)
    dirt_mask = np.maximum(dirt_mask, plaza_rim)

    # Hand-placed colour patches.
    for patch in PATCHES:
        qp = ellipse_mask(patch.x, patch.y, patch.rx, patch.ry,
                          math.radians(patch.angle), xx, yy, warp * 0.5)
        m = 1.0 - smoothstep(0.80, 1.04, qp)
        if patch.kind == "dark_soil":
            dark_mask = np.maximum(dark_mask, m * 0.92)
        elif patch.kind == "purple_moss":
            purple_mask = np.maximum(purple_mask, m * 0.88)
        elif patch.kind == "ruin_moss":
            moss_mask = np.maximum(moss_mask, m * 0.70)
        else:
            dirt_mask = np.maximum(dirt_mask, m * 0.80)

    # Moss creeps over the edges of every cobbled surface.
    edge = np.clip(4.0 * cobble_mask * (1.0 - cobble_mask), 0.0, 1.0)
    moss_break = np.clip((mid - 0.48) * 2.1, 0.0, 1.0) * cobble_mask
    moss_mask = np.maximum(moss_mask, edge * 0.72 + moss_break * 0.34)
    moss_mask = np.clip(moss_mask, 0.0, 1.0)

    print("  layering materials ...")
    # dark soil
    dark_tex = material([seamless(load_tile("dark_soil"))], 302, tint=(0.72, 0.68, 0.72))
    dark_tex *= (0.92 + 0.12 * fine)[..., None]
    a = (dark_mask * (0.55 + 0.25 * mid))[..., None]
    ground = ground * (1.0 - a) + dark_tex * a
    del dark_tex

    # purple moss
    purple_tex = material(moss_cells, 403, tint=(1.06, 0.92, 1.22))
    purple_tex *= (0.92 + 0.12 * fine)[..., None]
    a = (purple_mask * 0.85)[..., None]
    ground = ground * (1.0 - a) + purple_tex * a
    del purple_tex

    # dirt roads
    dirt_tex = material(dirt_cells, 504, tint=(1.30, 1.11, 0.94))
    dirt_tex *= (0.90 + 0.14 * fine + 0.06 * mid)[..., None]
    a = np.clip(dirt_mask * 1.05, 0.0, 1.0)[..., None]
    ground = ground * (1.0 - a) + dirt_tex * a
    del dirt_tex

    # cobblestone
    stone_tex = material(stone_cells, 605, tint=(1.12, 1.13, 1.20))
    stone_tex *= (0.88 + 0.16 * fine + 0.05 * mid)[..., None]
    a = np.clip(cobble_mask * 1.06, 0.0, 1.0)[..., None]
    ground = ground * (1.0 - a) + stone_tex * a
    del stone_tex

    # moss and dark wear on top of the stone
    green_tex = material(grass_cells, 706, tint=(0.72, 0.88, 0.64))
    a = np.clip(moss_mask * 0.55, 0.0, 0.62)[..., None]
    ground = ground * (1.0 - a) + green_tex * a
    del green_tex

    # ruts and dirt shading
    rut = np.clip(rut_mask, 0.0, 1.0)
    ground *= (1.0 - rut * 0.16)[..., None]
    rim = np.clip(4.0 * dirt_mask * (1.0 - dirt_mask), 0.0, 1.0)
    ground *= (1.0 - rim * 0.20)[..., None]

    # low-frequency colour wash and shadow-side tint
    lum = ground.mean(axis=2, keepdims=True)
    shadow_tint = np.array([0.90, 0.92, 1.06], dtype=np.float32)
    ground = ground * (0.93 + 0.11 * coarse[..., None])
    ground = ground * (1.0 - 0.18 * np.clip(1.0 - lum / 90.0, 0.0, 1.0)) + \
        ground * shadow_tint * 0.18 * np.clip(1.0 - lum / 90.0, 0.0, 1.0)

    # Fine static detail is painted with PIL so lines stay crisp.
    print("  painting detail ...")
    img = Image.fromarray(np.clip(ground[:H, :W], 0, 255).astype(np.uint8), "RGB")
    del ground
    draw = ImageDraw.Draw(img, "RGBA")
    rng = random.Random(0xD37A11)

    # detail masks as uint8 PIL images for cheap per-pixel queries
    grass_m = (1.0 - np.clip(dirt_mask + cobble_mask, 0.0, 1.0)).astype(np.float32)
    grass_img = Image.fromarray((grass_m * 255).astype(np.uint8), "L")
    dirt_img = Image.fromarray((np.clip(dirt_mask, 0, 1) * 255).astype(np.uint8), "L")
    cob_img = Image.fromarray((np.clip(cobble_mask, 0, 1) * 255).astype(np.uint8), "L")
    gpx, dpx, cpx = grass_img.load(), dirt_img.load(), cob_img.load()

    def px(x, y, surf):
        if 1 <= x < W - 1 and 1 <= y < H - 1:
            return surf[int(x), int(y)]
        return 0

    # grass tufts
    for _ in range(5200):
        x, y = rng.randrange(2, W - 2), rng.randrange(2, H - 2)
        if gpx[x, y] < 150:
            continue
        base = rng.choice([(39, 54, 35), (47, 64, 40), (57, 75, 45), (67, 86, 51)])
        length = rng.randint(2, 5)
        lean = rng.choice((-1, 0, 1))
        for i in range(length):
            c = tuple(min(255, v + i * 2) for v in base)
            draw.point((x + (lean if i > 1 else 0), y - i), fill=c + (rng.randint(120, 210),))
        if rng.random() < 0.22:
            draw.point((x + rng.choice((-1, 1)), y + 1), fill=(88, 100, 64, 140))

    # tiny purple flowers / spores near moss
    for _ in range(520):
        x, y = rng.randrange(2, W - 2), rng.randrange(2, H - 2)
        if gpx[x, y] > 90 or px(x, y, dpx) > 80:
            if rng.random() < 0.75:
                continue
        col = rng.choice([(111, 86, 156), (139, 108, 188), (168, 142, 210)])
        draw.point((x, y), fill=col + (rng.randint(80, 150),))
        if rng.random() < 0.4:
            draw.point((x, y - 1), fill=col + (90,))

    # pebbles on dirt shoulders
    for _ in range(2400):
        x, y = rng.randrange(2, W - 2), rng.randrange(2, H - 2)
        if dpx[x, y] < 120 or cpx[x, y] > 180:
            continue
        size = rng.choice((1, 1, 2))
        col = rng.choice([(44, 39, 38), (86, 77, 71), (103, 94, 86), (59, 52, 49)])
        draw.ellipse((x, y, x + size, y + size), fill=col + (rng.randint(90, 170),))

    # cobble chips, cracks and highlights
    for _ in range(2200):
        x, y = rng.randrange(2, W - 2), rng.randrange(2, H - 2)
        if cpx[x, y] < 140:
            continue
        if rng.random() < 0.55:
            draw.point((x, y), fill=(112, 107, 104, rng.randint(50, 100)))
        else:
            draw.point((x, y), fill=(28, 25, 26, rng.randint(50, 100)))

    for _ in range(150):
        x, y = rng.randrange(2, W - 2), rng.randrange(2, H - 2)
        if cpx[x, y] < 150:
            continue
        for _ in range(rng.randint(3, 9)):
            draw.point((x, y), fill=(22, 20, 22, rng.randint(110, 180)))
            x += rng.choice((0, 1, 1, -1))
            y += rng.choice((1, 1, 0, -1))

    # occasional puddles with a cold reflected sky
    for _ in range(16):
        x, y = rng.randrange(300, W - 300), rng.randrange(300, H - 300)
        if px(x, y, dpx) < 130 and px(x, y, cpx) < 130:
            continue
        rw, rh = rng.randint(22, 64), rng.randint(6, 16)
        draw.ellipse((x - rw, y - rh, x + rw, y + rh), fill=(30, 30, 44, 85))
        draw.ellipse((x - rw + 4, y - rh + 2, x + rw - 8, y + rh - 2),
                     fill=(48, 46, 68, 55))
        draw.ellipse((x - rw + 10, y - rh + 4, x + rw - 22, y - 1),
                     fill=(91, 82, 130, 30))

    # more moss clumps at the cobble fringe
    for _ in range(1300):
        x, y = rng.randrange(2, W - 2), rng.randrange(2, H - 2)
        if moss_mask[y, x] < 0.18:
            continue
        col = rng.choice([(58, 74, 55), (74, 96, 63), (92, 117, 75), (101, 93, 130)])
        draw.ellipse((x, y, x + rng.randint(1, 4), y + rng.randint(1, 3)),
                     fill=col + (rng.randint(45, 105),))

    img = img.filter(ImageFilter.GaussianBlur(0.22))
    img = img.convert("RGB")

    # -- static shadows ------------------------------------------------------
    print("  baking shadows ...")
    shadow = Image.new("L", (W, H), 0)
    sdraw = ImageDraw.Draw(shadow)
    for prop in ALL_PROPS:
        info = MANIFEST.get(prop.name)
        if not info:
            continue
        sw, sh = info["rect"][2] * prop.scale, info["rect"][3] * prop.scale
        if sh < 24:
            continue
        if prop.name.startswith("house") or prop.name in {"church", "tower_purple"}:
            ew, eh, strength = sw * 0.92, max(14, sh * 0.15), 120
        elif prop.name.startswith("tree"):
            ew, eh, strength = sw * 0.68, max(10, sw * 0.17), 95
        elif prop.name.startswith("fence"):
            ew, eh, strength = sw * 1.00, 10, 60
        else:
            ew, eh, strength = sw * 0.72, max(8, sw * 0.16), 80
        cx = prop.x + sw * 0.10
        cy = prop.y + 2
        sdraw.ellipse((cx - ew / 2, cy - eh / 2, cx + ew / 2, cy + eh / 2),
                      fill=strength)
    shadow = shadow.filter(ImageFilter.GaussianBlur(7.0))
    sa = np.asarray(shadow, dtype=np.float32) / 255.0
    arr = np.asarray(img, dtype=np.float32)
    arr *= (1.0 - np.clip(sa * 0.78, 0.0, 0.62))[..., None]
    # A faint cool bounce inside shadows.
    arr += sa[..., None] * np.array([8.0, 8.0, 17.0], dtype=np.float32)
    # -- static light pools -------------------------------------------------
    # Small additive pools let the runtime draw only the tight flame bloom,
    # which keeps the browser build fast while grounding each lantern in the
    # ground.
    print("  baking light pools ...")
    pools = {
        "lantern_tall": (245, (151, 118, 227), 0.50),
        "lamp_post": (215, (143, 121, 218), 0.44),
        "portal": (310, (168, 112, 244), 0.78),
        "shrine": (175, (127, 150, 216), 0.38),
        "tower_purple": (300, (138, 96, 216), 0.46),
        "church": (360, (119, 139, 198), 0.28),
        "stone_arch": (230, (139, 111, 207), 0.34),
    }
    for prop in ALL_PROPS:
        spec = pools.get(prop.name)
        if not spec:
            continue
        radius, color, strength = spec
        x0 = max(0, int(prop.x - radius))
        x1 = min(W, int(prop.x + radius) + 1)
        y0 = max(0, int(prop.y - radius * 0.82))
        y1 = min(H, int(prop.y + radius * 0.55) + 1)
        if x0 >= x1 or y0 >= y1:
            continue
        lx = np.arange(x0, x1, dtype=np.float32) - prop.x
        ly = (np.arange(y0, y1, dtype=np.float32) - prop.y) * 0.58
        d = np.sqrt(lx[None, :] ** 2 + ly[:, None] ** 2) / radius
        fall = np.clip(1.0 - d, 0.0, 1.0) ** 2.3
        add = np.asarray(color, dtype=np.float32) * (strength * fall[..., None])
        arr[y0:y1, x0:x1] += add
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")

    # -- final grade ---------------------------------------------------------
    arr = np.asarray(img, dtype=np.float32)
    lum = arr.mean(axis=2, keepdims=True)
    arr = arr * (0.92 + 0.14 * coarse[:H, :W, None])
    arr *= np.array([0.97, 0.985, 1.035], dtype=np.float32)
    arr = np.clip((arr - 118.0) * 1.035 + 118.0, 0, 255)
    img = Image.fromarray(arr.astype(np.uint8), "RGB")

    img.resize((640, 480), Image.LANCZOS).save(OUT / "ground_overview.png")
    # Palette-quantise the world texture: differences are sub-perceptual at
    # runtime but the file is roughly half the size for the Pygbag download.
    img.quantize(
        colors=256,
        method=Image.Quantize.MEDIANCUT,
        dither=Image.Dither.NONE,
    ).save(OUT / "ground.png", optimize=True)
    print(f"  wrote {OUT / 'ground.png'}  ({img.width}x{img.height})")


if __name__ == "__main__":
    main()
