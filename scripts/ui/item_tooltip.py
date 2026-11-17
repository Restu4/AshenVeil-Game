"""Selected-item detail card: description, attributes, comparison, actions."""
from __future__ import annotations

import pygame

from scripts.item_database import ItemDef
from scripts.player_stats import item_stat_lines
from scripts.pixel_font import draw_text
from scripts.ui.ui_common import button, panel, wrap_text

BUTTON_LABELS = (("equip", "EQUIP"), ("unequip", "UNEQUIP"),
                 ("use", "USE"), ("drop", "DROP"))


class ItemTooltip:
    """Draws item information and exposes the button hit rectangles."""

    def button_rects(self, rect: pygame.Rect) -> dict[str, pygame.Rect]:
        count = len(BUTTON_LABELS)
        width = 104
        gap = 10
        total = count * width + (count - 1) * gap
        start = rect.x + max(10, (rect.w - total) // 2)
        y = rect.bottom - 31
        return {
            key: pygame.Rect(start + index * (width + gap), y, width, 23)
            for index, (key, _) in enumerate(BUTTON_LABELS)
        }

    def enabled(self, item: ItemDef | None, inventory, equipment,
                source: str) -> dict[str, bool]:
        if item is None:
            return {key: False for key, _ in BUTTON_LABELS}
        equipped = equipment.is_equipped(item.item_id) if item.is_equipment else False
        in_bag = inventory.has(item.item_id)
        return {
            "equip": bool(item.is_equipment and in_bag and not equipped
                          and item.level_requirement <= getattr(
                              inventory.player, "level", 99)),
            "unequip": bool(item.is_equipment and source == "equip"),
            "use": bool(item.is_consumable and in_bag),
            "drop": bool(source == "bag" and in_bag),
        }

    def draw(self, target: pygame.Surface, rect: pygame.Rect,
             item: ItemDef | None, inventory, equipment, stats,
             source: str, confirm_drop: bool = False) -> None:
        panel(target, rect, fill=(11, 8, 16, 236), edge=(70, 58, 86))
        rects = self.button_rects(rect)
        state = self.enabled(item, inventory, equipment, source)

        if item is None:
            draw_text(target, "SELECT AN ITEM", rect.centerx, rect.y + 22, 1,
                      (150, 140, 162), spacing=1, center=True)
            for key, label in BUTTON_LABELS:
                button(target, rects[key], label, False, enabled=False)
            return

        color = item.rarity_color
        draw_text(target, item.name, rect.x + 14, rect.y + 10, 1, color,
                  spacing=1)
        draw_text(target, f"{item.rarity_label}  {item.slot_label}",
                  rect.x + 14, rect.y + 24, 1, (148, 138, 158), spacing=1)
        if item.level_requirement > 1:
            draw_text(target, f"LEVEL {item.level_requirement}",
                      rect.right - 14 - len(f"LEVEL {item.level_requirement}") * 6,
                      rect.y + 10, 1, (176, 162, 194), spacing=1)

        lines = wrap_text(item.description, rect.w - 28)
        for index, line in enumerate(lines[:2]):
            draw_text(target, line, rect.x + 14, rect.y + 39 + index * 12, 1,
                      (156, 148, 168), spacing=1)

        top = rect.y + 66
        half = rect.w // 2
        draw_text(target, "ATTRIBUTES", rect.x + 14, top, 1,
                  (188, 170, 214), spacing=1)
        for index, line in enumerate(item_stat_lines(item)[:5]):
            draw_text(target, line, rect.x + 14, top + 14 + index * 13, 1,
                      (206, 198, 220), spacing=1)

        if item.is_equipment:
            draw_text(target, "COMPARED TO EQUIPPED", rect.x + half + 8, top,
                      1, (188, 170, 214), spacing=1)
            comparison = equipment.comparison(item)
            if not comparison:
                draw_text(target, "NO CHANGE", rect.x + half + 8, top + 14, 1,
                          (142, 134, 154), spacing=1)
            for index, (key, delta) in enumerate(comparison[:5]):
                from scripts.player_stats import format_stat, stat_label
                sign = "+" if delta > 0 else "-"
                line = f"{stat_label(key)} {sign}{format_stat(key, abs(delta))}"
                tone = (126, 214, 142) if delta > 0 else (224, 112, 120)
                draw_text(target, line, rect.x + half + 8, top + 14 + index * 13,
                          1, tone, spacing=1)

        if confirm_drop:
            overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
            overlay.fill((8, 5, 12, 208))
            target.blit(overlay, rect.topleft)
            draw_text(target, "DROP THIS ITEM?", rect.centerx,
                      rect.y + rect.h // 2 - 28, 1, (232, 214, 240),
                      spacing=1, center=True)
            confirm = pygame.Rect(rect.centerx - 118, rect.y + rect.h // 2,
                                  108, 24)
            cancel = pygame.Rect(rect.centerx + 10, rect.y + rect.h // 2,
                                 108, 24)
            button(target, confirm, "CONFIRM", True, accent=(206, 108, 116))
            button(target, cancel, "CANCEL", False)
            self._confirm_rects = {"confirm": confirm, "cancel": cancel}
        else:
            self._confirm_rects = {}
            for key, label in BUTTON_LABELS:
                button(target, rects[key], label, state[key], enabled=state[key])

    @property
    def confirmation_rects(self) -> dict[str, pygame.Rect]:
        return getattr(self, "_confirm_rects", {})


__all__ = ["BUTTON_LABELS", "ItemTooltip"]
