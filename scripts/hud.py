"""ASHEN VEIL HUD: compact vitality, void essence and control hints.

Phase 4 shrinks the interface hard so the village stays visible:

* HP        top-left, 204 x 13 px
* VOID      directly below HP, 172 x 9 px
* skills    four 42 px icons, bottom-right
* combo     a small block, upper-right
* engaged   a slim target bar, top-centre

All static chrome is baked once; per-frame drawing is a handful of rects and
cached bitmap-font blits.  This keeps the Pygbag frame cheap.
"""
from __future__ import annotations

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
from scripts.skill_hud import SkillHUD
from scripts.ui.boss_hud import BossHUD

# Public geometry (tests assert these stay compact).
HP_X, HP_Y, HP_W, HP_H = 20, 20, 204, 13
VOID_X, VOID_Y, VOID_W, VOID_H = 20, 44, 172, 9
DASH_X, DASH_Y, DASH_W, DASH_H = 20, 57, 120, 3
HELP_W, HELP_H = 438, 32


class HUD:
    def __init__(self) -> None:
        self.time = 0.0
        self.show_help = True
        self.help_timer = 0.0
        self._flash = 0.0

        self._help = self._make_help()
        self._build = self._make_build_label()
        self._intro = self._make_intro()
        self.combat_ui = CombatUI()
        self.skill_hud = SkillHUD()
        self.boss_hud = BossHUD()

    # ------------------------------------------------------------------
    @staticmethod
    def _mini_frame(w: int, h: int) -> pygame.Surface:
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((10, 8, 15, 168))
        pygame.draw.rect(surf, (70, 60, 80, 210), (0, 0, w, h), 1)
        pygame.draw.rect(surf, (28, 24, 36, 200), (2, 2, w - 4, h - 4), 1)
        for cx, cy, dx, dy in ((2, 2, 1, 1), (w - 3, 2, -1, 1),
                               (2, h - 3, 1, -1), (w - 3, h - 3, -1, -1)):
            pygame.draw.line(surf, (142, 128, 154, 220), (cx, cy),
                             (cx + 6 * dx, cy), 1)
            pygame.draw.line(surf, (142, 128, 154, 220), (cx, cy),
                             (cx, cy + 6 * dy), 1)
        return surf

    def _make_help(self) -> pygame.Surface:
        surf = self._mini_frame(HELP_W, HELP_H)
        draw_text(surf, "LMB ATTACK   C DASH   SPACE DODGE   SHIFT RUN",
                  10, 6, 1, (170, 154, 188), spacing=1)
        draw_text(surf, "Q BURST   E STEP   R SLASH   F ECLIPSE",
                  10, 18, 1, (182, 146, 236), spacing=1)
        return surf

    def _make_build_label(self) -> pygame.Surface:
        label = "BUILD 0.4"
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
        self.boss_hud.update(dt)
        if self.help_timer > 13.0:
            self.show_help = False

    # ------------------------------------------------------------------
    @staticmethod
    def _bar(
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
        pygame.draw.rect(target, (15, 12, 20), (x, y, w, h))
        fill_w = int(w * ratio)
        if fill_w > 0:
            pygame.draw.rect(target, color, (x, y, fill_w, h))
            hi = max(1, h // 3)
            pygame.draw.rect(target, color_hi, (x, y, fill_w, hi))
            pygame.draw.rect(target, color_lo, (x, y + h - hi, fill_w, hi))
            if glow and ratio > 0.04:
                pygame.draw.rect(target, (198, 108, 108),
                                 (x + fill_w - 2, y, 2, h))
        for i in range(1, ticks):
            tx = x + int(w * i / ticks)
            pygame.draw.line(target, (24, 20, 30), (tx, y), (tx, y + h - 1))
        pygame.draw.rect(target, (106, 94, 119), (x - 2, y - 2, w + 4, h + 4), 1)

    # ------------------------------------------------------------------
    def _draw_vitals(self, target: pygame.Surface, player, skills=None) -> None:
        draw_text(target, "HP", HP_X, 8, 1, (158, 96, 106), spacing=1,
                  shadow=(0, 0, 0))
        level = f"LV {player.level}"
        draw_text(target, level, HP_X + HP_W - text_width(level, 1, 1), 8, 1,
                  (126, 112, 140), spacing=1, shadow=(0, 0, 0))

        self._bar(target, HP_X, HP_Y, HP_W, HP_H,
                  player.health / max(1.0, player.health_max),
                  BLOOD, BLOOD_LIGHT, BLOOD_DARK, ticks=5, glow=True)
        value = f"{int(round(player.health)):03d}"
        draw_text(target, value,
                  HP_X + HP_W - 4 - text_width(value, 1, 1), HP_Y + 3, 1,
                  (214, 190, 196), spacing=1, shadow=(6, 2, 4))

        draw_text(target, "VOID", VOID_X, 35, 1, (146, 118, 190), spacing=1,
                  shadow=(0, 0, 0))
        ratio = 0.0
        if skills is not None:
            energy = skills.energy
            ratio = energy.ratio
            value = f"{int(round(energy.current)):03d}"
            draw_text(target, value,
                      VOID_X + VOID_W - text_width(value, 1, 1), 35, 1,
                      (206, 184, 240), spacing=1, shadow=(0, 0, 0))
        pygame.draw.rect(target, (5, 4, 8), (VOID_X - 2, VOID_Y - 2,
                                             VOID_W + 4, VOID_H + 4))
        pygame.draw.rect(target, (54, 42, 72), (VOID_X - 1, VOID_Y - 1,
                                               VOID_W + 2, VOID_H + 2))
        pygame.draw.rect(target, (16, 12, 24), (VOID_X, VOID_Y, VOID_W, VOID_H))
        fill = int(VOID_W * max(0.0, min(1.0, ratio)))
        if fill > 0:
            pygame.draw.rect(target, (92, 56, 148),
                             (VOID_X, VOID_Y, fill, VOID_H))
            pygame.draw.rect(target, (166, 118, 238),
                             (VOID_X, VOID_Y, fill, 3))
            pygame.draw.rect(target, (56, 32, 92),
                             (VOID_X, VOID_Y + VOID_H - 3, fill, 3))
            if ratio > 0.03:
                pygame.draw.rect(target, (232, 210, 255),
                                 (VOID_X + fill - 2, VOID_Y, 2, VOID_H))
        for i in range(1, 10):
            tx = VOID_X + int(VOID_W * i / 10)
            pygame.draw.line(target, (26, 20, 36), (tx, VOID_Y),
                             (tx, VOID_Y + VOID_H - 1))
        pygame.draw.rect(target, (116, 90, 158), (VOID_X - 2, VOID_Y - 2,
                                                 VOID_W + 4, VOID_H + 4), 1)

        # Dash availability, three pixels tall.
        dash = max(0.0, min(1.0, player.dash_ready_ratio))
        color = (126, 92, 186) if dash >= 1.0 else (58, 44, 82)
        pygame.draw.rect(target, (10, 8, 14), (DASH_X - 1, DASH_Y - 1,
                                               DASH_W + 2, DASH_H + 2))
        pygame.draw.rect(target, color, (DASH_X, DASH_Y,
                                         int(DASH_W * dash), DASH_H))

    # ------------------------------------------------------------------
    def draw(self, target: pygame.Surface, player, combat_manager=None,
             camera=None, skills=None, stage=None, boss=None) -> None:
        self._draw_vitals(target, player, skills)
        self.combat_ui.draw_combat(target, combat_manager, camera)
        self.skill_hud.draw(target, skills, player)
        if stage is not None:
            stage.stage_hud.draw(target, stage)
        self.boss_hud.draw(target, boss)

        if self.show_help:
            target.blit(self._help, (20, SCREEN_H - 20 - HELP_H))
        target.blit(self._build, (SCREEN_W - 20 - self._build.get_width(),
                                  SCREEN_H - 16))

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
