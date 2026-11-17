"""Compact VOID ESSENCE HUD: four 42 px icons, bottom-right only.

The old Phase 3 panel was 348 x 160 and dominated the lower-left corner.  It is
now a single slim strip of icons with no title block, no second energy bar and
no wasted width.  Static chrome is baked once; per-frame work is the cooldown
band, key/cost labels and icon glyphs.
"""
from __future__ import annotations

import math

import pygame

from settings import SCREEN_H, SCREEN_W
from scripts.pixel_font import draw_text, text_width

SLOT = 42
SLOT_GAP = 6
SLOT_MARGIN = 20
SLOT_COUNT = 4
PANEL_W = SLOT * SLOT_COUNT + SLOT_GAP * (SLOT_COUNT - 1)
PANEL_H = SLOT
PANEL_X = SCREEN_W - SLOT_MARGIN - PANEL_W
PANEL_Y = SCREEN_H - SLOT_MARGIN - PANEL_H

TEXT_DIM = (112, 98, 132)
TEXT_KEY = (210, 190, 244)
TEXT_COST = (150, 130, 180)
BORDER = (92, 70, 128)
BORDER_DARK = (44, 32, 66)
PANEL_FILL = (9, 7, 15, 172)


class SkillHUD:
    def __init__(self) -> None:
        self._panel = self._make_panel()
        self._cooldown = pygame.Surface((SLOT, SLOT), pygame.SRCALPHA)
        self._cooldown.fill((4, 3, 8, 172))
        self._disabled = pygame.Surface((SLOT, SLOT), pygame.SRCALPHA)
        self._disabled.fill((6, 5, 10, 132))

    # ------------------------------------------------------------------
    @staticmethod
    def _make_panel() -> pygame.Surface:
        surf = pygame.Surface((PANEL_W, PANEL_H), pygame.SRCALPHA)
        surf.fill(PANEL_FILL)
        pygame.draw.rect(surf, (*BORDER, 210), (0, 0, PANEL_W, PANEL_H), 1)
        pygame.draw.rect(surf, (*BORDER_DARK, 220),
                         (2, 2, PANEL_W - 4, PANEL_H - 4), 1)
        return surf

    # ------------------------------------------------------------------
    def draw(self, target: pygame.Surface, skills, player) -> None:
        if skills is None:
            return
        target.blit(self._panel, (PANEL_X, PANEL_Y))
        for index, skill in enumerate(skills.skills):
            sx = PANEL_X + index * (SLOT + SLOT_GAP)
            self._slot(target, skill, player, skills.energy, sx, PANEL_Y)

    # ------------------------------------------------------------------
    def _slot(self, target, skill, player, energy, x: int, y: int) -> None:
        affordable = energy.can_afford(skill.cost)
        locked = player.combat.dead or not affordable
        charging = skill.icon == "eclipse" and getattr(skill, "charging", False)

        pygame.draw.rect(target, (6, 5, 10), (x, y, SLOT, SLOT))
        pygame.draw.rect(target, (18, 14, 27), (x + 1, y + 1,
                                               SLOT - 2, SLOT - 2))
        if charging:
            border = (224, 190, 255)
        elif locked:
            border = (52, 42, 68)
        elif skill.ready:
            border = BORDER
        else:
            border = (68, 50, 96)
        pygame.draw.rect(target, border, (x, y, SLOT, SLOT), 1)

        cx = x + SLOT // 2
        cy = y + SLOT // 2 + 2
        if locked and not charging:
            icon_color = (84, 72, 102)
        elif skill.ready or charging:
            icon_color = (208, 178, 255)
        else:
            icon_color = (126, 100, 160)
        self._icon(target, skill.icon, cx, cy, icon_color, charging)

        # Cooldown overlay: a dark band that shrinks from the bottom.
        if skill.timer > 0.0 and skill.cooldown > 0.0:
            ratio = max(0.0, min(1.0, skill.timer / skill.cooldown))
            height = int(SLOT * ratio)
            if height > 0:
                target.set_clip((x, y + SLOT - height, SLOT, height))
                target.blit(self._cooldown, (x, y))
                target.set_clip(None)
            if skill.timer >= 1.0:
                label = f"{math_ceil(skill.timer)}"
                draw_text(target, label, cx - text_width(label, 1, 1) // 2,
                          cy - 4, 1, (238, 224, 255), spacing=1,
                          shadow=(4, 2, 8))

        if locked and not charging:
            target.set_clip((x, y, SLOT, SLOT))
            target.blit(self._disabled, (x, y))
            target.set_clip(None)

        draw_text(target, skill.key, x + 3, y + 2, 1,
                  TEXT_KEY if not locked or charging else TEXT_DIM,
                  spacing=1, shadow=(3, 2, 6))
        cost = f"{int(skill.cost)}"
        draw_text(target, cost,
                  x + SLOT - 3 - text_width(cost, 1, 1),
                  y + SLOT - 9, 1,
                  TEXT_COST if not locked or charging else (86, 74, 102),
                  spacing=1, shadow=(3, 2, 6))

    # ------------------------------------------------------------------
    @staticmethod
    def _icon(target, kind: str, cx: int, cy: int,
              color: tuple[int, int, int], charging: bool) -> None:
        if kind == "burst":
            pygame.draw.circle(target, color, (cx, cy), 9, 1)
            pygame.draw.circle(target, color, (cx, cy), 5, 1)
            pygame.draw.circle(target, color, (cx, cy), 2)
            for angle in (0.0, 1.5708, 3.1416, 4.7124):
                x1 = int(cx + math.cos(angle) * 10)
                y1 = int(cy + math.sin(angle) * 10)
                x2 = int(cx + math.cos(angle) * 13)
                y2 = int(cy + math.sin(angle) * 13)
                pygame.draw.line(target, color, (x1, y1), (x2, y2), 1)
        elif kind == "shadow":
            for offset in (-6, 0, 6):
                pygame.draw.line(target, color,
                                 (cx - 8 + offset, cy - 7),
                                 (cx - 1 + offset, cy), 1)
                pygame.draw.line(target, color,
                                 (cx - 1 + offset, cy),
                                 (cx - 8 + offset, cy + 7), 1)
        elif kind == "slash":
            rect = pygame.Rect(cx - 10, cy - 10, 20, 20)
            pygame.draw.arc(target, color, rect, 2.1, 5.1, 2)
            pygame.draw.arc(target, color,
                            (cx - 6, cy - 6, 12, 12), 2.3, 4.9, 1)
        else:  # eclipse
            pygame.draw.circle(target, (26, 16, 38), (cx, cy), 9)
            pygame.draw.circle(target, color, (cx, cy), 9, 1)
            pygame.draw.arc(target, color, (cx - 9, cy - 9, 18, 18),
                            1.6, 3.6, 1)
            if charging:
                pygame.draw.circle(target, (246, 232, 255), (cx, cy), 2)


def math_ceil(value: float) -> int:
    """Small indirection so the HUD keeps integer cooldown labels."""
    return int(value) + (0 if float(value).is_integer() else 1)
