"""Procedural pixel-art frames for the two new enemy archetypes.

The Fallen Knight keeps its generated spritesheet.  The Void Stalker and the
Ashen Cultist have no source sheet, so their frames are drawn once into small
64x64 surfaces and shared through a module-level cache.  Rendering is deliberately
primitive-based (polygons, lines, circles) so it stays in the same chunky pixel
style as the rest of the game and costs nothing per frame in the browser.
"""
from __future__ import annotations

import math

import pygame

FRAME = 64
FOOT_LINE = 52

ANIMATIONS: dict[str, tuple[int, float, bool]] = {
    "idle": (4, 5.0, True),
    "walk": (6, 8.0, True),
    "attack": (4, 10.0, False),
    "hurt": (3, 10.0, False),
    "death": (6, 8.0, False),
}

ATTACK_FPS = {"void_stalker": 16.0, "ashen_cultist": 7.5}

# Shared frame cache: every stalker/cultist instance reuses the same surfaces.
_FRAME_CACHE: dict[tuple[str, str, str, int, float], pygame.Surface] = {}

STALKER = {
    "cloak": (43, 32, 62),
    "cloak_dark": (27, 20, 40),
    "cloak_light": (73, 52, 102),
    "edge": (106, 76, 148),
    "skin": (54, 42, 66),
    "eye": (222, 150, 255),
    "eye_hot": (250, 232, 255),
    "claw": (172, 146, 198),
}

CULTIST = {
    "robe": (62, 47, 72),
    "robe_dark": (38, 29, 48),
    "trim": (116, 82, 132),
    "hood": (28, 21, 36),
    "face": (10, 8, 14),
    "eye": (238, 166, 255),
    "staff": (74, 53, 42),
    "staff_light": (118, 86, 64),
    "ember": (196, 120, 255),
    "ember_hot": (250, 230, 255),
}


class ProceduralAnimator:
    """Small animator with the same surface/name API used by the knight."""

    def __init__(self, kind: str, scale: float = 1.0) -> None:
        self.kind = kind
        self.scale = float(scale)
        self.current_name = ""
        self.action = "idle"
        self.facing = "down"
        self.index = 0
        self.time = 0.0
        self.finished = False
        self.fps = 5.0
        self.loop = True
        self.play("idle", "down", restart=True)

    # ------------------------------------------------------------------
    def play(self, action: str, facing: str, restart: bool = False) -> None:
        action = action if action in ANIMATIONS else "idle"
        name = f"{action}_{facing}"
        if name != self.current_name or restart:
            self.current_name = name
            self.action = action
            self.facing = facing
            self.index = 0
            self.time = 0.0
            self.finished = False
            count, fps, loop = ANIMATIONS[action]
            if action == "attack":
                fps = ATTACK_FPS.get(self.kind, fps)
            self.fps = fps
            self.loop = loop

    def update(self, dt: float) -> None:
        count, _, _ = ANIMATIONS[self.action]
        if count <= 1 or self.finished:
            return
        duration = count / self.fps
        self.time += dt
        if self.time >= duration:
            if self.loop:
                self.time %= duration
                self.index = int(self.time * self.fps) % count
            else:
                self.finished = True
                self.index = count - 1
        else:
            self.index = min(count - 1, int(self.time * self.fps))

    @property
    def image(self) -> pygame.Surface:
        return _frame(self.kind, self.action, self.facing, self.index, self.scale)


# ---------------------------------------------------------------------------
def _frame(kind: str, action: str, facing: str, index: int,
           scale: float) -> pygame.Surface:
    key = (kind, action, facing, index, scale)
    cached = _FRAME_CACHE.get(key)
    if cached is not None:
        return cached
    surface = pygame.Surface((FRAME, FRAME), pygame.SRCALPHA)
    count = ANIMATIONS[action][0]
    if kind == "ashen_cultist":
        _draw_cultist(surface, action, facing, index, count)
    else:
        _draw_stalker(surface, action, facing, index, count)
    if scale != 1.0:
        surface = pygame.transform.scale(
            surface, (int(FRAME * scale), int(FRAME * scale))
        )
    _FRAME_CACHE[key] = surface
    return surface


def _mirrored(facing: str) -> tuple[str, bool]:
    if facing == "right":
        return "left", True
    return facing, False


def _phase(index: int, count: int) -> float:
    return index / max(1, count - 1)


# ---------------------------------------------------------------------------
# Void Stalker
# ---------------------------------------------------------------------------
def _draw_stalker(surf: pygame.Surface, action: str, facing: str,
                  index: int, count: int) -> None:
    draw_facing, mirror = _mirrored(facing)
    t = _phase(index, count)
    bob = (0, -1, 0, 1)[index % 4] if action in ("idle", "walk") else 0
    sway = 0.0
    if action == "walk":
        sway = math.sin(index / count * math.tau) * 1.8
    lunge = 0.0
    crouch = 0
    if action == "attack":
        lunge = (0.0, -3.0, 5.0, 2.0)[min(index, 3)]
        crouch = (2, 0, -1, 1)[min(index, 3)]
    if action == "hurt":
        lunge = -4.0 - t * 2.0
    if action == "death":
        _draw_stalker_death(surf, draw_facing, t)
        return

    cx = 32 + int(round(sway + lunge))
    top = 17 + bob - crouch
    hem = 50 + bob
    dark = STALKER["cloak_dark"]
    cloak = STALKER["cloak"]
    edge = STALKER["edge"]

    # Long, tattered cloak silhouette.
    if draw_facing in ("down", "up"):
        body = [
            (cx - 7, top + 8), (cx + 7, top + 8),
            (cx + 10, hem - 3), (cx + 6, hem + 2), (cx + 3, hem - 3),
            (cx, hem + 3), (cx - 3, hem - 3), (cx - 6, hem + 2),
            (cx - 10, hem - 3),
        ]
        pygame.draw.polygon(surf, dark, body)
        pygame.draw.polygon(surf, cloak, [
            (cx - 5, top + 9), (cx + 5, top + 9),
            (cx + 7, hem - 4), (cx, hem + 1), (cx - 7, hem - 4),
        ])
    else:
        # Profile: hunched back on the trailing side, claws on the leading side.
        body = [
            (cx + 6, top + 7), (cx + 10, hem - 6),
            (cx + 7, hem + 3), (cx + 2, hem - 2),
            (cx - 4, hem + 3), (cx - 8, hem - 5),
            (cx - 6, top + 10),
        ]
        pygame.draw.polygon(surf, dark, body)
        pygame.draw.polygon(surf, cloak, [
            (cx + 4, top + 9), (cx + 7, hem - 6), (cx, hem + 2),
            (cx - 6, hem - 6), (cx - 3, top + 11),
        ])
    pygame.draw.line(surf, edge, (cx - 5, top + 12), (cx - 7, hem - 6), 1)
    pygame.draw.line(surf, STALKER["cloak_light"], (cx + 5, top + 12),
                     (cx + 7, hem - 8), 1)

    # Bone legs and claw feet.
    step = math.sin(index / count * math.tau) * 2.0 if action == "walk" else 0.0
    if draw_facing in ("down", "up"):
        pygame.draw.line(surf, STALKER["skin"], (cx - 3, hem - 4),
                         (cx - 5 - step, 52), 2)
        pygame.draw.line(surf, STALKER["skin"], (cx + 3, hem - 4),
                         (cx + 5 + step, 52), 2)
        pygame.draw.line(surf, STALKER["claw"], (cx - 5 - step, 52),
                         (cx - 8 - step, 53), 1)
        pygame.draw.line(surf, STALKER["claw"], (cx + 5 + step, 52),
                         (cx + 8 + step, 53), 1)
    else:
        pygame.draw.line(surf, STALKER["skin"], (cx - 1, hem - 5),
                         (cx - 4 - step, 52), 2)
        pygame.draw.line(surf, STALKER["skin"], (cx + 2, hem - 5),
                         (cx + 5 + step, 52), 2)
        pygame.draw.line(surf, STALKER["claw"], (cx - 4 - step, 52),
                         (cx - 8 - step, 53), 1)

    # Head and glowing eyes.
    pygame.draw.circle(surf, STALKER["skin"], (cx, top + 5), 6)
    pygame.draw.circle(surf, dark, (cx, top + 3), 5)
    if draw_facing == "down":
        pygame.draw.rect(surf, STALKER["eye"], (cx - 4, top + 3, 3, 2))
        pygame.draw.rect(surf, STALKER["eye"], (cx + 2, top + 3, 3, 2))
        pygame.draw.rect(surf, STALKER["eye_hot"], (cx - 3, top + 3, 1, 1))
        pygame.draw.rect(surf, STALKER["eye_hot"], (cx + 3, top + 3, 1, 1))
    elif draw_facing == "left":
        pygame.draw.rect(surf, STALKER["eye"], (cx - 5, top + 3, 3, 2))
        pygame.draw.rect(surf, STALKER["eye_hot"], (cx - 5, top + 3, 1, 1))
    else:
        pygame.draw.line(surf, STALKER["edge"], (cx - 4, top + 6),
                         (cx + 4, top + 6), 1)
        pygame.draw.rect(surf, STALKER["cloak_light"], (cx - 1, top + 1, 2, 2))

    # Arms: long void claws.  The attack pose thrusts them forward.
    arm_y = top + 14
    if action == "attack":
        if draw_facing == "left":
            reach = 11 + int(t * 4)
            pygame.draw.line(surf, STALKER["skin"], (cx - 4, arm_y),
                             (cx - reach, arm_y - 2), 2)
            for spread in (-3, 0, 3):
                pygame.draw.line(surf, STALKER["claw"],
                                 (cx - reach, arm_y - 2),
                                 (cx - reach - 6, arm_y - 2 + spread), 1)
            pygame.draw.line(surf, STALKER["skin"], (cx + 2, arm_y + 2),
                             (cx - 2, arm_y + 10), 2)
        else:
            pygame.draw.line(surf, STALKER["skin"], (cx - 6, arm_y),
                             (cx - 12, arm_y + 7), 2)
            pygame.draw.line(surf, STALKER["skin"], (cx + 6, arm_y),
                             (cx + 12, arm_y + 7), 2)
            for side in (-1, 1):
                base_x = cx + side * 12
                for spread in (-3, 0, 3):
                    pygame.draw.line(surf, STALKER["claw"],
                                     (base_x, arm_y + 7),
                                     (base_x + side * 4,
                                      arm_y + 11 + spread), 1)
    else:
        if draw_facing == "left":
            pygame.draw.line(surf, STALKER["skin"], (cx - 2, arm_y),
                             (cx - 10, arm_y + 9), 2)
            for spread in (-2, 0, 2):
                pygame.draw.line(surf, STALKER["claw"],
                                 (cx - 10, arm_y + 9),
                                 (cx - 14, arm_y + 12 + spread), 1)
            pygame.draw.line(surf, STALKER["skin"], (cx + 3, arm_y),
                             (cx + 7, arm_y + 10), 2)
        else:
            for side in (-1, 1):
                shoulder = cx + side * 5
                hand = cx + side * 10
                pygame.draw.line(surf, STALKER["skin"], (shoulder, arm_y),
                                 (hand, arm_y + 11), 2)
                for spread in (-2, 0, 2):
                    pygame.draw.line(surf, STALKER["claw"],
                                     (hand, arm_y + 11),
                                     (hand + side * 3,
                                      arm_y + 14 + spread), 1)

    # Back spines catch the moonlight.
    for spine in range(3):
        sy = top + 10 + spine * 5
        pygame.draw.line(surf, STALKER["edge"], (cx + 6, sy),
                         (cx + 10, sy - 2), 1)

    if mirror:
        _flip_in_place(surf)


def _draw_stalker_death(surf: pygame.Surface, facing: str, t: float) -> None:
    collapse = min(1.0, t * 1.15)
    cx = 32
    height = int(26 * (1.0 - collapse * 0.72))
    top = 50 - height
    width = int(18 * (1.0 - collapse * 0.35))
    pygame.draw.ellipse(surf, STALKER["cloak_dark"],
                        (cx - width, 44 + int(collapse * 4), width * 2,
                         max(4, 12 - int(collapse * 5))))
    pygame.draw.polygon(surf, STALKER["cloak"], [
        (cx - width // 2, top + 4), (cx + width // 2, top + 4),
        (cx + width, 50), (cx - width, 50),
    ])
    pygame.draw.circle(surf, STALKER["skin"], (cx, top + 3), max(2, 6 - int(collapse * 3)))
    if collapse < 0.55 and facing in ("down", "left", "right"):
        pygame.draw.rect(surf, STALKER["eye"], (cx - 2, top + 2, 2, 1))
    for spread in (-8, -3, 3, 8):
        pygame.draw.line(surf, STALKER["claw"], (cx + spread, 46 + int(collapse * 5)),
                         (cx + spread - 4, 52), 1)


# ---------------------------------------------------------------------------
# Ashen Cultist
# ---------------------------------------------------------------------------
def _draw_cultist(surf: pygame.Surface, action: str, facing: str,
                  index: int, count: int) -> None:
    draw_facing, mirror = _mirrored(facing)
    t = _phase(index, count)
    bob = (0, -1, 0, 1)[index % 4] if action in ("idle", "walk") else 0
    sway = math.sin(index / count * math.tau) * 1.5 if action == "walk" else 0.0
    lean = 0.0
    if action == "attack":
        lean = (0.0, -1.0, 2.0, 1.0)[min(index, 3)]
    if action == "hurt":
        lean = -4.0 - t * 2.0
    if action == "death":
        _draw_cultist_death(surf, draw_facing, t)
        return

    cx = 32 + int(round(sway + lean))
    top = 26 + bob
    hem = 52 + bob
    robe = CULTIST["robe"]
    dark = CULTIST["robe_dark"]
    trim = CULTIST["trim"]

    # Staff first, so the robe overlaps it.
    staff_x = cx + 15
    staff_top = 12 + bob
    if action == "attack":
        staff_x += int(t * 5)
        staff_top -= int(t * 7)
    pygame.draw.line(surf, CULTIST["staff"], (staff_x, staff_top),
                     (staff_x + 1, hem), 2)
    pygame.draw.line(surf, CULTIST["staff_light"], (staff_x, staff_top + 2),
                     (staff_x, hem - 6), 1)
    pygame.draw.line(surf, CULTIST["staff"], (staff_x, staff_top),
                     (staff_x + 4, staff_top + 2), 1)
    orb_y = staff_top - 3
    orb_r = 3
    if action == "attack":
        orb_r = 3 + int(t * 4)
    pygame.draw.circle(surf, (60, 32, 90), (staff_x, orb_y), orb_r + 2)
    pygame.draw.circle(surf, CULTIST["ember"], (staff_x, orb_y), orb_r)
    pygame.draw.circle(surf, CULTIST["ember_hot"], (staff_x, orb_y),
                       max(1, orb_r // 2))

    # Robe.
    if draw_facing in ("down", "up"):
        pygame.draw.polygon(surf, dark, [
            (cx - 9, top), (cx + 9, top), (cx + 13, hem), (cx - 13, hem),
        ])
        pygame.draw.polygon(surf, robe, [
            (cx - 7, top + 1), (cx + 7, top + 1),
            (cx + 10, hem - 1), (cx - 10, hem - 1),
        ])
        pygame.draw.line(surf, trim, (cx - 6, top + 3), (cx - 8, hem - 2), 1)
        pygame.draw.line(surf, trim, (cx + 6, top + 3), (cx + 8, hem - 2), 1)
        pygame.draw.polygon(surf, dark, [
            (cx - 12, hem), (cx - 8, hem - 5), (cx - 4, hem + 2),
            (cx + 1, hem - 5), (cx + 6, hem + 2), (cx + 10, hem - 5),
            (cx + 13, hem),
        ])
    else:
        pygame.draw.polygon(surf, dark, [
            (cx - 6, top + 2), (cx + 7, top), (cx + 10, hem), (cx - 10, hem),
        ])
        pygame.draw.polygon(surf, robe, [
            (cx - 4, top + 3), (cx + 5, top + 1), (cx + 7, hem - 1),
            (cx - 8, hem - 1),
        ])
        pygame.draw.line(surf, trim, (cx - 6, top + 4), (cx - 8, hem - 2), 1)
        pygame.draw.line(surf, trim, (cx + 5, top + 3), (cx + 6, hem - 2), 1)
        pygame.draw.polygon(surf, dark, [
            (cx - 9, hem), (cx - 5, hem - 5), (cx - 1, hem + 2),
            (cx + 3, hem - 5), (cx + 7, hem + 1), (cx + 9, hem),
        ])

    # Hood and face.
    pygame.draw.circle(surf, dark, (cx, top - 7), 9)
    pygame.draw.circle(surf, robe, (cx, top - 8), 8)
    pygame.draw.circle(surf, CULTIST["face"], (cx, top - 5), 5)
    if draw_facing == "down":
        pygame.draw.rect(surf, CULTIST["eye"], (cx - 4, top - 6, 3, 2))
        pygame.draw.rect(surf, CULTIST["eye"], (cx + 2, top - 6, 3, 2))
    elif draw_facing == "left":
        pygame.draw.rect(surf, CULTIST["eye"], (cx - 5, top - 6, 3, 2))
    else:
        pygame.draw.line(surf, trim, (cx - 5, top - 7), (cx + 5, top - 7), 1)

    # Arm holding the staff.
    shoulder = (cx + 5, top + 3)
    hand = (staff_x - 1, staff_top + 14)
    pygame.draw.line(surf, dark, shoulder, hand, 2)
    pygame.draw.circle(surf, CULTIST["robe"], hand, 2)

    # Ash motes around the staff on the wind-up.
    if action == "attack" and t > 0.35:
        for mote in range(3):
            angle = t * 5.0 + mote * 2.1
            mx = staff_x + int(math.cos(angle) * (7 + mote * 2))
            my = orb_y + int(math.sin(angle) * (5 + mote))
            pygame.draw.rect(surf, CULTIST["ember"], (mx, my, 2, 2))

    if mirror:
        _flip_in_place(surf)


def _draw_cultist_death(surf: pygame.Surface, facing: str, t: float) -> None:
    collapse = min(1.0, t * 1.1)
    cx = 32
    width = int(14 * (1.0 - collapse * 0.28))
    top = int(50 - 24 * (1.0 - collapse * 0.75))
    pygame.draw.ellipse(surf, CULTIST["robe_dark"],
                        (cx - width, 45 + int(collapse * 3), width * 2,
                         max(4, 10 - int(collapse * 4))))
    pygame.draw.polygon(surf, CULTIST["robe"], [
        (cx - width // 2, top + 3), (cx + width // 2, top + 3),
        (cx + width, 50), (cx - width, 50),
    ])
    if collapse < 0.6:
        pygame.draw.circle(surf, CULTIST["hood"], (cx, top + 1), max(2, 6 - int(collapse * 2)))
    pygame.draw.line(surf, CULTIST["staff"], (cx + 8, 36 + int(collapse * 10)),
                     (cx + 12, 52), 2)
    pygame.draw.rect(surf, CULTIST["ember"], (cx + 8, 38 + int(collapse * 10), 2, 2))
    for spread in (-7, -2, 3, 8):
        pygame.draw.line(surf, CULTIST["trim"], (cx + spread, 47 + int(collapse * 4)),
                         (cx + spread, 52), 1)


def _flip_in_place(surface: pygame.Surface) -> None:
    """Flip in place; the frame cache always returns a fresh surface."""
    flipped = pygame.transform.flip(surface, True, False)
    surface.fill((0, 0, 0, 0))
    surface.blit(flipped, (0, 0))
