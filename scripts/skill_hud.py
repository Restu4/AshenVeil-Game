"""VOID ESSENCE HUD panel: energy bar and four skill slots.

The panel is deliberately separate from the vitality panel: the health bar keeps
its existing place and styling, while this block sits directly beneath it with a
darker charcoal/purple palette.  Everything static is baked once; only the
energy fill, cooldown overlays and numeric labels are drawn per frame.
"""
from __future__ import annotations

import math

import pygame

from scripts.pixel_font import draw_text, text_width

PANEL_X = 24
PANEL_Y = 128
PANEL_W = 348
PANEL_H = 160
SLOT = 72
SLOT_GAP = 10
SLOT_MARGIN = 15
SLOT_Y = 62

ENERGY_LABEL = (156, 132, 198)
ENERGY_VALUE = (222, 200, 255)
TEXT_DIM = (118, 104, 140)
TEXT_KEY = (206, 188, 240)
TEXT_COST = (150, 130, 180)
BORDER = (88, 66, 128)
BORDER_DARK = (44, 32, 66)
PANEL_FILL = (10, 8, 16, 196)


class SkillHUD:
    def __init__(self) -> None:
        self._panel = self._make_panel()
        self._cooldown = pygame.Surface((SLOT, SLOT), pygame.SRCALPHA)
        self._cooldown.fill((4, 3, 8, 168))
        self._disabled = pygame.Surface((SLOT, SLOT), pygame.SRCALPHA)
        self._disabled.fill((6, 5, 10, 128))

    # ------------------------------------------------------------------
    @staticmethod
    def _make_panel() -> pygame.Surface:
        surf = pygame.Surface((PANEL_W, PANEL_H), pygame.SRCALPHA)
        surf.fill(PANEL_FILL)
        pygame.draw.rect(surf, (*BORDER, 235), (0, 0, PANEL_W, PANEL_H), 1)
        pygame.draw.rect(surf, (*BORDER_DARK, 230),
                         (2, 2, PANEL_W - 4, PANEL_H - 4), 1)
        for cx, cy, dx, dy in ((2, 2, 1, 1), (PANEL_W - 3, 2, -1, 1),
                               (2, PANEL_H - 3, 1, -1),
                               (PANEL_W - 3, PANEL_H - 3, -1, -1)):
            pygame.draw.line(surf, (150, 118, 206, 235), (cx, cy),
                             (cx + 9 * dx, cy), 1)
            pygame.draw.line(surf, (150, 118, 206, 235), (cx, cy),
                             (cx, cy + 9 * dy), 1)
        draw_text(surf, "VOID ESSENCE", 16, 8, 1, ENERGY_LABEL, spacing=2)
        draw_text(surf, "DARK MAGIC", PANEL_W - 16 - text_width("DARK MAGIC", 1, 2),
                  8, 1, (92, 78, 116), spacing=2)
        return surf

    # ------------------------------------------------------------------
    def draw(self, target: pygame.Surface, skills, player) -> None:
        if skills is None:
            return
        target.blit(self._panel, (PANEL_X, PANEL_Y))
        energy = skills.energy

        value = f"{int(round(energy.current)):03d}"
        draw_text(target, value,
                  PANEL_X + PANEL_W - 16 - text_width(value, 1, 1),
                  PANEL_Y + 8, 1, ENERGY_VALUE, spacing=1)
        self._energy_bar(target, PANEL_X + 16, PANEL_Y + 24,
                         PANEL_W - 32, 12, energy.ratio)

        for index, skill in enumerate(skills.skills):
            sx = PANEL_X + SLOT_MARGIN + index * (SLOT + SLOT_GAP)
            sy = PANEL_Y + SLOT_Y
            self._slot(target, skill, player, energy, sx, sy)

    # ------------------------------------------------------------------
    @staticmethod
    def _energy_bar(target, x: int, y: int, w: int, h: int,
                    ratio: float) -> None:
        ratio = max(0.0, min(1.0, ratio))
        pygame.draw.rect(target, (5, 4, 8), (x - 2, y - 2, w + 4, h + 4))
        pygame.draw.rect(target, (54, 42, 72), (x - 1, y - 1, w + 2, h + 2))
        pygame.draw.rect(target, (16, 12, 24), (x, y, w, h))
        fill = int(w * ratio)
        if fill > 0:
            pygame.draw.rect(target, (92, 56, 148), (x, y, fill, h))
            pygame.draw.rect(target, (166, 118, 238), (x, y, fill, max(1, h // 3)))
            pygame.draw.rect(target, (56, 32, 92), (x, y + h - max(1, h // 3),
                                                     fill, max(1, h // 3)))
            if ratio > 0.02:
                pygame.draw.rect(target, (232, 210, 255),
                                 (x + fill - 2, y, 2, h))
        for i in range(1, 10):
            tx = x + int(w * i / 10)
            pygame.draw.line(target, (26, 20, 36), (tx, y),
                             (tx, y + h - 1))
        pygame.draw.rect(target, (116, 90, 158), (x - 2, y - 2, w + 4, h + 4),
                         1)

    # ------------------------------------------------------------------
    def _slot(self, target, skill, player, energy, x: int, y: int) -> None:
        affordable = energy.can_afford(skill.cost)
        locked = player.combat.dead or not affordable
        charging = skill.icon == "eclipse" and getattr(skill, "charging", False)

        pygame.draw.rect(target, (6, 5, 10), (x - 1, y - 1, SLOT + 2, SLOT + 2))
        pygame.draw.rect(target, (18, 14, 27), (x, y, SLOT, SLOT))
        if charging:
            border = (224, 190, 255)
        elif locked:
            border = (52, 42, 68)
        elif skill.ready:
            border = BORDER
        else:
            border = (68, 50, 96)
        pygame.draw.rect(target, border, (x, y, SLOT, SLOT), 1)
        pygame.draw.line(target, (128, 98, 176), (x + 2, y + 2),
                         (x + SLOT - 3, y + 2), 1)

        cx = x + SLOT // 2
        cy = y + 36
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
                label = f"{int(math_ceil(skill.timer))}"
                draw_text(target, label, cx - text_width(label, 2, 1) // 2,
                          cy - 7, 2, (238, 224, 255), spacing=1,
                          shadow=(4, 2, 8))

        if locked and not charging:
            target.set_clip((x, y, SLOT, SLOT))
            target.blit(self._disabled, (x, y))
            target.set_clip(None)

        draw_text(target, skill.key, x + 5, y + 4, 2,
                  TEXT_KEY if not locked or charging else TEXT_DIM, spacing=1,
                  shadow=(3, 2, 6))
        draw_text(target, f"{int(skill.cost)}",
                  x + SLOT - 5 - text_width(f"{int(skill.cost)}", 1, 1),
                  y + SLOT - 10, 1,
                  TEXT_COST if not locked or charging else (86, 74, 102),
                  spacing=1)

    # ------------------------------------------------------------------
    @staticmethod
    def _icon(target, kind: str, cx: int, cy: int,
              color: tuple[int, int, int], charging: bool) -> None:
        if kind == "burst":
            pygame.draw.circle(target, color, (cx, cy), 15, 2)
            pygame.draw.circle(target, color, (cx, cy), 9, 1)
            pygame.draw.circle(target, color, (cx, cy), 3)
            for angle in (0.0, 1.5708, 3.1416, 4.7124):
                x1 = int(cx + math.cos(angle) * 17)
                y1 = int(cy + math.sin(angle) * 17)
                x2 = int(cx + math.cos(angle) * 22)
                y2 = int(cy + math.sin(angle) * 22)
                pygame.draw.line(target, color, (x1, y1), (x2, y2), 2)
        elif kind == "shadow":
            for offset in (-10, 0, 10):
                pygame.draw.line(target, color,
                                 (cx - 13 + offset, cy - 11),
                                 (cx - 1 + offset, cy), 2)
                pygame.draw.line(target, color,
                                 (cx - 1 + offset, cy),
                                 (cx - 13 + offset, cy + 11), 2)
        elif kind == "slash":
            rect = pygame.Rect(cx - 17, cy - 17, 34, 34)
            pygame.draw.arc(target, color, rect, 2.1, 5.1, 3)
            pygame.draw.arc(target, color,
                            (cx - 11, cy - 11, 22, 22), 2.3, 4.9, 1)
        else:  # eclipse
            pygame.draw.circle(target, (26, 16, 38), (cx, cy), 16)
            pygame.draw.circle(target, color, (cx, cy), 16, 2)
            pygame.draw.arc(target, color, (cx - 16, cy - 16, 32, 32),
                            1.6, 3.6, 2)
            if charging:
                pygame.draw.circle(target, (246, 232, 255), (cx, cy), 3)


def math_ceil(value: float) -> int:
    """Small indirection so the HUD keeps integer cooldown labels."""
    return int(value) + (0 if float(value).is_integer() else 1)
