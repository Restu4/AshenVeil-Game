"""Left inventory panel: live character sprite and seven equipment slots."""
from __future__ import annotations

import math

import pygame

from scripts.item_database import EQUIPMENT_SLOTS, SLOT_LABELS, rarity_color
from scripts.pixel_font import draw_text
from scripts.ui.item_icons import draw_item_icon
from scripts.ui.ui_common import panel

SLOT_SIZE = 60


class EquipmentPanel:
    """Pure immediate-mode drawing plus a slot hit test."""

    def __init__(self) -> None:
        self._rects: dict[str, pygame.Rect] = {}
        self._preview: pygame.Rect = pygame.Rect(0, 0, 0, 0)

    # ------------------------------------------------------------------
    def layout(self, rect: pygame.Rect) -> None:
        cx = rect.x + rect.w // 2
        self._preview = pygame.Rect(cx - 48, rect.y + 78, 96, 128)
        right_x = rect.right - SLOT_SIZE - 16
        left_x = rect.x + 16
        center_x = cx - SLOT_SIZE // 2
        positions = {
            "helmet": (right_x, rect.y + 58),
            "weapon": (left_x, rect.y + 100),
            "ring": (right_x, rect.y + 136),
            "necklace": (right_x, rect.y + 214),
            "armor": (center_x, rect.y + 220),
            "gloves": (left_x, rect.y + 220),
            "boots": (center_x, rect.y + 290),
        }
        self._rects = {
            slot: pygame.Rect(x, y, SLOT_SIZE, SLOT_SIZE)
            for slot, (x, y) in positions.items()
        }

    def slot_rect(self, slot: str) -> pygame.Rect | None:
        return self._rects.get(slot)

    def slot_at(self, pos: tuple[int, int]) -> str | None:
        for slot in EQUIPMENT_SLOTS:
            rect = self._rects.get(slot)
            if rect is not None and rect.collidepoint(pos):
                return slot
        return None

    # ------------------------------------------------------------------
    def draw(self, target: pygame.Surface, rect: pygame.Rect, player,
             equipment, time: float = 0.0) -> None:
        self.layout(rect)
        panel(target, rect, fill=(9, 7, 13, 232), edge=(74, 60, 92))
        draw_text(target, "EQUIPMENT", rect.x + 12, rect.y + 9, 1,
                  (206, 188, 232), spacing=1)
        pygame.draw.line(target, (76, 60, 96),
                         (rect.x + 10, rect.y + 22),
                         (rect.right - 10, rect.y + 22), 1)

        # Character preview: an actual scaled player animation frame, not a
        # stand-in rectangle.
        preview = self._preview
        glow = pygame.Surface((preview.w + 28, preview.h + 20), pygame.SRCALPHA)
        pulse = 0.6 + 0.4 * math.sin(time * 1.7)
        pygame.draw.ellipse(glow, (96, 62, 142, int(18 + 8 * pulse)),
                            (6, 34, glow.get_width() - 12, glow.get_height() - 54))
        target.blit(glow, (preview.x - 14, preview.y - 10))
        pygame.draw.rect(target, (40, 33, 52), preview, 1)
        frame = player.animator.image
        if frame is not None:
            portrait = pygame.transform.scale(frame, (preview.w, preview.h))
            target.blit(portrait, preview.topleft)
        draw_text(target, f"LEVEL {int(player.level):02d}", preview.centerx,
                  preview.bottom + 8, 1, (180, 162, 204), spacing=1,
                  center=True)

        for slot in EQUIPMENT_SLOTS:
            rect_slot = self._rects[slot]
            item = equipment.equipped_item(slot)
            color = item.rarity_color if item is not None else (64, 56, 74)
            target.fill((15, 12, 20), rect_slot)
            pygame.draw.rect(target, color, rect_slot, 1)
            pygame.draw.rect(target, (32, 27, 40), rect_slot.inflate(-4, -4), 1)
            if item is not None:
                draw_item_icon(target, item, rect_slot.x + 18, rect_slot.y + 5)
                if item.rarity == "legendary":
                    halo = pygame.Surface((36, 36), pygame.SRCALPHA)
                    pygame.draw.circle(halo, (158, 112, 226, 30), (18, 18), 17)
                    target.blit(halo, (rect_slot.x + 12, rect_slot.y))
            else:
                draw_text(target, "-", rect_slot.centerx - 3,
                          rect_slot.y + 20, 1, (72, 64, 82), spacing=1)
            label = SLOT_LABELS[slot]
            draw_text(target, label, rect_slot.centerx, rect_slot.bottom + 4,
                      1, (150, 140, 162) if item is None else color,
                      spacing=1, center=True)


__all__ = ["SLOT_SIZE", "EquipmentPanel"]
