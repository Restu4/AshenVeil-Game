"""Shared drawing helpers for the full-screen UI screens.

The bitmap font is fixed width, so wrapping is a simple character budget.  All
helpers are pure immediate-mode drawing; no screen owns any state the game
needs to persist.
"""
from __future__ import annotations

import pygame

from scripts.pixel_font import GLYPH_W, draw_text, text_width


def wrap_text(text: str, width: int, scale: int = 1,
              spacing: int = 1) -> list[str]:
    """Wrap uppercase paragraph text to a pixel width."""
    step = GLYPH_W * scale + spacing * scale
    budget = max(4, width // max(1, step))
    words = text.upper().split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = word if not current else f"{current} {word}"
        if len(trial) <= budget:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_lines(target: pygame.Surface, lines: list[str], x: int, y: int,
               scale: int = 1, color=(168, 156, 180), spacing: int = 1,
               line_gap: int = 6, centered: bool = False) -> int:
    """Draw wrapped lines and return the next free y."""
    step = 7 * scale + line_gap
    for i, line in enumerate(lines):
        draw_text(target, line, x, y + i * step, scale, color, spacing=spacing,
                  center=centered)
    return y + len(lines) * step


def panel(target: pygame.Surface, rect: pygame.Rect, fill=(10, 8, 15, 196),
          edge=(74, 64, 88), inner=(30, 26, 38),
          corners: bool = True) -> None:
    """Dark, bevelled panel used by the menus."""
    surf = pygame.Surface(rect.size, pygame.SRCALPHA)
    surf.fill(fill)
    pygame.draw.rect(surf, edge, (0, 0, rect.w, rect.h), 1)
    pygame.draw.rect(surf, inner, (2, 2, rect.w - 4, rect.h - 4), 1)
    if corners and rect.w > 20 and rect.h > 20:
        for cx, cy, dx, dy in ((2, 2, 1, 1), (rect.w - 3, 2, -1, 1),
                               (2, rect.h - 3, 1, -1),
                               (rect.w - 3, rect.h - 3, -1, -1)):
            pygame.draw.line(surf, (150, 136, 164), (cx, cy),
                             (cx + 7 * dx, cy), 1)
            pygame.draw.line(surf, (150, 136, 164), (cx, cy),
                             (cx, cy + 7 * dy), 1)
    target.blit(surf, rect.topleft)


def button(target: pygame.Surface, rect: pygame.Rect, label: str,
           selected: bool, accent=(174, 122, 244),
           enabled: bool = True) -> None:
    """Keyboard/mouse friendly menu button."""
    fill = (24, 18, 34, 236) if selected else (12, 10, 18, 210)
    edge = accent if selected else (58, 50, 70)
    surf = pygame.Surface(rect.size, pygame.SRCALPHA)
    surf.fill(fill)
    pygame.draw.rect(surf, edge, (0, 0, rect.w, rect.h), 1)
    if selected:
        pygame.draw.rect(surf, (edge[0] // 3, edge[1] // 3, edge[2] // 3),
                         (2, 2, rect.w - 4, rect.h - 4), 1)
        pygame.draw.rect(surf, accent, (0, rect.h // 2 - 7, 2, 14))
    target.blit(surf, rect.topleft)
    color = (224, 210, 240) if enabled else (96, 88, 106)
    if selected and enabled:
        color = (240, 230, 252)
    draw_text(target, label, rect.centerx, rect.centery - 3, 1, color,
              spacing=1, center=True)


def status_chip(target: pygame.Surface, x: int, y: int, label: str,
                color: tuple[int, int, int], right: bool = False) -> int:
    """Small outlined chip; returns its width."""
    width = text_width(label, 1, 1) + 12
    bx = x - width if right else x
    pygame.draw.rect(target, (8, 6, 12), (bx, y, width, 14))
    pygame.draw.rect(target, color, (bx, y, width, 14), 1)
    draw_text(target, label, bx + 6, y + 4, 1, color, spacing=1)
    return width


def accent_glow(target: pygame.Surface, center: tuple[int, int],
                radius: int, color=(150, 96, 220), alpha: int = 40) -> None:
    """Cheap layered glow, used behind selected cards and the menu title."""
    surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for i in range(6, 0, -1):
        r = radius * i // 6
        pygame.draw.circle(surf, (*color, max(2, alpha // (7 - i))),
                           (radius, radius), r)
    target.blit(surf, (center[0] - radius, center[1] - radius))


__all__ = [
    "accent_glow",
    "button",
    "draw_lines",
    "panel",
    "status_chip",
    "wrap_text",
]
