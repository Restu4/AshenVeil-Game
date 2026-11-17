"""The level select: four atmospheric cards, real lock states, one Play action.

Cards are drawn from baked preview dioramas, so the screen is more than a list
of buttons while staying cheap to render.  Keyboard and mouse share the same
selection index; locked levels can be inspected but never entered.
"""
from __future__ import annotations

import math

import pygame

from settings import SCREEN_H, SCREEN_W
from scripts.level_config import LEVELS, get_level
from scripts.pixel_font import draw_text, text_width
from scripts.ui.preview_art import preview_surface
from scripts.ui.ui_common import (
    accent_glow,
    button,
    draw_lines,
    panel,
    status_chip,
    wrap_text,
)

CARD_W, CARD_H = 284, 420
CARD_GAP = 18
CARD_Y = 104
DETAIL = pygame.Rect(45, 548, SCREEN_W - 90, 138)
PLAY_BTN = pygame.Rect(DETAIL.right - 208, DETAIL.y + 50, 184, 38)

STATUS_COLORS = {
    "AVAILABLE": (196, 158, 240),
    "COMPLETE": (140, 204, 158),
    "LOCKED": (150, 106, 116),
    "UNLOCKED": (190, 172, 208),
}


class LevelSelect:
    def __init__(self, assets, progression) -> None:
        self.assets = assets
        self.progression = progression
        self.index = 0
        self.time = 0.0
        self.hover = -1
        self.message = ""
        self.message_timer = 0.0
        self._previews: dict[str, pygame.Surface] = {}
        self._dim = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        self._dim.fill((4, 3, 7, 156))
        self._vignette = self._make_vignette()

    # ------------------------------------------------------------------
    @staticmethod
    def _make_vignette() -> pygame.Surface:
        surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        for i in range(70):
            alpha = int(110 * (1.0 - i / 70.0))
            pygame.draw.rect(surf, (2, 1, 4, alpha),
                             (i, i, SCREEN_W - i * 2, SCREEN_H - i * 2), 1)
        return surf

    def _preview(self, level_id: str) -> pygame.Surface:
        surf = self._previews.get(level_id)
        if surf is None:
            level = get_level(level_id)
            surf = preview_surface(self.assets, level.preview, CARD_W - 12, 150)
            self._previews[level_id] = surf
        return surf

    @property
    def selected_id(self) -> str:
        return LEVELS[self.index].level_id

    def focus(self, level_id: str) -> None:
        for i, level in enumerate(LEVELS):
            if level.level_id == level_id:
                self.index = i
                return
        self.index = 0

    def card_rect(self, index: int) -> pygame.Rect:
        return pygame.Rect(45 + index * (CARD_W + CARD_GAP), CARD_Y,
                           CARD_W, CARD_H)

    def can_play(self, level_id: str) -> bool:
        return (get_level(level_id).playable
                and self.progression.is_playable(level_id))

    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        self.time += dt
        self.message_timer = max(0.0, self.message_timer - dt)
        if self.message_timer <= 0.0:
            self.message = ""

    def flash(self, message: str, seconds: float = 2.6) -> None:
        self.message = message
        self.message_timer = seconds

    def handle_event(self, event: pygame.event.Event) -> str | tuple | None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFT, pygame.K_a):
                self.index = (self.index - 1) % len(LEVELS)
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self.index = (self.index + 1) % len(LEVELS)
            elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                self.index = event.key - pygame.K_1
            elif event.key == pygame.K_ESCAPE:
                return "back"
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                return self._try_play()
        elif event.type == pygame.MOUSEMOTION:
            self.hover = -1
            for i in range(len(LEVELS)):
                if self.card_rect(i).collidepoint(event.pos):
                    self.hover = i
                    break
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if PLAY_BTN.collidepoint(event.pos) and self.can_play(self.selected_id):
                return ("play", self.selected_id)
            for i in range(len(LEVELS)):
                if self.card_rect(i).collidepoint(event.pos):
                    if self.index == i:
                        return self._try_play()
                    self.index = i
                    return None
        return None

    def _try_play(self) -> str | tuple:
        level = LEVELS[self.index]
        if not self.progression.is_unlocked(level.level_id):
            self.flash(self.progression.unlock_hint(level.level_id)
                       or "THIS PATH IS SEALED", 2.8)
            return "locked"
        if not level.playable:
            self.flash(level.coming_soon or "MAP NOT YET FORGED", 2.8)
            return "locked"
        return ("play", level.level_id)

    # ------------------------------------------------------------------
    def draw(self, target: pygame.Surface) -> None:
        target.blit(self._dim, (0, 0))
        self.draw_background(target)
        target.blit(self._vignette, (0, 0))
        self.draw_header(target)
        for i, level in enumerate(LEVELS):
            self.draw_card(target, i, level)
        self.draw_details(target)
        if self.message:
            draw_text(target, self.message, SCREEN_W // 2, DETAIL.y - 22, 1,
                      (214, 148, 160), spacing=2, center=True)

    # ------------------------------------------------------------------
    def draw_background(self, target: pygame.Surface) -> None:
        # Faint diagonal bands and drifting embers keep the screen alive.
        for i in range(0, SCREEN_W + SCREEN_H, 90):
            pygame.draw.line(target, (12, 10, 18),
                             (i, 0), (i - SCREEN_H, SCREEN_H), 2)
        level = LEVELS[self.index]
        accent_glow(target, (SCREEN_W // 2, 84), 300, level.accent,
                    int(16 + 8 * math.sin(self.time * 1.2)))

    def draw_header(self, target: pygame.Surface) -> None:
        draw_text(target, "CHOOSE YOUR DESCENT", SCREEN_W // 2, 34, 3,
                  (220, 210, 232), spacing=3, shadow=(6, 3, 10),
                  center=True)
        draw_text(target,
                  "ONLY THE ASHEN VILLAGE STANDS OPEN  ·  "
                  "COMPLETE A LEVEL TO UNLOCK THE ROAD BEYOND",
                  SCREEN_W // 2, 68, 1, (118, 104, 132), spacing=1,
                  center=True)
        pygame.draw.line(target, (62, 52, 74), (45, 88), (SCREEN_W - 45, 88), 1)

    # ------------------------------------------------------------------
    def draw_card(self, target: pygame.Surface, index: int,
                  level) -> None:
        selected = index == self.index
        hovered = index == self.hover
        rect = self.card_rect(index)
        if selected:
            rect = rect.move(0, -4)
        unlocked = self.progression.is_unlocked(level.level_id)
        completed = self.progression.is_completed(level.level_id)
        status = self.progression.status_label(level.level_id)
        accent = level.accent if unlocked else (92, 82, 102)

        if selected:
            accent_glow(target, (rect.centerx, rect.y + 120), 200,
                        accent, 24)
        panel(target, rect, fill=(10, 8, 15, 216),
              edge=accent if selected else
              ((96, 84, 112) if hovered else (54, 46, 66)),
              inner=(26, 22, 34) if selected else (20, 17, 26))

        # Preview with an accent wash and a hard pixel frame.
        preview = self._preview(level.level_id)
        px, py = rect.x + 6, rect.y + 6
        target.blit(preview, (px, py))
        wash = pygame.Surface(preview.get_size(), pygame.SRCALPHA)
        wash.fill((*accent, 20 if unlocked else 58))
        target.blit(wash, (px, py))
        pygame.draw.rect(target, accent if selected else (56, 48, 68),
                         (px - 1, py - 1, preview.get_width() + 2,
                          preview.get_height() + 2), 1)
        if not unlocked:
            self._draw_lock(target, (px, py, preview.get_width(),
                                     preview.get_height()))

        # Big level number and name.
        number = f"{level.number:02d}"
        draw_text(target, number, rect.x + 12, rect.y + 168, 3,
                  accent if unlocked else (104, 94, 116), spacing=2,
                  shadow=(4, 2, 8))
        name_x = rect.x + 12 + text_width(number, 3, 2) + 14
        draw_text(target, level.name, name_x, rect.y + 174, 1,
                  (218, 208, 230) if unlocked else (124, 116, 136),
                  spacing=1)
        draw_text(target, level.subtitle, name_x, rect.y + 187, 1,
                  (112, 98, 124), spacing=1)
        pygame.draw.line(target, (54, 44, 62), (rect.x + 12, rect.y + 204),
                         (rect.right - 12, rect.y + 204), 1)

        status_chip(target, rect.x + 12, rect.y + 214, status,
                    STATUS_COLORS.get(status, (160, 150, 170)))
        if completed:
            label = f"{self.progression.stages_cleared(level.level_id)}/4"
            draw_text(target, label,
                      rect.right - 12 - text_width(label, 1, 1),
                      rect.y + 218, 1, (120, 168, 134), spacing=1)

        draw_text(target, "BOSS", rect.x + 12, rect.y + 242, 1,
                  (110, 94, 124), spacing=1)
        boss_lines = wrap_text(level.boss_name, CARD_W - 24, 1)
        draw_lines(target, boss_lines, rect.x + 12, rect.y + 254, 1,
                   (184, 160, 198) if unlocked else (112, 102, 120),
                   line_gap=4)

        # Boss status line at the card foot.
        if not unlocked:
            hint = self.progression.unlock_hint(level.level_id)
            lines = wrap_text(hint or "SEALED", CARD_W - 24, 1)
            draw_lines(target, lines, rect.x + 12, rect.bottom - 42, 1,
                       (156, 110, 120), line_gap=3)
        elif completed:
            draw_text(target, "GUARDIAN SLAIN", rect.x + 12,
                      rect.bottom - 30, 1, (134, 188, 148), spacing=1)
        elif not level.playable:
            draw_text(target, level.coming_soon or "COMING SOON",
                      rect.x + 12, rect.bottom - 30, 1, (150, 138, 162),
                      spacing=1)
        else:
            draw_text(target, "THE VEIL WAITS", rect.x + 12,
                      rect.bottom - 30, 1, (156, 132, 184), spacing=1)

        if selected:
            pygame.draw.rect(target, accent,
                             (rect.x, rect.bottom - 2, rect.w, 2))

    # ------------------------------------------------------------------
    @staticmethod
    def _draw_lock(target: pygame.Surface, area: tuple[int, int, int, int]) -> None:
        x, y, w, h = area
        shade = pygame.Surface((w, h), pygame.SRCALPHA)
        shade.fill((5, 4, 9, 174))
        target.blit(shade, (x, y))
        cx, cy = x + w // 2, y + h // 2
        pygame.draw.rect(target, (128, 116, 140), (cx - 9, cy - 2, 18, 15), 0)
        pygame.draw.rect(target, (72, 62, 84), (cx - 9, cy - 2, 18, 15), 1)
        pygame.draw.arc(target, (128, 116, 140),
                        (cx - 7, cy - 13, 14, 18), 0.0, math.pi, 2)
        pygame.draw.circle(target, (54, 44, 64), (cx, cy + 4), 2)
        draw_text(target, "SEALED", cx, cy + 20, 1, (150, 122, 132),
                  spacing=2, center=True)

    # ------------------------------------------------------------------
    def draw_details(self, target: pygame.Surface) -> None:
        level = LEVELS[self.index]
        unlocked = self.progression.is_unlocked(level.level_id)
        playable = self.can_play(level.level_id)
        accent = level.accent if unlocked else (100, 90, 110)
        panel(target, DETAIL, fill=(9, 7, 13, 222), edge=(72, 60, 84))

        draw_text(target, f"LEVEL {level.level_id}  ·  {level.name}",
                  DETAIL.x + 16, DETAIL.y + 12, 2,
                  (220, 208, 232) if unlocked else (136, 126, 148),
                  spacing=2)
        boss = f"GUARDIAN: {level.boss_name} · {level.boss_subtitle}"
        draw_text(target, boss, DETAIL.x + 16, DETAIL.y + 34, 1,
                  (140, 116, 160) if unlocked else (108, 98, 116),
                  spacing=1)
        lines = wrap_text(level.description, 610, 1)
        draw_lines(target, lines, DETAIL.x + 16, DETAIL.y + 50, 1,
                   (166, 154, 178) if unlocked else (118, 108, 126),
                   line_gap=5)

        if unlocked:
            status = self.progression.status_label(level.level_id)
            chip_color = STATUS_COLORS.get(status, (170, 160, 180))
            status_chip(target, DETAIL.right - 224, DETAIL.y + 12, status,
                        chip_color, right=True)
            stages = self.progression.stages_cleared(level.level_id)
            draw_text(target, f"STAGES {stages}/4",
                      DETAIL.right - 224, DETAIL.y + 34, 1,
                      (122, 110, 138), spacing=1)
        else:
            hint = self.progression.unlock_hint(level.level_id)
            draw_text(target, hint, DETAIL.right - 224, DETAIL.y + 34, 1,
                      (150, 106, 116), spacing=1)

        label = "PLAY" if playable else ("SEALED" if not unlocked else "SOON")
        button(target, PLAY_BTN, label, playable,
               accent=accent, enabled=playable)
        if not playable:
            pygame.draw.line(target, (60, 50, 70),
                             (PLAY_BTN.x + 12, PLAY_BTN.centery),
                             (PLAY_BTN.right - 12, PLAY_BTN.centery), 1)

        draw_text(target, "ARROWS SELECT   ENTER PLAY   ESC BACK",
                  DETAIL.x + 16, DETAIL.bottom - 18, 1, (92, 82, 104),
                  spacing=1)


__all__ = ["LevelSelect"]
