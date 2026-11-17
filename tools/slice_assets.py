#!/usr/bin/env python3
"""Slice the ASHEN VEIL concept atlas into reusable game sprites.

The atlas is *not* a uniform grid.  Every rectangle below was inspected
manually (and cross-checked with a zero-shot image classifier) before being
named.  Coordinates refer to assets/environment/ashen_village_atlas.png.

Run from the project root:
    python tools/slice_assets.py
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ATLAS = ROOT / "assets" / "environment" / "ashen_village_atlas.png"
OUT = ROOT / "assets" / "sliced"

# name: (x, y, w, h, category)
RECTS = {
    # ---------------------------------------------------------------- buildings
    "house_timber": (621, 11, 354, 335, "buildings"),
    "house_long": (987, 11, 254, 335, "buildings"),
    "church": (1256, 13, 258, 333, "buildings"),
    "tower_purple": (1522, 6, 137, 348, "buildings"),
    "stone_gate": (611, 361, 247, 179, "buildings"),
    "stone_tower": (885, 366, 128, 171, "buildings"),
    "stone_pillar_tall": (1028, 360, 100, 180, "buildings"),
    "stone_pillar": (865, 371, 26, 101, "buildings"),
    "stone_wall_gate": (141, 522, 181, 102, "buildings"),
    "stone_arch": (954, 784, 200, 133, "buildings"),
    "stone_wall": (1381, 777, 210, 141, "buildings"),
    "statue_great": (1228, 778, 142, 154, "buildings"),
    "statue": (1588, 556, 59, 150, "buildings"),
    "well": (1136, 359, 143, 178, "buildings"),
    "signpost": (1287, 359, 143, 178, "buildings"),
    # -------------------------------------------------------------------- props
    "cart": (1429, 367, 224, 179, "props"),
    "lantern_tall": (1470, 548, 42, 156, "props"),
    "lamp_post": (1233, 591, 36, 102, "props"),
    "portal": (1596, 709, 59, 145, "props"),
    "fence_a": (15, 522, 114, 101, "props"),
    "fence_b": (334, 522, 131, 101, "props"),
    "fence_rail": (15, 631, 113, 65, "props"),
    "fence_rail_b": (143, 639, 132, 44, "props"),
    "fence_gate": (476, 538, 226, 81, "props"),
    "barrel_a": (778, 548, 54, 72, "props"),
    "barrel_b": (848, 564, 55, 56, "props"),
    "barrel_c": (729, 630, 51, 75, "props"),
    "barrel_d": (796, 632, 46, 73, "props"),
    "barrel_e": (865, 707, 62, 69, "props"),
    "barrel_f": (1147, 547, 59, 54, "props"),
    "crate_a": (860, 634, 77, 61, "props"),
    "crate_b": (952, 630, 46, 66, "props"),
    "crate_c": (716, 551, 46, 69, "props"),
    "crate_d": (1011, 629, 60, 67, "props"),
    "woodpile": (651, 631, 62, 70, "props"),
    "logs": (387, 631, 79, 69, "props"),
    "bones": (1262, 715, 77, 52, "props"),
    "skull": (1353, 735, 40, 31, "props"),
    "skull_b": (759, 791, 43, 40, "props"),
    "gravestone_a": (1051, 702, 58, 73, "props"),
    "gravestone_b": (1123, 699, 56, 66, "props"),
    "gravestone_c": (1193, 695, 49, 83, "props"),
    "gravestone_d": (1007, 717, 29, 51, "props"),
    "grave_cross": (1378, 549, 49, 146, "props"),
    "grave_cross_b": (383, 359, 48, 70, "props"),
    "rock_a": (814, 848, 82, 60, "props"),
    "rock_b": (820, 784, 50, 48, "props"),
    "rock_c": (14, 446, 81, 69, "props"),
    "rock_d": (104, 446, 88, 65, "props"),
    "rock_e": (424, 290, 66, 65, "props"),
    "rubble_a": (695, 848, 97, 76, "props"),
    "rubble_b": (308, 434, 119, 83, "props"),
    "rubble_c": (289, 636, 77, 66, "props"),
    "well_small": (996, 551, 55, 64, "props"),
    "shrine": (715, 723, 46, 42, "props"),
    # --------------------------------------------------------------- vegetation
    "tree_dead_big": (12, 688, 295, 242, "vegetation"),
    "tree_dead": (297, 707, 146, 219, "vegetation"),
    "tree_dead_tall": (428, 630, 208, 293, "vegetation"),
    "tree_dead_b": (564, 717, 132, 156, "vegetation"),
    "tree_dead_small": (13, 358, 55, 78, "vegetation"),
    "tree_dead_small_b": (434, 360, 48, 69, "vegetation"),
    "bush_a": (13, 289, 97, 67, "vegetation"),
    "bush_b": (116, 292, 86, 62, "vegetation"),
    "bush_c": (206, 290, 94, 66, "vegetation"),
    "bush_d": (171, 360, 106, 70, "vegetation"),
    "bush_e": (284, 360, 94, 69, "vegetation"),
    "bush_f": (198, 435, 101, 82, "vegetation"),
    "bush_g": (434, 435, 87, 82, "vegetation"),
    "bush_h": (779, 715, 64, 51, "vegetation"),
    "bush_i": (531, 448, 29, 59, "vegetation"),
    "bush_j": (569, 448, 31, 56, "vegetation"),
    "bush_k": (494, 291, 94, 63, "vegetation"),
    "plant_a": (399, 888, 53, 38, "vegetation"),
    "plant_b": (540, 887, 40, 38, "vegetation"),
    "plant_c": (611, 878, 67, 47, "vegetation"),
    "plant_d": (267, 839, 59, 67, "vegetation"),
    # ----------------------------------------------------------------- ground
    "grass": (13, 10, 96, 96, "ground"),
    "dirt": (136, 136, 96, 96, "ground"),
    "dirt_b": (192, 192, 96, 96, "ground"),
    "stone": (288, 248, 96, 96, "ground"),
    "stone_b": (296, 256, 96, 96, "ground"),
    "moss_purple": (384, 208, 96, 96, "ground"),
    "moss_purple_b": (392, 216, 96, 96, "ground"),
    "purple_soil": (480, 120, 96, 96, "ground"),
    "dark_soil": (208, 216, 96, 96, "ground"),
}


def clean_alpha(image: Image.Image) -> Image.Image:
    """Remove the low-alpha haze around the concept atlas sprites."""
    image = image.convert("RGBA")
    px = image.load()
    for y in range(image.height):
        for x in range(image.width):
            r, g, b, a = px[x, y]
            if a < 10:
                px[x, y] = (0, 0, 0, 0)
            elif a < 110 and max(r, g, b) < 20:
                # Almost pure dark fringe; keep it out of the way.
                px[x, y] = (0, 0, 0, 0)
    return image


def make_opaque_tile(image: Image.Image) -> Image.Image:
    """Composite a ground sample over its own average colour.

    The concept atlas uses a little translucent noise.  Ground tiles must be
    perfectly opaque or the tiled world shows pin-holes.
    """
    image = image.convert("RGBA")
    px = list(image.getdata())
    solid = [p for p in px if p[3] > 160]
    if not solid:
        solid = px
    base = tuple(sum(p[i] for p in solid) // len(solid) for i in range(3))
    bg = Image.new("RGBA", image.size, base + (255,))
    bg.alpha_composite(image)
    return bg.convert("RGB")


def main() -> None:
    atlas = Image.open(ATLAS).convert("RGBA")
    manifest = {}
    for name, (x, y, w, h, category) in RECTS.items():
        if x + w > atlas.width or y + h > atlas.height:
            raise SystemExit(f"{name}: rectangle outside atlas")
        crop = atlas.crop((x, y, x + w, y + h))
        folder = OUT / category
        folder.mkdir(parents=True, exist_ok=True)
        if category == "ground":
            tile = make_opaque_tile(crop)
            tile.save(folder / f"{name}.png")
        else:
            crop = clean_alpha(crop)
            crop.save(folder / f"{name}.png")
        manifest[name] = {
            "file": str((folder / f"{name}.png").relative_to(ROOT)).replace("\\", "/"),
            "rect": [x, y, w, h],
            "category": category,
        }
        print(f"  {name:22s} {w:3d}x{h:3d}  [{category}]")

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nSliced {len(manifest)} sprites into {OUT}")


if __name__ == "__main__":
    main()
