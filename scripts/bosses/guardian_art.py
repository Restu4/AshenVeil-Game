"""Procedural pixel art for THE HOLLOW GUARDIAN.

The guardian is a hulking, horned knight with a cracked black plate, a purple
furnace inside the chest and an oversized greatsword.  It is drawn once per
(action, frame, facing) into a small surface, then nearest-neighbour scaled, so
the browser pays one cached blit per frame instead of dozens of polygons.

The silhouette is intentionally much larger and heavier than the 64 px enemy
frames: wide pauldrons, tall horns, a cape that reaches the floor and a blade
longer than the knight is tall.
"""
from __future__ import annotations

import math

import pygame

FRAME = 112
FOOT_LINE = 96

ANIMATIONS: dict[str, tuple[int, float, bool]] = {
    "idle": (4, 4.5, True),
    "walk": (6, 7.0, True),
    "windup": (5, 9.0, False),
    "sweep": (4, 15.0, False),
    "slam": (5, 10.0, False),
    "combo": (6, 15.0, False),
    "wave": (5, 11.0, False),
    "charge": (5, 8.0, False),
    "hurt": (3, 10.0, False),
    "death": (7, 6.0, False),
    "roar": (4, 5.5, False),
    "victory": (5, 4.5, True),
}

CACHE: dict[tuple[str, int, str], pygame.Surface] = {}

PLATE = (33, 29, 43)
PLATE_DARK = (19, 17, 25)
PLATE_LIGHT = (62, 55, 78)
EDGE = (86, 78, 104)
PURPLE = (150, 88, 226)
PURPLE_HI = (214, 164, 255)
PURPLE_DARK = (74, 42, 112)
CRIMSON = (168, 48, 74)
CAPE = (20, 14, 27)
CAPE_HI = (41, 27, 52)
STEEL = (58, 54, 70)
STEEL_HI = (126, 116, 146)
BONE = (188, 174, 196)


def _rot(x: float, y: float, angle: float, ox: float, oy: float):
    """Rotate a point around an origin; angle 0 points up."""
    dx, dy = x - ox, y - oy
    ca, sa = math.cos(angle), math.sin(angle)
    return ox + dx * ca - dy * sa, oy + dx * sa + dy * ca


def _blade(surf, hand, angle, length, glow):
    hx, hy = hand
    dx, dy = math.sin(angle), -math.cos(angle)
    px, py = -dy, dx
    tip = (hx + dx * length, hy + dy * length)
    wide = 7
    points = [
        (hx + px * 4, hy + py * 4),
        (tip[0] + px * wide, tip[1] + py * wide),
        (tip[0] + dx * 10, tip[1] + dy * 10),
        (tip[0] - px * wide, tip[1] - py * wide),
        (hx - px * 4, hy - py * 4),
    ]
    pygame.draw.polygon(surf, PLATE_DARK, points)
    pygame.draw.polygon(surf, STEEL, points, 1)
    # Fuller and a purple heat line along the blade.
    pygame.draw.line(surf, (90, 82, 108),
                     (hx + dx * 8, hy + dy * 8),
                     (tip[0] - dx * 6, tip[1] - dy * 6), 1)
    pygame.draw.line(surf, glow,
                     (hx + dx * 10 + px * 2, hy + dy * 10 + py * 2),
                     (tip[0] - dx * 4, tip[1] - dy * 4), 1)
    # Crossguard and grip.
    pygame.draw.line(surf, EDGE,
                     (hx + px * 13, hy + py * 13),
                     (hx - px * 13, hy - py * 13), 3)
    pygame.draw.line(surf, (42, 30, 48),
                     (hx - dx * 9, hy - dy * 9), (hx + dx * 2, hy + dy * 2), 5)
    pygame.draw.circle(surf, PURPLE_HI, (int(hx - dx * 9), int(hy - dy * 9)), 2)


def _pose(action: str, t: float):
    """Return (bob, lean, sword_angle, stride, arm_lift, glow, crouch)."""
    wave = math.sin(t * math.tau)
    if action == "walk":
        return (-abs(wave) * 2.0, 0.0, 2.42, wave, 0.0, 1.0, 0.0)
    if action == "windup":
        return (-1.0 - 2.0 * t, -2.0, 0.30 + 0.22 * t, 0.0,
                7.0, 1.4 + t, 0.0)
    if action == "sweep":
        return (1.0, 4.0, 2.52 - 2.72 * t, 0.0, -1.0, 2.3, 0.0)
    if action == "slam":
        if t < 0.45:
            return (-3.0, -1.0, 0.22 + 0.20 * t / 0.45, 0.0, 8.0,
                    1.6 + t * 2, 0.0)
        k = min(1.0, (t - 0.45) / 0.35)
        return (3.0 * k, 5.0 * k, 0.42 + 2.1 * k, 0.0, -3.0, 3.2, 3.0 * k)
    if action == "combo":
        if t < 0.5:
            k = t / 0.5
            return (0.0, 3.0, 2.5 - 2.5 * k, 0.0, 0.0, 2.0, 0.0)
        k = (t - 0.5) / 0.5
        return (0.0, 3.0, -2.45 + 2.45 * k, 0.0, 0.0, 2.4, 0.0)
    if action == "wave":
        return (-1.0, -1.0, 1.35 + 0.1 * wave, 0.0, 4.0,
                2.2 + 1.4 * t, 0.0)
    if action == "charge":
        return (-2.0 - wave, -3.0, 0.62, 0.0, 9.0, 2.6 + 2.0 * t, 0.0)
    if action == "roar":
        return (-3.0, -4.0, 0.55, 0.0, 11.0, 3.0, 0.0)
    if action == "hurt":
        return (1.0, 3.0, 2.6, 0.0, -1.0, 1.2, 0.0)
    if action == "death":
        return (10.0 * t, 9.0 * t, 2.7 + 0.5 * t, 0.0, -8.0 * t, 0.6, 0.0)
    if action == "victory":
        return (3.0, 2.0, 2.95, 0.0, 3.0, 1.0, 2.0)
    # idle
    return (wave * 1.2, 0.0, 2.46, 0.0, 0.0, 1.1, 0.0)


def render_frame(action: str, index: int, facing: str = "right") -> pygame.Surface:
    count, _fps, _loop = ANIMATIONS.get(action, ANIMATIONS["idle"])
    t = (index % max(1, count)) / max(1, count - 1)
    bob, lean, sword_angle, stride, arm_lift, glow, crouch = _pose(action, t)

    surf = pygame.Surface((FRAME, FRAME), pygame.SRCALPHA)
    cx, foot = FRAME / 2, FOOT_LINE

    # --- cape -----------------------------------------------------------
    cape_sway = stride * 4.0
    pygame.draw.polygon(surf, CAPE, [
        (38 + lean * 0.5, 40 + bob),
        (74 + lean * 0.5, 40 + bob),
        (84 + cape_sway, foot - 2),
        (66 + cape_sway * 0.5, foot - 8),
        (56, foot - 2),
        (44 + cape_sway * 0.5, foot - 9),
        (26 + cape_sway, foot - 2),
    ])
    pygame.draw.line(surf, CAPE_HI, (40 + lean * 0.5, 44 + bob),
                     (47 + cape_sway * 0.6, foot - 7), 1)

    # --- legs / greaves -------------------------------------------------
    for side, base_x in ((-1, 44), (1, 66)):
        step = stride * 4.0 * side
        top = 72 + bob + crouch
        bottom = foot - 2
        pygame.draw.polygon(surf, PLATE_DARK, [
            (base_x - 7 + step * 0.4, top),
            (base_x + 7 + step * 0.4, top),
            (base_x + 9 + step, bottom - 6),
            (base_x + 12 + step, bottom),
            (base_x - 8 + step, bottom),
            (base_x - 8 + step, bottom - 7),
        ])
        pygame.draw.line(surf, PLATE_LIGHT, (base_x - 4 + step * 0.5, top + 3),
                         (base_x - 4 + step, bottom - 6), 1)
        pygame.draw.line(surf, EDGE, (base_x - 10 + step, bottom),
                         (base_x + 13 + step, bottom), 2)

    # --- torso ----------------------------------------------------------
    torso = [
        (36 + lean, 40 + bob),
        (76 + lean, 40 + bob),
        (81 + lean, 62 + bob),
        (70 + lean, 79 + bob + crouch),
        (43 + lean, 79 + bob + crouch),
        (31 + lean, 62 + bob),
    ]
    pygame.draw.polygon(surf, PLATE, torso)
    pygame.draw.polygon(surf, EDGE, torso, 1)
    pygame.draw.line(surf, PLATE_LIGHT, (39 + lean, 44 + bob),
                     (39 + lean, 66 + bob), 2)
    pygame.draw.polygon(surf, PLATE_DARK, [
        (46 + lean, 63 + bob), (66 + lean, 63 + bob),
        (62 + lean, 80 + bob + crouch), (50 + lean, 80 + bob + crouch),
    ])
    # Chest furnace and cracks.
    gx, gy = 56 + lean, 53 + bob
    pygame.draw.circle(surf, PURPLE_DARK, (int(gx), int(gy)), 8)
    pygame.draw.circle(surf, PURPLE, (int(gx), int(gy)), 5)
    pygame.draw.circle(surf, PURPLE_HI, (int(gx), int(gy)), 2)
    for a, b in (((gx - 5, gy - 2), (gx - 16, gy - 9)),
                 ((gx + 4, gy + 3), (gx + 17, gy + 11)),
                 ((gx - 2, gy + 5), (gx - 9, gy + 17)),
                 ((gx + 6, gy - 4), (gx + 13, gy - 13))):
        pygame.draw.line(surf, PURPLE, a, b, max(1, int(glow * 0.7)))
        pygame.draw.line(surf, PURPLE_HI, a, b, 1)

    # --- pauldrons + spikes --------------------------------------------
    for side in (-1, 1):
        sx = 56 + lean + side * 27
        sy = 44 + bob - arm_lift * 0.25
        pygame.draw.polygon(surf, PLATE_DARK, [
            (sx - side * 10, sy - 4), (sx + side * 14, sy - 8),
            (sx + side * 18, sy + 10), (sx + side * 2, sy + 15),
            (sx - side * 12, sy + 6),
        ])
        pygame.draw.polygon(surf, PLATE_LIGHT, [
            (sx - side * 8, sy - 2), (sx + side * 12, sy - 6),
            (sx + side * 13, sy + 1), (sx - side * 7, sy + 3),
        ], 1)
        # Two horns/spikes on each shoulder.
        for spike, length in ((0.0, 11), (0.55, 8)):
            bx = sx + side * (3 + spike * 9)
            by = sy - 3
            pygame.draw.polygon(surf, EDGE, [
                (bx - 3, by), (bx + 3, by),
                (bx + side * 3, by - length),
            ])

    # --- arms -----------------------------------------------------------
    # Left arm hangs; right arm holds the blade and follows the pose.
    lx = 56 + lean - 24
    pygame.draw.line(surf, PLATE_DARK, (lx, 50 + bob), (lx - 4, 68 + bob), 7)
    pygame.draw.circle(surf, EDGE, (lx - 4, 69 + bob), 4)
    hx = 56 + lean + 27
    hy = 57 + bob - arm_lift * 0.5
    pygame.draw.line(surf, PLATE_DARK, (hx - 4, 48 + bob), (hx, hy), 8)
    pygame.draw.circle(surf, EDGE, (int(hx), int(hy)), 5)
    pygame.draw.circle(surf, PURPLE_HI, (int(hx - 1), int(hy)), 2)

    # --- greatsword -----------------------------------------------------
    _blade(surf, (hx + 2, hy + 2), sword_angle, 62, PURPLE_HI)

    # --- head / horned helm --------------------------------------------
    hy2 = 27 + bob - arm_lift * 0.1
    pygame.draw.polygon(surf, PLATE_DARK, [
        (45 + lean, hy2 + 12), (47 + lean, hy2),
        (65 + lean, hy2), (68 + lean, hy2 + 12),
        (63 + lean, hy2 + 19), (49 + lean, hy2 + 19),
    ])
    pygame.draw.polygon(surf, PLATE_LIGHT, [
        (48 + lean, hy2 + 2), (64 + lean, hy2 + 2),
        (63 + lean, hy2 + 7), (49 + lean, hy2 + 7),
    ], 1)
    # Visor slit: two hot eyes.
    pygame.draw.line(surf, (8, 6, 10), (49 + lean, hy2 + 11),
                     (64 + lean, hy2 + 11), 3)
    pygame.draw.line(surf, PURPLE_HI, (51 + lean, hy2 + 11),
                     (54 + lean, hy2 + 11), 1)
    pygame.draw.line(surf, PURPLE_HI, (59 + lean, hy2 + 11),
                     (62 + lean, hy2 + 11), 1)
    # Horns sweep up and out.
    for side in (-1, 1):
        bx = 56 + lean + side * 9
        by = hy2 + 1
        pygame.draw.lines(surf, BONE, False, [
            (bx, by), (bx + side * 9, by - 9),
            (bx + side * 12, by - 18), (bx + side * 8, by - 24),
        ], 2)
        pygame.draw.circle(surf, EDGE,
                           (int(bx + side * 8), int(by - 24)), 2)
    # Crown of small purple runes on the brow.
    for i in range(3):
        pygame.draw.rect(surf, PURPLE,
                         (int(50 + lean + i * 5), int(hy2 + 4), 2, 2))

    if facing == "left":
        surf = pygame.transform.flip(surf, True, False)
    return surf


class GuardianAnimator:
    def __init__(self, scale: float = 2.8) -> None:
        self.scale = scale
        self.action = "idle"
        self.facing = "right"
        self.frame = 0
        self.time = 0.0
        self.finished = False

    def play(self, action: str, facing: str | None = None,
             restart: bool = False) -> None:
        if facing is not None:
            self.facing = facing
        if action == self.action and not restart:
            return
        self.action = action if action in ANIMATIONS else "idle"
        self.frame = 0
        self.time = 0.0
        self.finished = False

    def update(self, dt: float) -> None:
        count, fps, loop = ANIMATIONS.get(self.action, ANIMATIONS["idle"])
        self.time += max(0.0, dt)
        step = self.time * fps
        if loop:
            self.frame = int(step) % count
        else:
            self.frame = min(count - 1, int(step))
            if step >= count:
                self.finished = True

    def _surface(self, action: str, index: int, facing: str) -> pygame.Surface:
        key = (action, index % ANIMATIONS.get(action, ANIMATIONS["idle"])[0],
               "left" if facing == "left" else "right")
        surf = CACHE.get(key)
        if surf is None:
            base = render_frame(action, index, facing)
            size = int(round(FRAME * self.scale))
            surf = pygame.transform.scale(base, (size, size))
            CACHE[key] = surf
        return surf

    @property
    def image(self) -> pygame.Surface:
        facing = "left" if self.facing == "left" else "right"
        return self._surface(self.action, self.frame, facing)

    @property
    def frame_size(self) -> int:
        return int(round(FRAME * self.scale))

    @property
    def foot_line(self) -> int:
        return int(round(FOOT_LINE * self.scale))


__all__ = ["ANIMATIONS", "FRAME", "FOOT_LINE", "GuardianAnimator", "render_frame"]
