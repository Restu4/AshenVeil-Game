#!/usr/bin/env python3
"""ASHEN VEIL - Fallen Knight sprite sheet generator.

The village asset pack contains no enemy artwork, so the Fallen Knight is
generated here in the same 64x64, four-direction pixel-art language as the
player sheet.  The output is a normal ``CharacterAnimator`` sheet:

    assets/enemies/fallen_knight.png
    assets/enemies/fallen_knight.json

Run from the project root:

    python tools/generate_fallen_knight.py
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

FW = FH = 64
COLS = 8
FOOT_Y = 54

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets" / "enemies"


def H(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


# ---------------------------------------------------------------------------
# Palette - rusted steel, dead cloth and the same cold purple as the village.
# ---------------------------------------------------------------------------
OUT = H("0a090d")
STEEL_0 = H("1a1922")
STEEL_1 = H("2b2a36")
STEEL_2 = H("3f3e4f")
STEEL_3 = H("5b5a70")
STEEL_4 = H("7d7c94")
STEEL_5 = H("a6a4ba")
RUST_0 = H("3b2620")
RUST_1 = H("5c3a2c")
RUST_2 = H("80543a")
RUST_3 = H("a06f47")
CLOTH_0 = H("15121d")
CLOTH_1 = H("241f31")
CLOTH_2 = H("372e49")
CLOTH_3 = H("4b3f63")
TRIM = H("6b5a8c")
PURPLE_0 = H("3a2360")
PURPLE_1 = H("7b49c8")
PURPLE_2 = H("b078ff")
PURPLE_3 = H("efe0ff")
BONE = H("b3aa9c")
BONE_D = H("776f64")
LEATHER = H("2e241d")


class Canvas:
    def __init__(self) -> None:
        self.image = Image.new("RGBA", (FW, FH), (0, 0, 0, 0))
        self.draw = ImageDraw.Draw(self.image)

    def px(self, x, y, color, alpha: int = 255) -> None:
        x, y = int(round(x)), int(round(y))
        if 0 <= x < FW and 0 <= y < FH:
            self.image.putpixel((x, y), (*color, alpha))

    def rect(self, x0, y0, x1, y1, color, alpha: int = 255) -> None:
        x0, y0 = int(round(x0)), int(round(y0))
        x1, y1 = int(round(x1)), int(round(y1))
        if x1 < x0:
            x0, x1 = x1, x0
        if y1 < y0:
            y0, y1 = y1, y0
        self.draw.rectangle((x0, y0, x1, y1), fill=(*color, alpha))

    def poly(self, points, color, alpha: int = 255) -> None:
        self.draw.polygon([(int(round(x)), int(round(y))) for x, y in points],
                          fill=(*color, alpha))

    def ellipse(self, x0, y0, x1, y1, color, alpha: int = 255) -> None:
        self.draw.ellipse((int(round(x0)), int(round(y0)),
                           int(round(x1)), int(round(y1))), fill=(*color, alpha))


def blade(cv: Canvas, pivot, angle_deg: float, length: float,
          scale: float = 1.0) -> None:
    """Draw a heavy, rust-pitted longsword from a hand pivot."""
    a = math.radians(angle_deg)
    dx, dy = math.cos(a), math.sin(a)
    px, py = pivot
    bx, by = -dy, dx
    half = max(1.0, 2.0 * scale)
    tip = (px + dx * length, py + dy * length)
    base = (px + dx * 4.0 * scale, py + dy * 4.0 * scale)

    # Grip and pommel behind the hand.
    grip_end = (px - dx * 5.0, py - dy * 5.0)
    cv.poly([(px + bx * 1.6, py + by * 1.6),
             (grip_end[0] + bx * 1.6, grip_end[1] + by * 1.6),
             (grip_end[0] - bx * 1.6, grip_end[1] - by * 1.6),
             (px - bx * 1.6, py - by * 1.6)], LEATHER)
    cv.px(grip_end[0], grip_end[1], BONE_D)
    cv.px(grip_end[0] + bx, grip_end[1] + by, BONE_D)

    # Crossguard, slightly swept.
    guard_a = (px + bx * 4.0, py + by * 4.0)
    guard_b = (px - bx * 3.5, py - by * 3.5)
    cv.poly([(guard_a[0], guard_a[1] - 1),
             (guard_b[0], guard_b[1] - 1),
             (guard_b[0], guard_b[1] + 1),
             (guard_a[0], guard_a[1] + 1)], RUST_2)
    cv.px(guard_a[0], guard_a[1], RUST_3)
    cv.px(guard_b[0], guard_b[1], RUST_1)

    # Blade body with a pale edge and dark fuller.
    cv.poly([(base[0] + bx * half, base[1] + by * half),
             (tip[0] + bx * 0.6, tip[1] + by * 0.6),
             (tip[0] - bx * 0.6, tip[1] - by * 0.6),
             (base[0] - bx * half, base[1] - by * half)], STEEL_3)
    cv.poly([(base[0] + bx * half, base[1] + by * half),
             (tip[0] + bx * 0.6, tip[1] + by * 0.6),
             (tip[0], tip[1]),
             (base[0], base[1])], STEEL_4)
    cv.poly([(base[0], base[1]),
             (tip[0], tip[1]),
             (tip[0] - bx * 0.6, tip[1] - by * 0.6),
             (base[0] - bx * half, base[1] - by * half)], STEEL_2)
    # Fuller line and rust pits.
    for t in (0.28, 0.46, 0.64, 0.8):
        x = base[0] + (tip[0] - base[0]) * t
        y = base[1] + (tip[1] - base[1]) * t
        cv.px(x, y, STEEL_1)
    for t in (0.36, 0.58, 0.72):
        x = base[0] + (tip[0] - base[0]) * t + bx * 0.9
        y = base[1] + (tip[1] - base[1]) * t + by * 0.9
        cv.px(x, y, RUST_1)


def rust(cv: Canvas, points, rng: random.Random, color=RUST_1) -> None:
    for x, y in points:
        cv.px(x, y, color)
        if rng.random() < 0.35:
            cv.px(x + 1, y, RUST_2)


# ---------------------------------------------------------------------------
# Body construction.  Directions are drawn for down / up / left, then the
# left frames are mirrored to produce right.
# ---------------------------------------------------------------------------
def draw_knight(cv: Canvas, direction: str, *, bob: int = 0, leg: float = 0.0,
                sway: float = 0.0, sword_angle: float = 165.0,
                lean: int = 0, sink: int = 0, hurt: int = 0,
                eye_glow: int = 1, dust: float = 0.0) -> None:
    seed = sum(ord(c) for c in direction) * 131 + int(leg * 7) * 17
    seed += int(sword_angle) * 3 + int(sink) * 29 + int(hurt) * 11
    rng = random.Random(seed & 0xFFFF)
    y = bob + sink
    back = direction == "up"
    side = direction in {"left", "right"}
    x_off = lean - hurt
    y_off = y
    hand = (43, 40) if direction != "left" else (23, 40)
    hand = (hand[0] + x_off, hand[1] + y_off)
    cape_flare = int(round(sway))
    blade_len = 19.0 if direction != "down" else 20.0

    # ---- tattered cloak ---------------------------------------------------
    if back:
        cv.poly([(23 + x_off, 24 + y_off), (41 + x_off, 24 + y_off),
                 (46 + cape_flare + x_off, 50 + y_off),
                 (41 + x_off, 47 + y_off), (38 + x_off, 53 + y_off),
                 (34 + x_off, 48 + y_off), (30 + x_off, 52 + y_off),
                 (26 + x_off, 47 + y_off), (18 + cape_flare + x_off, 51 + y_off)],
                CLOTH_1)
        cv.poly([(27 + x_off, 26 + y_off), (37 + x_off, 26 + y_off),
                 (38 + x_off, 46 + y_off), (32 + x_off, 49 + y_off),
                 (26 + x_off, 46 + y_off)], CLOTH_2)
        cv.px(32 + x_off, 30 + y_off, TRIM)
        cv.px(32 + x_off, 33 + y_off, TRIM)
        cv.px(32 + x_off, 40 + y_off, PURPLE_1)
        cv.px(33 + x_off, 41 + y_off, PURPLE_0)
    else:
        spread = 3 if side else 0
        cv.poly([(24 + x_off - spread, 25 + y_off),
                 (40 + x_off + spread, 25 + y_off),
                 (44 + cape_flare + x_off + spread, 49 + y_off),
                 (39 + x_off, 46 + y_off), (36 + x_off, 52 + y_off),
                 (32 + x_off, 47 + y_off), (29 + x_off, 51 + y_off),
                 (26 + x_off, 46 + y_off), (20 + cape_flare + x_off - spread, 50 + y_off)],
                CLOTH_1)
        cv.poly([(27 + x_off, 27 + y_off), (38 + x_off, 27 + y_off),
                 (39 + x_off, 44 + y_off), (31 + x_off, 46 + y_off),
                 (24 + x_off, 43 + y_off)], CLOTH_0)

    # ---- legs / greaves ---------------------------------------------------
    step = int(round(leg))
    lift_r = max(0, -step)
    legs = ((28, step, 0), (36, -step, lift_r))
    for lx, dx, lift in legs:
        lx += x_off
        ly = y_off
        cv.rect(lx - 2, 40 + ly, lx + 2, 50 + ly - lift, STEEL_2)
        cv.rect(lx - 2, 40 + ly, lx + 2, 43 + ly - lift, STEEL_3)
        cv.rect(lx - 2, 44 + ly, lx + 2, 45 + ly - lift, STEEL_1)
        cv.rect(lx - 3 + (dx // 2), 50 + ly - lift, lx + 3 + (dx // 2),
                53 + ly - lift, STEEL_1)
        cv.rect(lx - 3 + (dx // 2), 52 + ly - lift, lx + 3 + (dx // 2),
                53 + ly - lift, STEEL_0)
    rust(cv, [(27 + x_off, 45 + y_off), (38 + x_off, 47 + y_off)], rng)

    # ---- tabard / belt ----------------------------------------------------
    tab_h = 10 if not back else 9
    cv.poly([(28 + x_off, 34 + y_off), (37 + x_off, 34 + y_off),
             (38 + x_off, 44 + y_off + tab_h), (32 + x_off, 43 + y_off + tab_h),
             (26 + x_off, 44 + y_off + tab_h)], CLOTH_2)
    cv.poly([(30 + x_off, 43 + y_off + tab_h), (32 + x_off, 41 + y_off + tab_h),
             (34 + x_off, 44 + y_off + tab_h), (33 + x_off, 47 + y_off + tab_h),
             (29 + x_off, 46 + y_off + tab_h)], CLOTH_3)
    cv.rect(25 + x_off, 36 + y_off, 39 + x_off, 38 + y_off, LEATHER)
    cv.rect(30 + x_off, 36 + y_off, 34 + x_off, 38 + y_off, BONE_D)

    # ---- torso ------------------------------------------------------------
    cv.poly([(24 + x_off, 26 + y_off), (40 + x_off, 26 + y_off),
             (39 + x_off, 39 + y_off), (25 + x_off, 39 + y_off)], STEEL_2)
    cv.poly([(26 + x_off, 27 + y_off), (38 + x_off, 27 + y_off),
             (38 + x_off, 31 + y_off), (26 + x_off, 31 + y_off)], STEEL_3)
    cv.rect(31 + x_off, 27 + y_off, 33 + x_off, 38 + y_off, STEEL_1)
    cv.rect(31 + x_off, 27 + y_off, 32 + x_off, 31 + y_off, STEEL_2)
    cv.rect(25 + x_off, 38 + y_off, 39 + x_off, 39 + y_off, STEEL_1)
    rust(cv, [(27 + x_off, 33 + y_off), (37 + x_off, 29 + y_off),
              (35 + x_off, 36 + y_off), (29 + x_off, 30 + y_off)], rng)

    # ---- pauldrons --------------------------------------------------------
    for px0, px1 in ((19, 28), (36, 45)):
        cv.ellipse(px0 + x_off, 24 + y_off, px1 + x_off, 34 + y_off, STEEL_1)
        cv.ellipse(px0 + 1 + x_off, 24 + y_off, px1 - 1 + x_off, 31 + y_off, STEEL_2)
        cv.rect(px0 + 2 + x_off, 25 + y_off, px1 - 2 + x_off, 26 + y_off, STEEL_4)
        cv.rect(px0 + 2 + x_off, 30 + y_off, px1 - 2 + x_off, 31 + y_off, STEEL_1)
        rust(cv, [(px0 + 3 + x_off, 28 + y_off), (px1 - 3 + x_off, 27 + y_off),
                  (px1 - 4 + x_off, 30 + y_off)], rng, RUST_2)

    # ---- arms -------------------------------------------------------------
    arm_swing = int(round(leg * 0.6))
    if back:
        cv.rect(21 + x_off, 31 + y_off, 25 + x_off, 39 + y_off + arm_swing, STEEL_2)
        cv.rect(39 + x_off, 31 + y_off, 43 + x_off, 39 + y_off - arm_swing, STEEL_2)
    elif side:
        cv.rect(31 + x_off, 31 + y_off, 36 + x_off, 39 + y_off + arm_swing, STEEL_2)
        cv.rect(22 + x_off, 32 + y_off, 26 + x_off, 38 + y_off, STEEL_1)
    else:
        cv.rect(20 + x_off, 31 + y_off, 25 + x_off, 40 + y_off + arm_swing, STEEL_2)
        cv.rect(39 + x_off, 31 + y_off, 43 + x_off, 40 + y_off - arm_swing, STEEL_2)
    cv.rect(hand[0] - 2, hand[1] - 1, hand[0] + 2, hand[1] + 3, LEATHER)

    # ---- sword ------------------------------------------------------------
    if back:
        blade(cv, hand, sword_angle, blade_len, 1.0)

    # ---- helmet -----------------------------------------------------------
    hx = x_off
    hy = y_off
    cv.ellipse(25 + hx, 11 + hy, 39 + hx, 26 + hy, STEEL_1)
    cv.rect(26 + hx, 15 + hy, 38 + hx, 24 + hy, STEEL_2)
    cv.rect(27 + hx, 12 + hy, 37 + hx, 14 + hy, STEEL_3)
    cv.rect(27 + hx, 12 + hy, 30 + hx, 13 + hy, STEEL_4)
    if direction == "up":
        cv.rect(27 + hx, 17 + hy, 37 + hx, 22 + hy, STEEL_1)
        cv.rect(26 + hx, 23 + hy, 38 + hx, 25 + hy, STEEL_1)
        cv.rect(31 + hx, 13 + hy, 33 + hx, 24 + hy, STEEL_0)
        rust(cv, [(28 + hx, 16 + hy), (36 + hx, 19 + hy), (34 + hx, 23 + hy)],
             rng)
    elif direction == "left":
        cv.rect(24 + hx, 18 + hy, 34 + hx, 22 + hy, STEEL_0)
        cv.rect(25 + hx, 18 + hy, 29 + hx, 19 + hy, H("050407"))
        # One cold eye set deep in the visor.
        cv.px(26 + hx, 20 + hy, PURPLE_1)
        cv.px(27 + hx, 20 + hy, PURPLE_2)
        cv.px(26 + hx, 21 + hy, PURPLE_0)
        if eye_glow:
            cv.px(27 + hx, 19 + hy, PURPLE_2)
        cv.rect(36 + hx, 17 + hy, 40 + hx, 23 + hy, STEEL_2)
        cv.rect(31 + hx, 24 + hy, 38 + hx, 25 + hy, STEEL_1)
        rust(cv, [(33 + hx, 16 + hy), (29 + hx, 24 + hy)], rng)
        cv.poly([(28 + hx, 25 + hy), (36 + hx, 25 + hy),
                 (39 + hx, 30 + hy), (25 + hx, 30 + hy)], STEEL_1)
    else:
        cv.rect(25 + hx, 18 + hy, 39 + hx, 22 + hy, STEEL_0)
        cv.rect(26 + hx, 19 + hy, 38 + hx, 20 + hy, H("050407"))
        for ex in (28, 34):
            cv.px(ex + hx, 19 + hy, PURPLE_1)
            cv.px(ex + 1 + hx, 19 + hy, PURPLE_2)
            cv.px(ex + hx, 20 + hy, PURPLE_0)
            if eye_glow:
                cv.px(ex + 1 + hx, 18 + hy, PURPLE_2)
                cv.px(ex + 2 + hx, 20 + hy, PURPLE_0)
        cv.rect(30 + hx, 21 + hy, 34 + hx, 22 + hy, STEEL_1)
        cv.rect(26 + hx, 23 + hy, 38 + hx, 24 + hy, STEEL_1)
        cv.rect(28 + hx, 24 + hy, 36 + hx, 25 + hy, STEEL_2)
        rust(cv, [(27 + hx, 14 + hy), (36 + hx, 15 + hy), (30 + hx, 23 + hy)],
             rng)

    # Gorget under the helmet.
    cv.rect(27 + x_off, 25 + y_off, 37 + x_off, 27 + y_off, STEEL_1)
    cv.px(30 + x_off, 26 + y_off, RUST_1)
    cv.px(35 + x_off, 26 + y_off, RUST_1)

    if not back:
        blade(cv, hand, sword_angle, blade_len, 1.0)

    # ---- death dust -------------------------------------------------------
    if dust > 0.0:
        for i in range(int(6 + 10 * dust)):
            r = random.Random(0xA5 + i * 17)
            dx = r.uniform(-15, 15)
            dy = -r.uniform(2, 26) * dust
            cv.px(32 + dx, 40 + dy, PURPLE_2 if i % 3 else PURPLE_3)
        for i in range(4):
            r = random.Random(0x77 + i)
            cv.px(32 + r.uniform(-18, 18), 30 + r.uniform(-10, 12),
                  CLOTH_3)


# ---------------------------------------------------------------------------
# Animation poses.
# ---------------------------------------------------------------------------
IDLE_SWORD = {"down": 68.0, "up": -66.0, "left": 162.0}
WALK_SWORD = {"down": 72.0, "up": -62.0, "left": 158.0}


def idle_frame(direction: str, index: int, count: int = 4) -> Image.Image:
    cv = Canvas()
    phase = index / count * math.tau
    bob = (0, -1, 0, 1)[index % 4]
    sway = math.sin(phase) * 1.2
    sword_angle = IDLE_SWORD[direction] + math.sin(phase + 0.7) * 2.0
    draw_knight(cv, direction, bob=bob, sway=sway, sword_angle=sword_angle,
                eye_glow=(1 if index % 2 == 0 else 0))
    return cv.image


def walk_frame(direction: str, index: int, count: int = 6) -> Image.Image:
    cv = Canvas()
    phase = index / count * math.tau
    leg = math.sin(phase) * 2.2
    bob = -1 if abs(math.sin(phase)) > 0.72 else 0
    sword_angle = WALK_SWORD[direction] + math.sin(phase) * 4.0
    draw_knight(cv, direction, bob=bob, leg=leg, sway=math.sin(phase) * 1.6,
                sword_angle=sword_angle, eye_glow=(1 if index % 3 else 0))
    return cv.image


ATTACK_KEYS = {
    # windup angle, strike angle, pivot lean
    "down": (-52.0, 118.0),
    "up": (18.0, 206.0),
    "left": (262.0, 118.0),
}


def attack_frame(direction: str, index: int, count: int = 6) -> Image.Image:
    cv = Canvas()
    windup, strike = ATTACK_KEYS[direction]
    # 0-1 wind up, 2-3 sweep, 4 follow-through, 5 recover.
    if index <= 1:
        t = (index + 1) / 3.0
        angle = _lerp(IDLE_SWORD[direction], windup, t)
        lean = -1 if index else 0
    elif index <= 3:
        t = (index - 2) / 2.0
        angle = _lerp(windup, strike, t * t * (3 - 2 * t))
        lean = 2 if index >= 3 else 1
    else:
        t = (index - 4) / 2.0
        angle = _lerp(strike, IDLE_SWORD[direction], t)
        lean = 1 - int(t * 2)
    bob = -1 if index in (1, 2) else 0
    draw_knight(cv, direction, bob=bob, sway=(1 if index in (2, 3) else 0),
                sword_angle=angle, lean=lean, leg=(1.0 if index == 3 else 0.0),
                eye_glow=1)
    return cv.image


def hurt_frame(direction: str, index: int, count: int = 3) -> Image.Image:
    cv = Canvas()
    hurt = (2, 3, 1)[index % 3]
    bob = (-1, 0, 0)[index % 3]
    draw_knight(cv, direction, bob=bob, hurt=hurt,
                sword_angle=IDLE_SWORD[direction] - 16.0,
                sway=-1.0, eye_glow=1)
    return cv.image


def death_frame(direction: str, index: int, count: int = 8) -> Image.Image:
    cv = Canvas()
    # Buckle, kneel, then dissolve into ash.
    sink = min(5, index)
    dust = max(0.0, (index - 3) / 4.0)
    draw_knight(cv, direction, sink=sink, hurt=min(3, index),
                sword_angle=IDLE_SWORD[direction] + 18.0 * index / count,
                sway=-2.0, eye_glow=(1 if index < 4 else 0), dust=dust)
    image = cv.image
    if index >= 4:
        alpha = (220, 160, 95, 28)[min(3, index - 4)]
        if alpha < 255:
            image.putalpha(image.getchannel("A").point(
                lambda a, alpha=alpha: a * alpha // 255))
    return image


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


# ---------------------------------------------------------------------------
# Sheet assembly.
# ---------------------------------------------------------------------------
ROWS = [
    ("idle_down", 0, 4, 5, True, idle_frame, "down"),
    ("idle_up", 1, 4, 5, True, idle_frame, "up"),
    ("idle_left", 2, 4, 5, True, idle_frame, "left"),
    ("idle_right", 3, 4, 5, True, idle_frame, "right"),
    ("walk_down", 4, 6, 8, True, walk_frame, "down"),
    ("walk_up", 5, 6, 8, True, walk_frame, "up"),
    ("walk_left", 6, 6, 8, True, walk_frame, "left"),
    ("walk_right", 7, 6, 8, True, walk_frame, "right"),
    ("attack_down", 8, 6, 14, False, attack_frame, "down"),
    ("attack_up", 9, 6, 14, False, attack_frame, "up"),
    ("attack_left", 10, 6, 14, False, attack_frame, "left"),
    ("attack_right", 11, 6, 14, False, attack_frame, "right"),
    ("hurt_down", 12, 3, 10, False, hurt_frame, "down"),
    ("hurt_up", 13, 3, 10, False, hurt_frame, "up"),
    ("hurt_left", 14, 3, 10, False, hurt_frame, "left"),
    ("hurt_right", 15, 3, 10, False, hurt_frame, "right"),
    # Death is drawn once; CharacterAnimator falls back to this row.
    ("death_down", 16, 8, 8, False, death_frame, "down"),
]


def build() -> tuple[Image.Image, dict]:
    height = len(ROWS) * FH
    sheet = Image.new("RGBA", (COLS * FW, height), (0, 0, 0, 0))
    rows = []
    for name, row, frames, fps, loop, factory, facing in ROWS:
        for col in range(frames):
            base = facing
            if base == "right":
                frame = ImageOps.mirror(factory("left", col, frames))
            else:
                frame = factory(base, col, frames)
            # The sheet's foot line is y=52, like the player; lift the art
            # two pixels so the boots meet the ground anchor.
            lifted = Image.new("RGBA", (FW, FH), (0, 0, 0, 0))
            lifted.alpha_composite(frame, (0, -2))
            sheet.paste(lifted, (col * FW, row * FH))
        rows.append({"name": name, "row": row, "frames": frames,
                     "fps": fps, "loop": loop})
    metadata = {"frame_size": [FW, FH], "columns": COLS, "rows": rows}
    return sheet, metadata


def contact_sheet(sheet: Image.Image) -> Image.Image:
    scale = 3
    preview = sheet.resize((sheet.width * scale, sheet.height * scale),
                          Image.NEAREST)
    bg = Image.new("RGBA", (preview.width + 24, preview.height + 24),
                   (12, 10, 16, 255))
    bg.alpha_composite(preview, (12, 12))
    draw = ImageDraw.Draw(bg)
    for i in range(len(ROWS) + 1):
        draw.line([(12, 12 + i * FH * scale),
                   (12 + sheet.width * scale, 12 + i * FH * scale)],
                  fill=(58, 48, 70, 255), width=1)
    return bg


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sheet, metadata = build()
    sheet.save(OUT_DIR / "fallen_knight.png")
    (OUT_DIR / "fallen_knight.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    shots = ROOT / "screenshots"
    shots.mkdir(exist_ok=True)
    contact_sheet(sheet).save(shots / "fallen_knight_contact.png")
    print(f"wrote {OUT_DIR / 'fallen_knight.png'} ({sheet.width}x{sheet.height})")
    print(f"wrote {OUT_DIR / 'fallen_knight.json'}")
    print(f"wrote {shots / 'fallen_knight_contact.png'}")


if __name__ == "__main__":
    main()
