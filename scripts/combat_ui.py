"""Combat-facing UI: the engaged enemy bar and the death veil."""
from __future__ import annotations

import pygame

from settings import SCREEN_H, SCREEN_W
from scripts.pixel_font import draw_text, text_width


class CombatUI:
    def __init__(self) -> None:
        self._enemy_panel = self._make_enemy_panel()
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
        draw_text(surf, "PRESS R OR CLICK TO RISE AGAIN", w // 2, 166, 1,
                  (186, 172, 198), spacing=2, center=True)
        return surf

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
