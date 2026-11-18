#!/usr/bin/env python3
"""Build the three Phase 8 NPC idle sheets from the existing Wanderer sheet.

The silhouettes and pixel shading come from the shipped player spritesheet;
each survivor gets a distinct palette and a few hand-placed pixel accessories.
Run from the project root:

    python tools/generate_npc_sprites.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "characters" / "ashen_veil_player_spritesheet.png"
OUT = ROOT / "assets" / "npcs"
FRAME = 64
ROWS = ("down", "up", "left", "right")


def tint_pixel(r: int, g: int, b: int, a: int, palette: str) -> tuple[int, int, int, int]:
    if a == 0:
        return (0, 0, 0, 0)
    # Preserve skin and metal highlights; only the cloak's cool purples move.
    if b > r + 4 or (b > g + 6 and r < 170):
        if palette == "merchant":
            r, g, b = int(min(255, r * 1.34)), int(min(255, g * 1.04)), int(b * 0.60)
        elif palette == "blacksmith":
            r, g, b = int(r * 0.92), int(min(255, g * 1.12)), int(min(255, b * 0.96))
        else:
            r, g, b = int(r * 0.82), int(g * 0.68), int(min(255, b * 1.24))
    return (r, g, b, a)


def recolor(frame: Image.Image, palette: str) -> Image.Image:
    out = Image.new("RGBA", frame.size)
    out.putdata([tint_pixel(*pixel, palette) for pixel in frame.getdata()])
    return out


def _hat(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int],
         fill: tuple[int, int, int], edge: tuple[int, int, int]) -> None:
    x0, y0, x1, y1 = box
    draw.rectangle((x0, y0, x1, y1), fill=edge)
    draw.rectangle((x0 + 1, y0 + 1, x1 - 1, y1), fill=fill)
    draw.line((x0 + 1, y1, x1 - 1, y1), fill=edge, width=1)


def decorate(frame: Image.Image, palette: str, row: int, phase: int) -> Image.Image:
    draw = ImageDraw.Draw(frame)
    bob = phase % 2
    if palette == "merchant":
        hats = ((20, 17, 43, 23), (21, 17, 44, 23),
                (23, 17, 46, 23), (17, 17, 40, 23))
        _hat(draw, hats[row], (116, 82, 48), (48, 32, 24))
        draw.rectangle((20, 22, 43, 23), fill=(168, 122, 64))
        if row in (0, 2):
            draw.rectangle((40, 35 + bob, 46, 42 + bob), fill=(64, 42, 28))
            draw.rectangle((41, 36 + bob, 45, 39 + bob), fill=(212, 166, 72))
        else:
            draw.rectangle((18, 35 + bob, 24, 42 + bob), fill=(64, 42, 28))
    elif palette == "blacksmith":
        draw.rectangle((23, 32, 41, 50), fill=(74, 54, 44))
        draw.rectangle((24, 33, 40, 49), outline=(132, 92, 62), width=1)
        draw.line((26, 38, 38, 38), fill=(176, 120, 70), width=1)
        handle_x = 43 if row in (0, 2) else 18
        draw.line((handle_x, 30 + bob, handle_x, 43 + bob), fill=(92, 62, 40))
        draw.rectangle((handle_x - 4, 27 + bob, handle_x + 4, 31 + bob),
                       fill=(138, 146, 156), outline=(48, 50, 58), width=1)
    else:
        hoods = ((19, 17, 45, 29), (20, 17, 46, 29),
                 (22, 17, 48, 29), (16, 17, 42, 29))
        _hat(draw, hoods[row], (36, 22, 58), (96, 62, 142))
        draw.rectangle((23, 27, 41, 30), fill=(12, 9, 20))
        draw.point((30, 27), fill=(216, 176, 255))
        draw.point((34, 27), fill=(216, 176, 255))
        draw.rectangle((21, 34, 43, 52), fill=(34, 22, 54))
        draw.rectangle((22, 35, 42, 51), outline=(106, 72, 152), width=1)
        staff_x = 46 if row in (0, 2) else 15
        draw.line((staff_x, 24 + bob, staff_x, 51 + bob), fill=(82, 58, 104))
        draw.ellipse((staff_x - 3, 19 + bob, staff_x + 3, 25 + bob),
                     fill=(168, 104, 244), outline=(224, 186, 255), width=1)
    return frame


def build(palette: str) -> None:
    sheet = Image.new("RGBA", (FRAME * 4, FRAME * 4))
    for row in range(4):
        for phase in range(4):
            crop = Image.open(SOURCE).convert("RGBA").crop(
                (phase * FRAME, row * FRAME,
                 (phase + 1) * FRAME, (row + 1) * FRAME)
            )
            frame = decorate(recolor(crop, palette), palette, row, phase)
            sheet.paste(frame, (phase * FRAME, row * FRAME))
    path = OUT / f"{palette}.png"
    sheet.save(path)
    print(f"  {path.relative_to(ROOT)}  {sheet.size[0]}x{sheet.size[1]}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for palette in ("merchant", "blacksmith", "veil_keeper"):
        build(palette)


if __name__ == "__main__":
    main()
