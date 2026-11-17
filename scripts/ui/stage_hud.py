"""Small stage / objective indicator plus stage-transition banners.

This stays under the vitality bars in the top-left and never grows into a
quest log: one stage line, one objective line, four tiny stage pips.
"""
from __future__ import annotations

import math

import pygame

from scripts.pixel_font import draw_text, text_width
from scripts.ui.ui_common import panel

PANEL = pygame.Rect(20, 66, 300, 42)


class StageHUD:
    def __init__(self) -> None:
        self.time = 0.0

    def update(self, dt: float) -> None:
        self.time += dt

    def draw(self, target: pygame.Surface, level) -> None:
        if level is None:
            return
        panel(target, PANEL, fill=(9, 7, 13, 190),
              edge=(62, 52, 74), inner=(24, 20, 31))
        label = (f"STAGE {level.stage_number}/{level.stage_total}  ·  "
                 f"{level.stage_name}")
        draw_text(target, label, PANEL.x + 9, PANEL.y + 7, 1,
                  (188, 168, 210), spacing=1)
        draw_text(target, level.objective, PANEL.x + 9, PANEL.y + 21, 1,
                  (128, 114, 146), spacing=1)

        # Four pips: cleared stages filled, current stage pulsing.
        for i in range(level.stage_total):
            cx = PANEL.right - 14 - (level.stage_total - 1 - i) * 13
            cy = PANEL.y + 13
            cleared = i < level.stages_cleared
            current = i == level.stage_number - 1
            if cleared:
                color = (150, 196, 160)
            elif current:
                pulse = 0.5 + 0.5 * math.sin(self.time * 4.0)
                color = (int(150 + 70 * pulse), int(110 + 60 * pulse),
                         int(200 + 55 * pulse))
            else:
                color = (58, 48, 68)
            pygame.draw.rect(target, color, (cx - 3, cy - 3, 7, 7))
            pygame.draw.rect(target, (16, 12, 20), (cx - 3, cy - 3, 7, 7), 1)

        # Objective distance/remaining, when the level script exposes it.
        extra = level.objective_detail
        if extra:
            draw_text(target, extra, PANEL.x + 9,
                      PANEL.y + 31, 1, (108, 96, 122), spacing=1)

    # ------------------------------------------------------------------
    def draw_banner(self, target: pygame.Surface, level) -> None:
        if level is None or level.banner_timer <= 0.0:
            return
        timer = level.banner_timer
        total = max(0.001, level.banner_total)
        k = timer / total
        # Fade in over the first 0.35 s, hold, fade out.
        alpha = int(255 * min(1.0, (1.0 - k) * 4.0, k * 3.0))
        alpha = max(0, min(255, alpha))
        title = level.banner_title
        subtitle = level.banner_subtitle
        y = 106
        draw_text(target, title, 640, y, 2, (226, 206, 248), spacing=3,
                  shadow=(8, 4, 12), alpha=alpha, center=True)
        width = text_width(title, 2, 3)
        pygame.draw.line(target, (112, 78, 148),
                         (640 - width // 2 - 22, y + 17),
                         (640 - width // 2 - 6, y + 17), 1)
        pygame.draw.line(target, (112, 78, 148),
                         (640 + width // 2 + 6, y + 17),
                         (640 + width // 2 + 22, y + 17), 1)
        if subtitle:
            draw_text(target, subtitle, 640, y + 23, 1, (150, 128, 174),
                      spacing=2, alpha=alpha, center=True)


__all__ = ["StageHUD"]
