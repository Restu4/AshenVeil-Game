"""Title screen: the first thing the player sees in the browser build.

The world keeps living behind the menu (ash, fog and the shrine glow), but the
menu itself is a fixed, self-contained screen.  Keyboard and mouse both work.
"""
from __future__ import annotations

import math

import pygame

from settings import SCREEN_H, SCREEN_W, SUBTITLE, TITLE
from scripts.pixel_font import draw_text, text_width
from scripts.ui.ui_common import accent_glow, button, panel

ITEMS = ("BEGIN DESCENT", "LEVEL SELECT", "QUIT")
ITEM_W, ITEM_H = 244, 34
ITEM_X = SCREEN_W // 2 - ITEM_W // 2
ITEM_Y = 388
ITEM_GAP = 44


class MainMenu:
    def __init__(self, progression) -> None:
        self.progression = progression
        self.index = 0
        self.time = 0.0
        self.message = ""
        self.message_timer = 0.0
        self._vignette = self._make_vignette()
        self._frame = self._make_frame()

    # ------------------------------------------------------------------
    @staticmethod
    def _make_vignette() -> pygame.Surface:
        surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        surf.fill((3, 2, 6, 132))
        for i in range(90):
            alpha = int(140 * (1.0 - i / 90.0))
            pygame.draw.rect(surf, (2, 1, 4, alpha),
                             (i, i, SCREEN_W - i * 2, SCREEN_H - i * 2), 1)
        return surf

    @staticmethod
    def _make_frame() -> pygame.Surface:
        surf = pygame.Surface((560, 92), pygame.SRCALPHA)
        panel(surf, pygame.Rect(0, 0, 560, 92), fill=(8, 6, 12, 178))
        return surf

    # ------------------------------------------------------------------
    def reset(self, index: int = 0) -> None:
        self.index = max(0, min(len(ITEMS) - 1, index))
        self.message = ""
        self.message_timer = 0.0

    @property
    def selected(self) -> str:
        return ITEMS[self.index]

    def item_rect(self, index: int) -> pygame.Rect:
        return pygame.Rect(ITEM_X, ITEM_Y + index * ITEM_GAP, ITEM_W, ITEM_H)

    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        self.time += dt
        self.message_timer = max(0.0, self.message_timer - dt)
        if self.message_timer <= 0.0:
            self.message = ""

    def handle_event(self, event: pygame.event.Event) -> str | None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.index = (self.index - 1) % len(ITEMS)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.index = (self.index + 1) % len(ITEMS)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER,
                               pygame.K_SPACE):
                return self._activate(self.selected)
            elif event.key == pygame.K_ESCAPE:
                return "quit"
        elif event.type == pygame.MOUSEMOTION:
            for i in range(len(ITEMS)):
                if self.item_rect(i).collidepoint(event.pos):
                    self.index = i
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i in range(len(ITEMS)):
                if self.item_rect(i).collidepoint(event.pos):
                    self.index = i
                    return self._activate(ITEMS[i])
        return None

    def _activate(self, item: str) -> str:
        if item == "BEGIN DESCENT":
            return "begin"
        if item == "LEVEL SELECT":
            return "select"
        return "quit"

    def flash(self, message: str, seconds: float = 2.2) -> None:
        self.message = message
        self.message_timer = seconds

    # ------------------------------------------------------------------
    def draw(self, target: pygame.Surface, assets=None) -> None:
        target.blit(self._vignette, (0, 0))
        pulse = 0.5 + 0.5 * math.sin(self.time * 1.4)

        accent_glow(target, (SCREEN_W // 2, 196), 280,
                    (118, 74, 168), int(26 + 12 * pulse))
        draw_text(target, TITLE, SCREEN_W // 2, 128, 7, (222, 212, 232),
                  spacing=3, shadow=(8, 4, 14), shadow_offset=(3, 4),
                  center=True)
        draw_text(target, "THE MOON IS DEAD", SCREEN_W // 2, 196, 2,
                  (148, 120, 184), spacing=5, center=True)

        draw_text(target, "A DARK FANTASY HACK AND SLASH", SCREEN_W // 2,
                  250, 1, (98, 86, 112), spacing=3, center=True)
        pygame.draw.line(target, (92, 70, 116),
                         (SCREEN_W // 2 - 230, 272),
                         (SCREEN_W // 2 + 230, 272), 1)
        pygame.draw.line(target, (46, 36, 62),
                         (SCREEN_W // 2 - 180, 275),
                         (SCREEN_W // 2 + 180, 275), 1)

        for i, label in enumerate(ITEMS):
            rect = self.item_rect(i)
            selected = i == self.index
            button(target, rect, label, selected,
                   accent=(182, 132, 248), enabled=(label != "QUIT"))
            if selected:
                draw_text(target, ">", rect.x - 18, rect.y + 12, 1,
                          (206, 168, 255), spacing=1)

        if self.message:
            draw_text(target, self.message, SCREEN_W // 2, 548, 1,
                      (204, 154, 164), spacing=2, center=True)

        # Profile line + controls.
        completed = sum(1 for level_id in self.progression.data.get("levels", {})
                        if self.progression.is_completed(level_id))
        profile = (f"PROFILE  LEVEL 01 AVAILABLE  ·  "
                   f"COMPLETED {completed}/4")
        draw_text(target, profile, SCREEN_W // 2, 572, 1, (116, 104, 130),
                  spacing=2, center=True)
        draw_text(target,
                  "WASD MOVE   SPACE DODGE   LMB ATTACK   RMB DASH   "
                  "Q E R F SKILLS",
                  SCREEN_W // 2, SCREEN_H - 38, 1, (92, 82, 104),
                  spacing=1, center=True)
        draw_text(target, "ENTER SELECT   ESC QUIT", SCREEN_W // 2,
                  SCREEN_H - 22, 1, (74, 66, 86), spacing=2, center=True)


__all__ = ["MainMenu"]
