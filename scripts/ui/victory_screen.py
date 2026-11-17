"""Victory screen shown after the Hollow Guardian falls.

No auto-teleport, no forced reset: the player reads the result, sees Level 02
unlock, and chooses where to go next.  Both buttons return to the level select;
Continue preselects the newly opened road, Return preselects the level just
completed.
"""
from __future__ import annotations

import math

import pygame

from settings import SCREEN_H, SCREEN_W
from scripts.pixel_font import draw_text
from scripts.ui.ui_common import (
    accent_glow,
    button,
    draw_lines,
    panel,
    wrap_text,
)

PANEL = pygame.Rect(276, 156, 728, 392)
BTN_A = pygame.Rect(PANEL.x + 54, PANEL.bottom - 62, 286, 40)
BTN_B = pygame.Rect(PANEL.right - 54 - 286, PANEL.bottom - 62, 286, 40)


class VictoryScreen:
    def __init__(self, progression) -> None:
        self.progression = progression
        self.time = 0.0
        self.index = 0
        self.level = None
        self.next_level = None
        self.save_ok = True
        self._dim = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        self._dim.fill((3, 2, 6, 188))

    # ------------------------------------------------------------------
    def open(self, level, next_level, save_ok: bool = True) -> None:
        self.level = level
        self.next_level = next_level
        self.save_ok = save_ok
        self.index = 0
        self.time = 0.0

    def update(self, dt: float) -> None:
        self.time += dt

    @property
    def selected(self) -> str:
        return ("continue", "select")[self.index]

    # ------------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event) -> str | None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT,
                             pygame.K_d, pygame.K_TAB):
                self.index = (self.index + 1) % 2
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER,
                               pygame.K_SPACE):
                return self.selected
            elif event.key == pygame.K_ESCAPE:
                return "select"
        elif event.type == pygame.MOUSEMOTION:
            if BTN_A.collidepoint(event.pos):
                self.index = 0
            elif BTN_B.collidepoint(event.pos):
                self.index = 1
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if BTN_A.collidepoint(event.pos):
                self.index = 0
                return "continue"
            if BTN_B.collidepoint(event.pos):
                self.index = 1
                return "select"
        return None

    # ------------------------------------------------------------------
    def draw(self, target: pygame.Surface) -> None:
        if self.level is None:
            return
        target.blit(self._dim, (0, 0))
        pulse = 0.5 + 0.5 * math.sin(self.time * 1.6)
        accent_glow(target, (SCREEN_W // 2, PANEL.y + 66), 250,
                    self.level.accent, int(26 + 14 * pulse))
        panel(target, PANEL, fill=(8, 6, 12, 232), edge=(120, 92, 150),
              inner=(32, 26, 42))

        draw_text(target, "THE HOLLOW GUARDIAN FALLS", SCREEN_W // 2,
                  PANEL.y + 26, 2, (226, 210, 244), spacing=2,
                  shadow=(8, 4, 12), center=True)
        draw_text(target, f"LEVEL {self.level.level_id} COMPLETE",
                  SCREEN_W // 2, PANEL.y + 56, 3, (200, 158, 246),
                  spacing=4, shadow=(7, 3, 12), center=True)
        draw_text(target, self.level.name, SCREEN_W // 2, PANEL.y + 90, 1,
                  (150, 130, 174), spacing=4, center=True)

        pygame.draw.line(target, (84, 64, 104),
                         (PANEL.x + 70, PANEL.y + 112),
                         (PANEL.right - 70, PANEL.y + 112), 1)
        pygame.draw.line(target, (40, 31, 50),
                         (PANEL.x + 110, PANEL.y + 115),
                         (PANEL.right - 110, PANEL.y + 115), 1)

        story = (
            "The shrine is silent. The purple cracks go dark, the greatsword "
            "sinks into the stone, and the ash settles for the first time in "
            "years. Somewhere beyond the village, another road opens."
        )
        draw_lines(target, wrap_text(story, 600, 1), SCREEN_W // 2,
                   PANEL.y + 128, 1, (172, 158, 184), line_gap=6,
                   centered=True)

        # Unlock line.
        if self.next_level is not None:
            draw_text(target, f"LEVEL {self.next_level.level_id} · "
                              f"{self.next_level.name} UNLOCKED",
                      SCREEN_W // 2, PANEL.y + 198, 2, (152, 214, 168),
                      spacing=2, shadow=(4, 8, 5), center=True)
            draw_text(target, "THE ROAD CONTINUES · ITS MAP IS NOT YET FORGED",
                      SCREEN_W // 2, PANEL.y + 222, 1, (126, 142, 128),
                      spacing=2, center=True)
        else:
            draw_text(target, "THE LAST ROAD IS OPEN", SCREEN_W // 2,
                      PANEL.y + 205, 1, (152, 214, 168), spacing=3,
                      center=True)

        stages = self.progression.stages_cleared(self.level.level_id)
        stats = (f"STAGES CLEARED {stages}/4   ·   BOSS DEFEATED   ·   "
                 f"PROFILE {'SAVED' if self.save_ok else 'SAVE FAILED'}")
        draw_text(target, stats, SCREEN_W // 2, PANEL.y + 250, 1,
                  (138, 124, 156) if self.save_ok else (206, 132, 140),
                  spacing=1, center=True)

        button(target, BTN_A, "CONTINUE", self.index == 0,
               accent=(156, 210, 172))
        button(target, BTN_B, "RETURN TO LEVEL SELECT", self.index == 1,
               accent=(174, 132, 232))
        draw_text(target, "ARROWS CHOOSE   ENTER CONFIRM", SCREEN_W // 2,
                  PANEL.bottom - 16, 1, (88, 78, 100), spacing=2,
                  center=True)


__all__ = ["VictoryScreen"]
