"""ASHEN VEIL HUD: vitality, stamina, level, title and control hints."""
from __future__ import annotations

import math

import pygame

from settings import (
    BLOOD,
    BLOOD_DARK,
    BLOOD_LIGHT,
    BONE,
    SCREEN_H,
    SCREEN_W,
    SUBTITLE,
    TITLE,
)
from scripts.combat_ui import CombatUI
from scripts.pixel_font import draw_text, text_width


class HUD:
    def __init__(self) -> None:
        self.time = 0.0
        self.show_help = True
        self.help_timer = 0.0
        self._flash = 0.0

        self._panel = self._make_panel(348, 100)
        self._decorate_panel()
        self._title = self._make_title()
        self._help = self._make_help()
        self._build = self._make_build_label()
        self._intro = self._make_intro()
        self.combat_ui = CombatUI()

    # ------------------------------------------------------------------
    @staticmethod
    def _panel_frame(w: int, h: int) -> pygame.Surface:
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((10, 8, 15, 188))
        pygame.draw.rect(surf, (67, 58, 78, 225), (0, 0, w, h), 1)
        pygame.draw.rect(surf, (29, 25, 37, 220), (2, 2, w - 4, h - 4), 1)
        for cx, cy, dx, dy in ((2, 2, 1, 1), (w - 3, 2, -1, 1),
                               (2, h - 3, 1, -1), (w - 3, h - 3, -1, -1)):
            pygame.draw.line(surf, (147, 133, 157, 235), (cx, cy),
                             (cx + 9 * dx, cy), 1)
            pygame.draw.line(surf, (147, 133, 157, 235), (cx, cy),
                             (cx, cy + 9 * dy), 1)
        return surf

    def _make_panel(self, w: int, h: int) -> pygame.Surface:
        return self._panel_frame(w, h)

    def _decorate_panel(self) -> None:
        surf = self._panel
        pygame.draw.circle(surf, (8, 7, 12, 235), (44, 50), 33)
        pygame.draw.circle(surf, (101, 89, 114, 240), (44, 50), 33, 2)
        pygame.draw.circle(surf, (45, 35, 60, 235), (44, 50), 27, 1)
        pygame.draw.arc(surf, (166, 145, 196, 210), (5, 11, 78, 78), 0.5, 2.6, 1)
        pygame.draw.arc(surf, (129, 112, 158, 150), (5, 11, 78, 78), 3.6, 5.7, 1)
        for angle in (0.0, math.pi / 2, math.pi, math.pi * 1.5):
            x = 44 + math.cos(angle) * 30
            y = 50 + math.sin(angle) * 30
            pygame.draw.circle(surf, (185, 167, 205, 210), (int(x), int(y)), 2)
        draw_text(surf, "LV", 44, 26, 1, (137, 124, 153), spacing=1, center=True)
        draw_text(surf, "VITALITY", 90, 10, 1, (158, 142, 169), spacing=2)
        draw_text(surf, "STAMINA", 90, 44, 1, (137, 128, 105), spacing=2)
        draw_text(surf, "THE VEILED", 90, 74, 1, (99, 89, 111), spacing=2)

    def _make_title(self) -> pygame.Surface:
        surf = pygame.Surface((560, 70), pygame.SRCALPHA)
        draw_text(surf, TITLE, 280, 8, 4, BONE, spacing=2,
                  shadow=(0, 0, 0), shadow_offset=(2, 2), center=True)
        draw_text(surf, SUBTITLE, 280, 43, 1, (134, 120, 148),
                  spacing=5, center=True)
        pygame.draw.line(surf, (69, 59, 80), (152, 39), (204, 39), 1)
        pygame.draw.line(surf, (69, 59, 80), (356, 39), (408, 39), 1)
        return surf

    def _make_help(self) -> pygame.Surface:
        surf = self._panel_frame(444, 50)
        draw_text(surf, "LMB - ATTACK", 16, 10, 1, (176, 152, 200), spacing=1)
        draw_text(surf, "SPACE - DODGE", 146, 10, 1, (176, 152, 200), spacing=1)
        draw_text(surf, "SHIFT - RUN", 316, 10, 1, (146, 134, 158), spacing=1)
        draw_text(surf, "WASD - MOVE", 16, 28, 1, (146, 134, 158), spacing=1)
        draw_text(surf, "H - HINTS", 160, 28, 1, (112, 102, 124), spacing=1)
        draw_text(surf, "F1 - DEBUG", 278, 28, 1, (98, 90, 108), spacing=1)
        return surf

    def _make_build_label(self) -> pygame.Surface:
        label = "PROTOTYPE BUILD 0.2"
        w = text_width(label, 1, 1)
        surf = pygame.Surface((w, 9), pygame.SRCALPHA)
        draw_text(surf, label, 0, 0, 1, (72, 64, 82), spacing=1)
        return surf

    def _make_intro(self) -> pygame.Surface:
        surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        band = pygame.Surface((SCREEN_W, 244), pygame.SRCALPHA)
        for y in range(244):
            edge = min(y, 243 - y)
            a = int(150 * min(1.0, edge / 54.0))
            pygame.draw.line(band, (5, 4, 9, a), (0, y), (SCREEN_W, y))
        surf.blit(band, (0, 238))
        draw_text(surf, "A  DYING  VILLAGE", SCREEN_W // 2, 280, 1,
                  (158, 142, 176), spacing=3, center=True)
        draw_text(surf, TITLE, SCREEN_W // 2, 318, 7, BONE,
                  spacing=2, shadow=(0, 0, 0), shadow_offset=(2, 3), center=True)
        cy = 392
        pygame.draw.line(surf, (113, 97, 132, 200), (SCREEN_W // 2 - 260, cy),
                         (SCREEN_W // 2 - 22, cy), 1)
        pygame.draw.line(surf, (113, 97, 132, 200), (SCREEN_W // 2 + 22, cy),
                         (SCREEN_W // 2 + 260, cy), 1)
        pygame.draw.polygon(surf, (171, 151, 200, 230),
                            [(SCREEN_W // 2, cy - 5), (SCREEN_W // 2 + 6, cy),
                             (SCREEN_W // 2, cy + 5), (SCREEN_W // 2 - 6, cy)])
        draw_text(surf, SUBTITLE, SCREEN_W // 2, 410, 2, (172, 156, 189),
                  spacing=4, center=True)
        draw_text(surf, "THE MOON IS DEAD. THE VILLAGE DREAMS.",
                  SCREEN_W // 2, 448, 1, (115, 103, 128), spacing=2, center=True)
        return surf

    # ------------------------------------------------------------------
    def toggle_help(self) -> None:
        self.show_help = not self.show_help
        self.help_timer = 0.0

    def update(self, dt: float, player) -> None:
        self.time += dt
        self.help_timer += dt
        if self.help_timer > 13.0:
            self.show_help = False
        if player.exhausted:
            self._flash += dt
        else:
            self._flash = 0.0

    # ------------------------------------------------------------------
    def _bar(
        self,
        target: pygame.Surface,
        x: int,
        y: int,
        w: int,
        h: int,
        ratio: float,
        color: tuple[int, int, int],
        color_hi: tuple[int, int, int],
        color_lo: tuple[int, int, int],
        ticks: int = 0,
        glow: bool = False,
    ) -> None:
        ratio = max(0.0, min(1.0, ratio))
        pygame.draw.rect(target, (5, 4, 8), (x - 2, y - 2, w + 4, h + 4))
        pygame.draw.rect(target, (47, 41, 55), (x - 1, y - 1, w + 2, h + 2))
        pygame.draw.rect(target, (17, 14, 23), (x, y, w, h))
        fill_w = int(w * ratio)
        if fill_w > 0:
            pygame.draw.rect(target, color, (x, y, fill_w, h))
            hi = max(1, h // 3)
            pygame.draw.rect(target, color_hi, (x, y, fill_w, hi))
            pygame.draw.rect(target, color_lo, (x, y + h - hi, fill_w, hi))
            if glow and ratio > 0.05:
                pygame.draw.rect(target, (198, 108, 108),
                                 (x + fill_w - 2, y, 2, h))
        for i in range(1, ticks):
            tx = x + int(w * i / ticks)
            pygame.draw.line(target, (24, 20, 30), (tx, y), (tx, y + h - 1))
        pygame.draw.rect(target, (106, 94, 119), (x - 2, y - 2, w + 4, h + 4), 1)

    # ------------------------------------------------------------------
    def draw(self, target: pygame.Surface, player, enemy=None) -> None:
        target.blit(self._panel, (24, 22))
        draw_text(target, str(player.level), 68, 60, 3, BONE,
                  spacing=0, shadow=(0, 0, 0), center=True)

        bx, bw = 114, 232
        value = f"{int(player.health):03d}"
        value_w = text_width(value, 1, 1)
        draw_text(target, value, bx + bw - value_w, 32, 1,
                  (183, 160, 166), spacing=1)
        self._bar(target, bx, 43, bw, 15, player.health / player.health_max,
                  BLOOD, BLOOD_LIGHT, BLOOD_DARK, ticks=5, glow=True)

        if player.exhausted and int(self._flash * 5) % 2 == 0:
            draw_text(target, "SPENT",
                      bx + bw - text_width("SPENT", 1, 1), 66, 1,
                      (164, 102, 94), spacing=1)
        elif player.combat.blocked_flash > 0.0 and int(self.time * 12) % 2 == 0:
            draw_text(target, "NO STAMINA",
                      bx + bw - text_width("NO STAMINA", 1, 1), 66, 1,
                      (164, 102, 94), spacing=1)
        self._bar(target, bx, 78, bw - 22, 9, player.stamina.ratio,
                  (139, 146, 100), (177, 181, 126), (83, 92, 62), ticks=4)

        if self._intro_alpha() < 90:
            target.blit(self._title, ((SCREEN_W - 560) // 2, 12))

        self.combat_ui.draw_enemy(target, enemy)

        if self.show_help:
            target.blit(self._help, (24, SCREEN_H - 70))
        target.blit(self._build, (SCREEN_W - 24 - self._build.get_width(),
                                  SCREEN_H - 24))

        a = self._intro_alpha()
        if a > 0:
            self._intro.set_alpha(a)
            target.blit(self._intro, (0, 0))

        self.combat_ui.draw_death(target, player)

    def _intro_alpha(self) -> int:
        t = self.time
        if t < 0.9:
            return int(255 * (t / 0.9))
        if t < 3.7:
            return 255
        if t < 5.0:
            return int(255 * (1.0 - (t - 3.7) / 1.3))
        return 0
