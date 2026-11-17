"""Boss health presentation: large but compact, top centre only.

The bar is wide enough to read across the arena (620 px) yet short (64 px), so
the fight keeps the middle of the screen.  It is drawn only while a boss
encounter is live and disappears as soon as the guardian is defeated.
"""
from __future__ import annotations

import math

import pygame

from settings import SCREEN_W
from scripts.bosses.hollow_guardian import INTRO, PHASE_THRESHOLDS
from scripts.pixel_font import draw_text, text_width

BAR_W, BAR_H = 620, 64
BAR_X = (SCREEN_W - BAR_W) // 2
BAR_Y = 8
FILL_X = BAR_X + 14
FILL_Y = BAR_Y + 32
FILL_W = BAR_W - 28
FILL_H = 15

PURPLE = (154, 96, 226)
PURPLE_HI = (218, 176, 255)
PURPLE_DARK = (62, 34, 98)
CRIMSON = (196, 62, 86)
CRIMSON_HI = (236, 126, 142)
BONE = (222, 212, 232)
DIM = (128, 112, 146)


class BossHUD:
    def __init__(self) -> None:
        self.time = 0.0
        self._panel = self._make_panel()

    @staticmethod
    def _make_panel() -> pygame.Surface:
        surf = pygame.Surface((BAR_W, BAR_H), pygame.SRCALPHA)
        surf.fill((9, 7, 13, 208))
        pygame.draw.rect(surf, (124, 92, 156, 236), (0, 0, BAR_W, BAR_H), 1)
        pygame.draw.rect(surf, (36, 26, 48, 230), (2, 2, BAR_W - 4, BAR_H - 4),
                         1)
        for cx, cy, dx, dy in ((2, 2, 1, 1), (BAR_W - 3, 2, -1, 1),
                               (2, BAR_H - 3, 1, -1),
                               (BAR_W - 3, BAR_H - 3, -1, -1)):
            pygame.draw.line(surf, (204, 168, 236), (cx, cy),
                             (cx + 10 * dx, cy), 1)
            pygame.draw.line(surf, (204, 168, 236), (cx, cy),
                             (cx, cy + 10 * dy), 1)
        # Crimson ritual notches on the frame.
        pygame.draw.line(surf, (128, 40, 58), (18, 0), (58, 0), 2)
        pygame.draw.line(surf, (128, 40, 58), (BAR_W - 58, 0),
                         (BAR_W - 18, 0), 2)
        return surf

    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        self.time += dt

    def draw(self, target: pygame.Surface, boss_manager) -> None:
        if boss_manager is None:
            return
        boss = getattr(boss_manager, "boss", None)
        if boss is None or not boss_manager.in_fight:
            return
        if boss.health.dead:
            return

        target.blit(self._panel, (BAR_X, BAR_Y))
        self._draw_name(target, boss)
        self._draw_bar(target, boss)
        self._draw_phases(target, boss)
        self._draw_banner(target, boss)
        self._draw_intro_hint(target, boss)

    # ------------------------------------------------------------------
    def _draw_name(self, target: pygame.Surface, boss) -> None:
        name = getattr(boss, "name", "THE HOLLOW GUARDIAN")
        draw_text(target, name, BAR_X + BAR_W // 2, BAR_Y + 9, 2, BONE,
                  spacing=2, shadow=(5, 2, 8), center=True)
        phase = f"PHASE {boss.phase}  ·  {boss.phase_name}"
        width = text_width(phase, 1, 1)
        draw_text(target, phase, BAR_X + BAR_W - 14 - width, BAR_Y + 12, 1,
                  (188, 152, 220), spacing=1)

    def _draw_bar(self, target: pygame.Surface, boss) -> None:
        ratio = max(0.0, min(1.0, boss.health.ratio))
        pygame.draw.rect(target, (4, 3, 6), (FILL_X - 2, FILL_Y - 2,
                                             FILL_W + 4, FILL_H + 4))
        pygame.draw.rect(target, (18, 13, 24),
                         (FILL_X, FILL_Y, FILL_W, FILL_H))
        fill = int(FILL_W * ratio)
        if fill > 0:
            pygame.draw.rect(target, PURPLE_DARK,
                             (FILL_X, FILL_Y, fill, FILL_H))
            pygame.draw.rect(target, PURPLE,
                             (FILL_X, FILL_Y, fill, FILL_H - 6))
            pygame.draw.rect(target, PURPLE_HI,
                             (FILL_X, FILL_Y, fill, 3))
            # The last third bleeds crimson.
            danger_w = int(FILL_W * 0.35)
            if fill > FILL_W - danger_w:
                start = max(FILL_X, FILL_X + fill - danger_w)
                pygame.draw.rect(target, CRIMSON,
                                 (start, FILL_Y, FILL_X + fill - start,
                                  FILL_H - 6))
                pygame.draw.rect(target, CRIMSON_HI,
                                 (start, FILL_Y, FILL_X + fill - start, 2))
            pygame.draw.rect(target, (240, 224, 255),
                             (FILL_X + fill - 2, FILL_Y, 2, FILL_H))
        # Phase thresholds: 70% and 35% of maximum health.
        for threshold in PHASE_THRESHOLDS:
            tx = FILL_X + int(FILL_W * threshold)
            pygame.draw.line(target, (18, 10, 24), (tx, FILL_Y),
                             (tx, FILL_Y + FILL_H), 2)
            pygame.draw.polygon(target, (226, 178, 255), [
                (tx, FILL_Y - 4), (tx + 3, FILL_Y - 1),
                (tx, FILL_Y + 2), (tx - 3, FILL_Y - 1),
            ])
        value = f"{int(round(boss.health.current)):04d}"
        draw_text(target, value, FILL_X + FILL_W - text_width(value, 1, 1),
                  FILL_Y - 13, 1, (222, 206, 240), spacing=1,
                  shadow=(4, 2, 6))
        pygame.draw.rect(target, (150, 118, 184),
                         (FILL_X - 2, FILL_Y - 2, FILL_W + 4, FILL_H + 4), 1)

    def _draw_phases(self, target: pygame.Surface, boss) -> None:
        # Three small diamonds mark the phases; the live one is bright.
        for i in range(3):
            cx = BAR_X + 22 + i * 14
            cy = BAR_Y + BAR_H - 11
            active = boss.phase >= i + 1
            color = ((214, 176, 255) if i == boss.phase - 1
                     else ((124, 88, 160) if active else (52, 42, 64)))
            pygame.draw.polygon(target, color, [
                (cx, cy - 4), (cx + 4, cy), (cx, cy + 4), (cx - 4, cy),
            ])
        draw_text(target, "WARDEN OF THE ASHEN SHRINE", BAR_X + 72,
                  BAR_Y + BAR_H - 15, 1, (118, 104, 136), spacing=1)

    def _draw_banner(self, target: pygame.Surface, boss) -> None:
        timer = getattr(boss, "phase_banner", 0.0)
        if timer <= 0.0:
            return
        alpha = int(255 * min(1.0, timer / 0.6))
        text = getattr(boss, "phase_banner_text", "")
        pulse = 1.0 + 0.04 * math.sin(self.time * 9.0)
        y = int(BAR_Y + BAR_H + 18)
        draw_text(target, text, SCREEN_W // 2, y, 2,
                  (222, 182, 255), spacing=3, shadow=(8, 3, 12),
                  alpha=alpha, center=True)
        width = int(text_width(text, 2, 3) * pulse)
        pygame.draw.line(target, (148, 96, 196, alpha),
                         (SCREEN_W // 2 - width // 2 - 18, y + 18),
                         (SCREEN_W // 2 - 26, y + 18), 1)
        pygame.draw.line(target, (148, 96, 196, alpha),
                         (SCREEN_W // 2 + 26, y + 18),
                         (SCREEN_W // 2 + width // 2 + 18, y + 18), 1)

    def _draw_intro_hint(self, target: pygame.Surface, boss) -> None:
        if getattr(boss, "state", "") != INTRO:
            return
        draw_text(target, "THE SHRINE HOLDS ITS BREATH",
                  SCREEN_W // 2, BAR_Y + BAR_H + 18, 1, (150, 128, 176),
                  spacing=3, center=True)


__all__ = ["BossHUD", "BAR_W", "BAR_H", "BAR_X", "BAR_Y"]
