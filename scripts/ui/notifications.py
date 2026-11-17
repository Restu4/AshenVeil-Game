"""Small transient pickup/use/equip toasts, kept out of the compact HUD."""
from __future__ import annotations

from dataclasses import dataclass

import pygame

from scripts.pixel_font import draw_text, text_width
from settings import SCREEN_H, SCREEN_W

MAX_TOASTS = 5


@dataclass
class Toast:
    text: str
    timer: float
    total: float
    color: tuple[int, int, int]


class Notifications:
    def __init__(self) -> None:
        self.items: list[Toast] = []

    def push(self, text: str, color=(214, 196, 238), duration: float = 2.4) -> None:
        clean = str(text).upper()
        if not clean:
            return
        if self.items and self.items[-1].text == clean:
            self.items[-1].timer = self.items[-1].total
            return
        self.items.append(Toast(clean[:64], duration, duration, color))
        if len(self.items) > MAX_TOASTS:
            self.items.pop(0)

    def update(self, dt: float) -> None:
        dt = max(0.0, dt)
        for toast in self.items:
            toast.timer = max(0.0, toast.timer - dt)
        self.items[:] = [toast for toast in self.items if toast.timer > 0.0]

    def clear(self) -> None:
        self.items.clear()

    def draw(self, target: pygame.Surface) -> None:
        base_y = SCREEN_H - 116
        for index, toast in enumerate(self.items):
            life = toast.timer / max(0.01, toast.total)
            fade = min(1.0, life * 4.0)
            alpha = int(232 * fade)
            width = text_width(toast.text, 1, 1) + 20
            x = SCREEN_W // 2 - width // 2
            y = base_y - index * 22
            surf = pygame.Surface((width, 18), pygame.SRCALPHA)
            surf.fill((10, 7, 14, int(190 * fade)))
            pygame.draw.rect(surf, (*toast.color, int(190 * fade)),
                             (0, 0, width, 18), 1)
            target.blit(surf, (x, y))
            draw_text(target, toast.text, x + 10, y + 5, 1, toast.color,
                      spacing=1, alpha=alpha)


__all__ = ["MAX_TOASTS", "Notifications", "Toast"]
