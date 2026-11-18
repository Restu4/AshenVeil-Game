"""Merchant overlay: categories, priced stock, sales and confirmations.

Every transaction goes through ShopManager, which validates gold, stock,
capacity, level requirements and equipped-item protection.  This screen only
presents choices and never mutates the inventory itself.
"""
from __future__ import annotations

import math

import pygame

from scripts.item_database import get_item, RARITY_COLORS
from scripts.player_stats import item_stat_lines
from scripts.pixel_font import draw_text, text_width
from scripts.ui.ui_common import (
    accent_glow, button, draw_lines, panel, wrap_text,
)

WINDOW = pygame.Rect(70, 34, 1140, 652)
CATEGORY_X = WINDOW.x + 18
CATEGORY_Y = WINDOW.y + 82
CATEGORY_W = 188
CATEGORY_H = 36
CATEGORY_GAP = 7
LIST_X = WINDOW.x + 226
LIST_Y = WINDOW.y + 82
LIST_W = 456
ROW_H = 40
ROW_GAP = 3
MAX_ROWS = 11
DETAIL = pygame.Rect(WINDOW.x + 704, WINDOW.y + 82, 414, 470)
FOOTER = pygame.Rect(WINDOW.x + 18, WINDOW.bottom - 62, WINDOW.w - 36, 46)
BUY_TAB = pygame.Rect(WINDOW.x + 18, WINDOW.y + 40, 130, 30)
SELL_TAB = pygame.Rect(WINDOW.x + 154, WINDOW.y + 40, 130, 30)
CLOSE_RECT = pygame.Rect(WINDOW.right - 148, WINDOW.y + 40, 128, 30)
QTY_MINUS = pygame.Rect(DETAIL.x + 18, DETAIL.bottom - 78, 34, 30)
QTY_PLUS = pygame.Rect(DETAIL.x + 60, DETAIL.bottom - 78, 34, 30)
ACTION_RECT = pygame.Rect(DETAIL.x + 108, DETAIL.bottom - 78,
                          DETAIL.w - 126, 30)
CONFIRM_RECT = pygame.Rect(DETAIL.x + 40, DETAIL.y + 300, 150, 34)
CANCEL_RECT = pygame.Rect(DETAIL.right - 190, DETAIL.y + 300, 150, 34)
REVEAL_TIME = 0.16


class MerchantScreen:
    def __init__(self, shop, inventory, notify=None) -> None:
        self.shop = shop
        self.inventory = inventory
        self.notify = notify
        self.mode = "buy"
        self.category_index = 0
        self.selected = 0
        self.hover: str | None = None
        self.quantity = 1
        self.confirm = False
        self.reveal = 0.0
        self.time = 0.0

    # ------------------------------------------------------------------
    def open(self) -> None:
        self.reveal = 0.0
        self.time = 0.0
        self.mode = "buy"
        self.category_index = 0
        self.selected = 0
        self.quantity = 1
        self.confirm = False
        self.hover = None

    def update(self, dt: float) -> None:
        dt = max(0.0, dt)
        self.time += dt
        self.reveal = min(1.0, self.reveal + dt / REVEAL_TIME)

    # ------------------------------------------------------------------
    def entries(self) -> list:
        if self.mode == "sell":
            return list(self.inventory.entries)
        categories = self.shop.categories
        if not categories or self.category_index >= len(categories):
            return []
        return self.shop.entries_for(categories[self.category_index][0])

    def selected_entry(self):
        entries = self.entries()
        if not entries:
            return None
        return entries[min(self.selected, len(entries) - 1)]

    def item_id(self) -> str:
        entry = self.selected_entry()
        if entry is None:
            return ""
        return str(getattr(entry, "item_id", ""))

    def max_quantity(self) -> int:
        item_id = self.item_id()
        if not item_id:
            return 1
        if self.mode == "sell":
            return max(1, int(self.inventory.count(item_id)))
        entry = self.selected_entry()
        remaining = self.shop.remaining(item_id)
        return max(1, min(self.shop.max_quantity, remaining))

    def total_price(self) -> int:
        item_id = self.item_id()
        if not item_id:
            return 0
        unit = (self.shop.buy_price(item_id) if self.mode == "buy"
                else self.shop.sell_price(item_id))
        return unit * self.quantity

    def can_act(self) -> bool:
        item_id = self.item_id()
        if not item_id or self.total_price() <= 0:
            return False
        if self.mode == "sell":
            return self.shop.can_sell(item_id)
        return self.shop.remaining(item_id) > 0

    # ------------------------------------------------------------------
    def category_rects(self) -> list[pygame.Rect]:
        return [
            pygame.Rect(CATEGORY_X, CATEGORY_Y + index * (CATEGORY_H + CATEGORY_GAP),
                        CATEGORY_W, CATEGORY_H)
            for index in range(len(self.shop.categories))
        ]

    def row_rects(self) -> list[pygame.Rect]:
        return [
            pygame.Rect(LIST_X, LIST_Y + index * (ROW_H + ROW_GAP),
                        LIST_W, ROW_H)
            for index in range(min(MAX_ROWS, len(self.entries())))
        ]

    def _say(self, text: str) -> None:
        if callable(self.notify):
            self.notify(text)

    def _clamp_selection(self) -> None:
        count = len(self.entries())
        self.selected = max(0, min(self.selected, max(0, count - 1)))
        self.quantity = max(1, min(self.quantity, self.max_quantity()))

    def _commit(self) -> None:
        item_id = self.item_id()
        if not item_id:
            self._say("NOTHING SELECTED")
            self.confirm = False
            return
        if self.mode == "buy":
            ok = self.shop.buy(item_id, self.quantity)
            if ok:
                self._say(self.shop.last_message)
        else:
            # Selling always targets the selected inventory slot, not by ID,
            # so the exact stack (and its upgrade identity) is preserved.
            entry = self.selected_entry()
            index = self.inventory.entries.index(entry) if entry is not None else -1
            ok = self.shop.sell(index, self.quantity)
            if ok:
                self._say(self.shop.last_message)
        self.confirm = False
        self._clamp_selection()

    # ------------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event) -> str | None:
        if self.confirm:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.confirm = False
                    return None
                if event.key in (pygame.K_RETURN, pygame.K_SPACE,
                                 pygame.K_KP_ENTER):
                    self._commit()
                    return None
                return None
            if event.type == pygame.MOUSEMOTION:
                self.hover = ("confirm" if CONFIRM_RECT.collidepoint(event.pos)
                              else "cancel" if CANCEL_RECT.collidepoint(event.pos)
                              else None)
                return None
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if CANCEL_RECT.collidepoint(event.pos):
                    self.confirm = False
                elif CONFIRM_RECT.collidepoint(event.pos):
                    self._commit()
                return None
            return None

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_i):
                return "close"
            if event.key == pygame.K_TAB:
                self.mode = "sell" if self.mode == "buy" else "buy"
                self.selected = 0
                self.quantity = 1
                self.hover = None
                return None
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected = max(0, self.selected - 1)
                self.quantity = 1
                return None
            if event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = min(len(self.entries()) - 1, self.selected + 1)
                self.quantity = 1
                return None
            if event.key in (pygame.K_LEFT, pygame.K_a):
                if self.mode == "buy" and self.shop.categories:
                    self.category_index = max(0, self.category_index - 1)
                    self.selected = 0
                else:
                    self.quantity = max(1, self.quantity - 1)
                return None
            if event.key in (pygame.K_RIGHT, pygame.K_d):
                if self.mode == "buy" and self.shop.categories:
                    self.category_index = min(len(self.shop.categories) - 1,
                                              self.category_index + 1)
                    self.selected = 0
                else:
                    self.quantity = min(self.max_quantity(), self.quantity + 1)
                return None
            if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                if self.can_act():
                    self.confirm = True
                else:
                    self._say("NOT ENOUGH GOLD" if self.mode == "buy"
                              else "CANNOT SELL THAT")
                return None
            return None

        if event.type == pygame.MOUSEMOTION:
            self.hover = None
            pos = event.pos
            for index, rect in enumerate(self.category_rects()):
                if rect.collidepoint(pos):
                    self.hover = f"cat:{index}"
                    break
            for index, rect in enumerate(self.row_rects()):
                if rect.collidepoint(pos):
                    self.hover = f"row:{index}"
                    break
            if QTY_MINUS.collidepoint(pos):
                self.hover = "qty-"
            elif QTY_PLUS.collidepoint(pos):
                self.hover = "qty+"
            elif ACTION_RECT.collidepoint(pos):
                self.hover = "act"
            elif BUY_TAB.collidepoint(pos):
                self.hover = "buy"
            elif SELL_TAB.collidepoint(pos):
                self.hover = "sell"
            return None

        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return None
        pos = event.pos
        if CLOSE_RECT.collidepoint(pos):
            return "close"
        if BUY_TAB.collidepoint(pos):
            self.mode = "buy"
            self.selected = 0
            self.quantity = 1
            self.confirm = False
            return None
        if SELL_TAB.collidepoint(pos):
            self.mode = "sell"
            self.selected = 0
            self.quantity = 1
            self.confirm = False
            return None
        for index, rect in enumerate(self.category_rects()):
            if rect.collidepoint(pos):
                self.category_index = index
                self.selected = 0
                self.quantity = 1
                self.mode = "buy"
                return None
        for index, rect in enumerate(self.row_rects()):
            if rect.collidepoint(pos):
                self.selected = index
                self.quantity = 1
                return None
        if QTY_MINUS.collidepoint(pos):
            self.quantity = max(1, self.quantity - 1)
            return None
        if QTY_PLUS.collidepoint(pos):
            self.quantity = min(self.max_quantity(), self.quantity + 1)
            return None
        if ACTION_RECT.collidepoint(pos):
            if self.can_act():
                self.confirm = True
            else:
                self._say("NOT ENOUGH GOLD" if self.mode == "buy"
                          else "CANNOT SELL THAT")
            return None
        return None

    # ------------------------------------------------------------------
    def draw(self, target: pygame.Surface) -> None:
        dim = pygame.Surface(target.get_size(), pygame.SRCALPHA)
        dim.fill((5, 4, 9, int(190 * self.reveal)))
        target.blit(dim, (0, 0))
        panel(target, WINDOW, fill=(12, 9, 17, 248), edge=(148, 112, 82),
              inner=(34, 27, 44))

        draw_text(target, "THE MERCHANT", WINDOW.x + 18, WINDOW.y + 10, 2,
                  (236, 206, 158), spacing=1)
        gold = f"GOLD {self.inventory.gold:06d}"
        draw_text(target, gold, WINDOW.right - 20 - text_width(gold, 2, 1),
                  WINDOW.y + 12, 2, (238, 196, 96), spacing=1)
        button(target, BUY_TAB, "BUY", self.mode == "buy", accent=(222, 178, 92))
        button(target, SELL_TAB, "SELL", self.mode == "sell", accent=(222, 178, 92))
        button(target, CLOSE_RECT, "CLOSE", False)
        hint = "TAB MODE   G IN WORLD"
        draw_text(target, hint, WINDOW.x + 306, WINDOW.y + 48, 1,
                  (150, 138, 166), spacing=1)

        # Category rail.
        for index, (_, label) in enumerate(self.shop.categories):
            rect = self.category_rects()[index]
            active = index == self.category_index and self.mode == "buy"
            button(target, rect, label, active or self.hover == f"cat:{index}",
                   accent=(222, 178, 92))

        entries = self.entries()
        for index, entry in enumerate(entries[:MAX_ROWS]):
            rect = self.row_rects()[index]
            item = get_item(self._entry_id(entry))
            if item is None:
                continue
            selected = index == self.selected
            hovered = self.hover == f"row:{index}"
            if selected:
                accent_glow(target, rect.center, 26, item.rarity_color, alpha=30)
            fill = (24, 18, 30, 238) if selected else (12, 10, 18, 214)
            surf = pygame.Surface(rect.size, pygame.SRCALPHA)
            surf.fill(fill)
            pygame.draw.rect(surf, item.rarity_color if selected else (58, 50, 70),
                             (0, 0, rect.w, rect.h), 1)
            target.blit(surf, rect.topleft)
            if self.mode == "buy" and self.shop.remaining(item.item_id) <= 0:
                name_color = (104, 96, 112)
                name = f"{item.name}  SOLD"
            else:
                name_color = item.rarity_color if selected else (214, 204, 228)
                name = item.name
            draw_text(target, name[:44], rect.x + 10, rect.y + 6, 1,
                      name_color, spacing=1)
            price = (self.shop.buy_price(item.item_id) if self.mode == "buy"
                     else self.shop.sell_price(item.item_id))
            tag = f"{price} G"
            draw_text(target, tag, rect.right - 10 - text_width(tag, 1, 1),
                      rect.y + 6, 1, (232, 196, 108), spacing=1)
            meta = f"{item.slot_label} {item.rarity_label}"
            if self.mode == "sell":
                meta += f"  X{int(entry.quantity)}"
                if not self.shop.can_sell(item.item_id):
                    meta += "  EQUIPPED"
            elif not entry.limited:
                meta += "  UNLIMITED"
            else:
                meta += f"  LEFT {self.shop.remaining(item.item_id)}"
            draw_text(target, meta[:60], rect.x + 10, rect.y + 22, 1,
                      (140, 128, 156), spacing=1)
            if selected:
                pygame.draw.rect(target, item.rarity_color,
                                 (rect.x, rect.y, 3, rect.h))

        if not entries:
            draw_text(target, "NO STOCK IN THIS CATEGORY", LIST_X + 8,
                      LIST_Y + 12, 1, (140, 128, 156), spacing=1)

        self._draw_detail(target)

        panel(target, FOOTER, fill=(10, 8, 15, 238), edge=(70, 58, 86))
        notice = self.shop.last_message or "SELECT AN ITEM THEN CONFIRM"
        draw_text(target, notice[:96], FOOTER.x + 14, FOOTER.y + 16, 1,
                  (196, 176, 218), spacing=1)
        keys = "UP DOWN SELECT   LEFT RIGHT CATEGORY OR QTY   ENTER CONFIRM"
        draw_text(target, keys, FOOTER.x + 14, WINDOW.bottom - 24, 1,
                  (134, 122, 150), spacing=1)

        if self.confirm:
            self._draw_confirm(target)

    @staticmethod
    def _entry_id(entry) -> str:
        return str(getattr(entry, "item_id", ""))

    def _draw_detail(self, target: pygame.Surface) -> None:
        panel(target, DETAIL, fill=(10, 8, 15, 232), edge=(78, 64, 92))
        entry = self.selected_entry()
        item = get_item(self.item_id()) if entry is not None else None
        if item is None:
            draw_text(target, "NOTHING SELECTED", DETAIL.x + 16,
                      DETAIL.y + 16, 2, (214, 198, 236), spacing=1)
            return
        draw_text(target, item.name[:32], DETAIL.x + 16, DETAIL.y + 14, 2,
                  item.rarity_color, spacing=1)
        meta = f"{item.rarity_label}  {item.slot_label}"
        draw_text(target, meta, DETAIL.x + 16, DETAIL.y + 44, 1,
                  (178, 158, 204), spacing=1)
        pygame.draw.line(target, (78, 62, 98),
                         (DETAIL.x + 14, DETAIL.y + 62),
                         (DETAIL.right - 14, DETAIL.y + 62))
        lines = wrap_text(item.description, DETAIL.w - 32, 1)
        y = draw_lines(target, lines[:5], DETAIL.x + 16, DETAIL.y + 74, 1,
                       (176, 164, 190), line_gap=6)
        y += 12
        for line in item_stat_lines(item)[:7]:
            draw_text(target, line[:44], DETAIL.x + 16, y, 1,
                      (206, 194, 228), spacing=1)
            y += 18

        label = "BUY PRICE" if self.mode == "buy" else "SELL PRICE"
        draw_text(target, label, DETAIL.x + 16, DETAIL.y + 268, 1,
                  (140, 128, 156), spacing=1)
        unit = (self.shop.buy_price(item.item_id) if self.mode == "buy"
                else self.shop.sell_price(item.item_id))
        draw_text(target, f"{unit} G EACH", DETAIL.x + 16, DETAIL.y + 286, 1,
                  (238, 196, 108), spacing=1)

        button(target, QTY_MINUS, "-", self.hover == "qty-")
        button(target, QTY_PLUS, "+", self.hover == "qty+")
        count = f"X{self.quantity:02d}"
        draw_text(target, count, QTY_MINUS.right + 6, DETAIL.bottom - 70, 1,
                  (226, 212, 246), spacing=1)
        act = "BUY" if self.mode == "buy" else "SELL"
        button(target, ACTION_RECT, f"{act} {self.total_price()} G",
               self.hover == "act", accent=(222, 178, 92),
               enabled=self.can_act())

    def _draw_confirm(self, target: pygame.Surface) -> None:
        box = pygame.Rect(DETAIL.x + 16, DETAIL.y + 120,
                          DETAIL.w - 32, 224)
        panel(target, box, fill=(14, 10, 20, 252), edge=(226, 178, 92),
              inner=(44, 34, 52))
        item = get_item(self.item_id())
        name = item.name if item is not None else "ITEM"
        draw_text(target, "CONFIRM TRADE", box.x + 18, box.y + 18, 2,
                  (238, 206, 158), spacing=1)
        question = f"{name[:34]} X{self.quantity:02d}"
        draw_text(target, question, box.x + 18, box.y + 58, 1,
                  (224, 212, 240), spacing=1)
        verb = "BUY FOR" if self.mode == "buy" else "SELL FOR"
        draw_text(target, f"{verb} {self.total_price()} GOLD?", box.x + 18,
                  box.y + 82, 1, (232, 196, 108), spacing=1)
        if self.mode == "sell" and item is not None and self.upgrade_level(item.item_id):
            draw_text(target, "FORGE LEVEL INCLUDED IN PRICE", box.x + 18,
                      box.y + 106, 1, (180, 148, 220), spacing=1)
        button(target, CONFIRM_RECT, "CONFIRM", True, accent=(222, 178, 92))
        button(target, CANCEL_RECT, "CANCEL", False)

    def upgrade_level(self, item_id: str) -> int:
        upgrades = getattr(self.shop, "upgrades", None)
        if upgrades is None or not hasattr(upgrades, "level"):
            return 0
        return int(upgrades.level(item_id))


__all__ = ["MerchantScreen", "WINDOW"]
