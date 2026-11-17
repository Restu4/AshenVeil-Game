"""Combat-facing UI: health bars, combo readout, crit flash and the death veil."""
from __future__ import annotations

import pygame

from settings import SCREEN_H, SCREEN_W
from scripts.combat_config import ATTACK_COUNT, COMBO_RESET_TIME, CRIT_FLASH_TIME
from scripts.pixel_font import draw_text, text_width


class CombatUI:
    def __init__(self) -> None:
        self._enemy_panel = self._make_enemy_panel()
        self._combo_panel = self._make_combo_panel()
        self._death_band = self._make_death_band()
        self._dim = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        self._dim.fill((4, 3, 8, 176))

    # ------------------------------------------------------------------
    @staticmethod
    def _mini_frame(w: int, h: int) -> pygame.Surface:
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((9, 7, 14, 194))
        pygame.draw.rect(surf, (64, 55, 76, 225), (0, 0, w, h), 1)
        pygame.draw.rect(surf, (27, 23, 35, 222), (2, 2, w - 4, h - 4), 1)
        for cx, cy, dx, dy in ((2, 2, 1, 1), (w - 3, 2, -1, 1),
                               (2, h - 3, 1, -1), (w - 3, h - 3, -1, -1)):
            pygame.draw.line(surf, (141, 126, 156, 235), (cx, cy),
                             (cx + 8 * dx, cy), 1)
            pygame.draw.line(surf, (141, 126, 156, 235), (cx, cy),
                             (cx, cy + 8 * dy), 1)
        return surf

    def _make_enemy_panel(self) -> pygame.Surface:
        surf = self._mini_frame(372, 56)
        draw_text(surf, "FALLEN KNIGHT", 16, 9, 1, (150, 130, 172), spacing=2)
        draw_text(surf, "UNDEAD SENTINEL", 16, 22, 1, (92, 82, 105), spacing=2)
        return surf

    def _make_combo_panel(self) -> pygame.Surface:
        surf = self._mini_frame(190, 86)
        draw_text(surf, "COMBO", 12, 8, 1, (150, 130, 172), spacing=2)
        draw_text(surf, "HITS", 142, 8, 1, (104, 92, 118), spacing=1)
        return surf

    def _make_death_band(self) -> pygame.Surface:
        w, h = 760, 220
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        band = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(h):
            edge = min(y, h - 1 - y)
            alpha = int(196 * min(1.0, edge / 52.0))
            pygame.draw.line(band, (4, 3, 7, alpha), (0, y), (w, y))
        surf.blit(band, (0, 0))
        pygame.draw.line(surf, (116, 44, 52, 210), (w // 2 - 300, 52),
                         (w // 2 - 44, 52), 1)
        pygame.draw.line(surf, (116, 44, 52, 210), (w // 2 + 44, 52),
                         (w // 2 + 300, 52), 1)
        draw_text(surf, "YOU DIED", w // 2, 66, 7, (168, 72, 78),
                  spacing=3, shadow=(0, 0, 0), shadow_offset=(2, 3), center=True)
        draw_text(surf, "THE VEIL CLAIMS ANOTHER", w // 2, 128, 1,
                  (146, 128, 160), spacing=4, center=True)
        draw_text(surf, "PRESS ENTER OR CLICK TO RISE AGAIN", w // 2, 166, 1,
                  (186, 172, 198), spacing=2, center=True)
        return surf

    # ------------------------------------------------------------------
    # Engaged target bar (top centre)
    # ------------------------------------------------------------------
    def draw_enemy(self, target: pygame.Surface, enemy) -> None:
        if enemy is None:
            return
        x = (SCREEN_W - 372) // 2
        y = 92
        target.blit(self._enemy_panel, (x, y))

        bx, bw = x + 16, 340
        value = f"{max(0, int(round(enemy.health.current))):03d}"
        value_w = text_width(value, 1, 1)
        draw_text(target, value, bx + bw - value_w, y + 9, 1,
                  (176, 156, 190), spacing=1)

        bar_y = y + 34
        ratio = enemy.health.ratio
        pygame.draw.rect(target, (5, 4, 8), (bx - 2, bar_y - 2, bw + 4, 14))
        pygame.draw.rect(target, (45, 39, 54), (bx - 1, bar_y - 1, bw + 2, 12))
        pygame.draw.rect(target, (15, 12, 20), (bx, bar_y, bw, 10))
        fill = int(bw * ratio)
        if fill > 0:
            pygame.draw.rect(target, (86, 54, 128), (bx, bar_y, fill, 10))
            pygame.draw.rect(target, (128, 84, 186), (bx, bar_y, fill, 4))
            pygame.draw.rect(target, (58, 36, 88), (bx, bar_y + 6, fill, 4))
            pygame.draw.rect(target, (196, 156, 255), (bx + fill - 2,
                                                       bar_y, 2, 10))
        for i in range(1, 5):
            tx = bx + int(bw * i / 5)
            pygame.draw.line(target, (26, 21, 33), (tx, bar_y),
                             (tx, bar_y + 9))
        pygame.draw.rect(target, (104, 90, 120), (bx - 2, bar_y - 2,
                                                  bw + 4, 14), 1)

    # ------------------------------------------------------------------
    # Floating enemy bars
    # ------------------------------------------------------------------
    def draw_enemy_bars(self, target: pygame.Surface, combat, camera) -> None:
        if combat is None or camera is None:
            return
        player = combat.player
        for enemy in combat.enemies:
            if not enemy.alive:
                continue
            distance = abs(enemy.x - player.x) + abs(enemy.y - player.y)
            damaged = enemy.health.current < enemy.health.maximum - 0.01
            if not damaged and enemy.aggro_timer <= 0.0 and distance > 620.0:
                continue
            sx, sy = camera.to_screen(enemy.x, enemy.y - 62)
            if sx < -70 or sx > SCREEN_W + 70 or sy < -30 or sy > SCREEN_H + 30:
                continue
            w, h = 56, 5
            x = int(sx) - w // 2
            y = int(sy)
            pygame.draw.rect(target, (5, 4, 8), (x - 1, y - 1, w + 2, h + 2))
            pygame.draw.rect(target, (28, 23, 35), (x, y, w, h))
            fill = int(w * enemy.health.ratio)
            if fill > 0:
                pygame.draw.rect(target, (96, 60, 140), (x, y, fill, h))
                pygame.draw.rect(target, (176, 132, 240), (x, y, fill, 2))
            for i in range(1, 4):
                tx = x + int(w * i / 4)
                pygame.draw.line(target, (20, 16, 26), (tx, y),
                                 (tx, y + h - 1))
            if enemy.flash_timer > 0.0:
                pygame.draw.rect(target, (226, 206, 255), (x, y, w, h), 1)

    # ------------------------------------------------------------------
    # Combo readout + critical flash
    # ------------------------------------------------------------------
    def draw_combo(self, target: pygame.Surface, player) -> None:
        combo = player.combat
        if combo.combo_count <= 0:
            return
        x = SCREEN_W - 24 - self._combo_panel.get_width()
        y = 118
        target.blit(self._combo_panel, (x, y))

        decay = COMBO_RESET_TIME if COMBO_RESET_TIME > 0 else 1.0
        fade = min(1.0, combo.combo_decay / decay)
        color = (238, 208, 255) if fade > 0.28 else (170, 148, 186)
        number = str(combo.combo_count)
        scale = 4 if combo.combo_count < 10 else 3
        draw_text(target, number, x + 12, y + 20, scale, color,
                  spacing=1, shadow=(4, 2, 8))
        draw_text(target, "HIT" if combo.combo_count == 1 else "HITS",
                  x + 142, y + 40, 1, (150, 130, 172), spacing=1)

        stage = combo.attack_stage
        py = y + 68
        for index in range(ATTACK_COUNT):
            px = x + 12 + index * 32
            filled = index < stage
            pygame.draw.rect(target, (8, 6, 12), (px - 1, py - 1, 26, 8))
            pygame.draw.rect(target, (42, 34, 52), (px, py, 24, 6))
            if filled:
                if index == ATTACK_COUNT - 1:
                    pygame.draw.rect(target, (206, 158, 255), (px, py, 24, 6))
                else:
                    pygame.draw.rect(target, (112, 74, 168), (px, py, 24, 6))
            pygame.draw.rect(target, (66, 55, 78), (px - 1, py - 1, 26, 8), 1)
        draw_text(target, "CHAIN", x + 12, y + 76, 1, (96, 86, 110),
                  spacing=1)

    def draw_crit(self, target: pygame.Surface, player) -> None:
        timer = player.combat.crit_flash
        if timer <= 0.0:
            return
        k = min(1.0, timer / max(0.001, CRIT_FLASH_TIME))
        alpha = int(255 * min(1.0, k * 2.2))
        pulse = int(4 * (1.0 - k))
        draw_text(target, "CRITICAL", SCREEN_W // 2, 196 - pulse, 2,
                  (255, 226, 158), spacing=3, shadow=(8, 4, 10),
                  alpha=alpha, center=True)
        half = 120
        pygame.draw.line(target, (198, 158, 86),
                         (SCREEN_W // 2 - half, 222), (SCREEN_W // 2 - 34, 222))
        pygame.draw.line(target, (198, 158, 86),
                         (SCREEN_W // 2 + 34, 222), (SCREEN_W // 2 + half, 222))

    # ------------------------------------------------------------------
    def draw_combat(self, target: pygame.Surface, combat, camera) -> None:
        self.draw_enemy_bars(target, combat, camera)
        if combat is None:
            return
        self.draw_enemy(target, combat.engaged)
        self.draw_combo(target, combat.player)
        self.draw_crit(target, combat.player)

    # ------------------------------------------------------------------
    def draw_death(self, target: pygame.Surface, player) -> None:
        if not player.combat.dead:
            return
        fade = min(1.0, max(0.0, player.combat.death_time / 0.85))
        self._dim.set_alpha(int(255 * fade))
        target.blit(self._dim, (0, 0))
        self._death_band.set_alpha(int(255 * fade))
        target.blit(self._death_band,
                    ((SCREEN_W - self._death_band.get_width()) // 2,
                     (SCREEN_H - self._death_band.get_height()) // 2 - 10))
