"""Blacksmith overlay: eligible gear, stat preview, material costs, confirmation.

The forge never fakes a stat: preview rows are produced by the same
``BlacksmithManager`` that builds the effective equipment definition, and the
upgrade itself is the only mutation.  Identity and rarity stay untouched.
"""
from __future__ import annotations

import math

import pygame

from scripts.item_database import get_item, STAT_KEYS
from scripts.player_stats import format_stat, stat_label
from scripts.pixel_font import draw_text, text_width
from scripts.ui.ui_common import (
    accent_glow, button, draw_lines, panel, wrap_text,
)

WINDOW = pygame.Rect(70, 34, 1140, 652)
LIST_X = WINDOW.x + 18
LIST_Y = WINDOW.y + 82
LIST_W = 470
ROW_H = 44
ROW_GAP = 4
MAX_ROWS = 11
DETAIL = pygame.Rect(WINDOW.x + 510, WINDOW.y + 82, 592, 470)
FOOTER = pygame.Rect(WINDOW.x + 18, WINDOW.bottom - 62, WINDOW.w - 36, 46)
CLOSE_RECT = pygame.Rect(WINDOW.right - 148, WINDOW.y + 40, 128, 30)
ACTION_RECT = pygame.Rect(DETAIL.x + 20, DETAIL.bottom - 62,
                          DETAIL.w - 40, 38)
CONFIRM_RECT = pygame.Rect(DETAIL.x + 60, DETAIL.y + 344, 200, 38)
CANCEL_RECT = pygame.Rect(DETAIL.right - 260, DETAIL.y + 344, 200, 38)
REVEAL_TIME = 0.16


class BlacksmithScreen:
    def __init__(self, blacksmith, inventory, notify=None) -> None:
        self.blacksmith = blacksmith
        self.inventory = inventory
        self.notify = notify
        self.selected = 0
        self.hover: str | None = None
        self.confirm = False
        self.reveal = 0.0
        self.time = 0.0

    # ------------------------------------------------------------------
    def open(self) -> None:
        self.reveal = 0.0
        self.time = 0.0
        self.selected = 0
        self.confirm = False
        self.hover = None

    def update(self, dt: float) -> None:
        dt = max(0.0, dt)
        self.time += dt
        self.reveal = min(1.0, self.reveal + dt / REVEAL_TIME)

    def eligible_entries(self) -> list:
        return [entry for entry in self.inventory.entries
                if self.blacksmith.eligible(entry.item_id)]

    def selected_entry(self):
        entries = self.eligible_entries()
        if not entries:
            return None
        return entries[min(self.selected, len(entries) - 1)]

    def item_id(self) -> str:
        entry = self.selected_entry()
        return str(getattr(entry, "item_id", "")) if entry is not None else ""

    def row_rects(self) -> list[pygame.Rect]:
        return [
            pygame.Rect(LIST_X, LIST_Y + index * (ROW_H + ROW_GAP), LIST_W, ROW_H)
            for index in range(min(MAX_ROWS, len(self.eligible_entries())))
        ]

    @staticmethod
    def _say_to(notify, text: str) -> None:
        if callable(notify):
            notify(text)

    def _say(self, text: str) -> None:
        self._say_to(self.notify, text)

    def _clamp(self) -> None:
        count = len(self.eligible_entries())
        self.selected = max(0, min(self.selected, max(0, count - 1)))

    def _commit(self) -> None:
        item_id = self.item_id()
        if item_id:
            self.blacksmith.upgrade(item_id)
            self._say(self.blacksmith.last_message)
        self.confirm = False
        self._clamp()

    # ------------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event) -> str | None:
        if self.confirm:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.confirm = False
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE,
                                   pygame.K_KP_ENTER):
                    self._commit()
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
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected = max(0, self.selected - 1)
                return None
            if event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = min(len(self.eligible_entries()) - 1,
                                    self.selected + 1)
                return None
            if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                ok, _ = self.blacksmith.can_upgrade(self.item_id())
                if ok:
                    self.confirm = True
                else:
                    self._say(self.blacksmith.last_message or "CANNOT FORGE")
                return None
            return None

        if event.type == pygame.MOUSEMOTION:
            self.hover = None
            for index, rect in enumerate(self.row_rects()):
                if rect.collidepoint(event.pos):
                    self.hover = f"row:{index}"
                    break
            if ACTION_RECT.collidepoint(event.pos):
                self.hover = "act"
            return None

        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return None
        pos = event.pos
        if CLOSE_RECT.collidepoint(pos):
            return "close"
        for index, rect in enumerate(self.row_rects()):
            if rect.collidepoint(pos):
                self.selected = index
                return None
        if ACTION_RECT.collidepoint(pos):
            ok, reason = self.blacksmith.can_upgrade(self.item_id())
            if ok:
                self.confirm = True
            else:
                self._say(reason)
            return None
        return None

    # ------------------------------------------------------------------
    def draw(self, target: pygame.Surface) -> None:
        dim = pygame.Surface(target.get_size(), pygame.SRCALPHA)
        dim.fill((5, 4, 9, int(190 * self.reveal)))
        target.blit(dim, (0, 0))
        panel(target, WINDOW, fill=(12, 9, 17, 248), edge=(196, 104, 78),
              inner=(34, 27, 44))

        draw_text(target, "THE BLACKSMITH", WINDOW.x + 18, WINDOW.y + 10, 2,
                  (238, 174, 132), spacing=1)
        gold = f"GOLD {self.inventory.gold:06d}"
        draw_text(target, gold, WINDOW.right - 20 - text_width(gold, 2, 1),
                  WINDOW.y + 12, 2, (238, 196, 96), spacing=1)
        button(target, CLOSE_RECT, "CLOSE", False)
        hint = "MAX +5   HIGHER LEVELS NEED GUARDIAN EMBERS"
        draw_text(target, hint, WINDOW.x + 320, WINDOW.y + 48, 1,
                  (170, 138, 132), spacing=1)

        entries = self.eligible_entries()
        for index, entry in enumerate(entries[:MAX_ROWS]):
            rect = self.row_rects()[index]
            item = get_item(entry.item_id)
            if item is None:
                continue
            level = self.blacksmith.level(item.item_id)
            selected = index == self.selected
            if selected:
                accent_glow(target, rect.center, 30, item.rarity_color, alpha=28)
            surf = pygame.Surface(rect.size, pygame.SRCALPHA)
            surf.fill((24, 18, 30, 236) if selected else (12, 10, 18, 214))
            pygame.draw.rect(surf, item.rarity_color if selected else (58, 50, 70),
                             (0, 0, rect.w, rect.h), 1)
            target.blit(surf, rect.topleft)
            name = f"{item.name} +{level}" if level else item.name
            color = item.rarity_color if selected else (214, 204, 228)
            draw_text(target, name[:40], rect.x + 10, rect.y + 7, 1,
                      color, spacing=1)
            meta = f"{item.slot_label}  {item.rarity_label}"
            if level >= self.blacksmith.max_level:
                meta += "  MAX"
            else:
                cost = self.blacksmith.next_cost(item.item_id)
                meta += f"  NEXT {cost['gold']} G"
            draw_text(target, meta[:62], rect.x + 10, rect.y + 26, 1,
                      (140, 128, 156), spacing=1)
            if selected:
                pygame.draw.rect(target, item.rarity_color,
                                 (rect.x, rect.y, 3, rect.h))
        if not entries:
            draw_text(target, "NO FORGEABLE GEAR IN SATCHEL", LIST_X + 8,
                      LIST_Y + 12, 1, (140, 128, 156), spacing=1)

        self._draw_detail(target)

        panel(target, FOOTER, fill=(10, 8, 15, 238), edge=(70, 58, 86))
        notice = self.blacksmith.last_message or "SELECT GEAR THEN CONFIRM"
        draw_text(target, notice[:110], FOOTER.x + 14, FOOTER.y + 16, 1,
                  (214, 176, 158), spacing=1)
        draw_text(target, "UP DOWN SELECT   ENTER FORGE   ESC CLOSE",
                  FOOTER.x + 14, WINDOW.bottom - 24, 1, (134, 122, 150))

        if self.confirm:
            self._draw_confirm(target)

    def _draw_detail(self, target: pygame.Surface) -> None:
        panel(target, DETAIL, fill=(10, 8, 15, 232), edge=(86, 62, 56))
        item_id = self.item_id()
        item = get_item(item_id) if item_id else None
        if item is None:
            draw_text(target, "NO GEAR SELECTED", DETAIL.x + 18,
                      DETAIL.y + 18, 2, (232, 186, 156), spacing=1)
            draw_text(target, "BRING WEAPONS OR ARMOR TO THE FORGE",
                      DETAIL.x + 18, DETAIL.y + 56, 1, (156, 132, 128))
            return

        level = self.blacksmith.level(item_id)
        current = self.blacksmith.effective_item(item)
        preview = self.blacksmith.preview_item(item)
        label = f"{item.name} +{level}" if level else item.name
        draw_text(target, label[:40], DETAIL.x + 18, DETAIL.y + 14, 2,
                  item.rarity_color, spacing=1)
        meta = f"{item.rarity_label}  {item.slot_label}  VALUE {current.value}"
        draw_text(target, meta[:64], DETAIL.x + 18, DETAIL.y + 44, 1,
                  (184, 156, 148), spacing=1)
        pygame.draw.line(target, (88, 62, 58), (DETAIL.x + 14, DETAIL.y + 64),
                         (DETAIL.right - 14, DETAIL.y + 64))
        lines = wrap_text(item.description, DETAIL.w - 36, 1)
        y = draw_lines(target, lines[:4], DETAIL.x + 18, DETAIL.y + 76, 1,
                       (174, 158, 152), line_gap=6)
        y += 8

        if self.blacksmith.is_max(item_id):
            draw_text(target, "FORGE LEVEL +5  MAXIMUM REACHED",
                      DETAIL.x + 18, y + 4, 1, (238, 196, 96), spacing=1)
        else:
            draw_text(target, "CURRENT", DETAIL.x + 18, y, 1,
                      (140, 128, 156), spacing=1)
            draw_text(target, "NEXT", DETAIL.x + 250, y, 1,
                      (140, 128, 156), spacing=1)
            y += 18
            for key in STAT_KEYS:
                now = current.stats.get(key, 0.0) if current else 0.0
                after = preview.stats.get(key, 0.0) if preview else 0.0
                if abs(after - now) < 1e-9 and abs(now) < 1e-9:
                    continue
                draw_text(target, stat_label(key), DETAIL.x + 18, y, 1,
                          (196, 180, 176), spacing=1)
                draw_text(target, format_stat(key, now), DETAIL.x + 168, y, 1,
                          (220, 206, 226), spacing=1)
                gain = after - now
                color = (126, 208, 146) if gain > 0 else (196, 180, 176)
                draw_text(target, format_stat(key, after, signed=gain > 0),
                          DETAIL.x + 252, y, 1, color, spacing=1)
                y += 18
            cost = self.blacksmith.next_cost(item_id)
            draw_text(target, f"COST {cost['gold']} GOLD", DETAIL.x + 18,
                      DETAIL.y + 278, 1, (238, 196, 96), spacing=1)
            materials = cost["materials"]
            if materials:
                parts = []
                for material_id, quantity in materials.items():
                    have = self.inventory.count(material_id)
                    mat = get_item(material_id)
                    short = have < quantity
                    parts.append(f"{mat.name if mat else material_id} "
                                 f"{have}/{quantity}")
                    if short:
                        parts.append("MISSING")
                draw_text(target, "  ".join(parts)[:70], DETAIL.x + 18,
                          DETAIL.y + 298, 1,
                          (126, 208, 146) if "MISSING" not in parts else (232, 128, 128))
            else:
                draw_text(target, "NO MATERIALS REQUIRED", DETAIL.x + 18,
                          DETAIL.y + 298, 1, (126, 208, 146))

        ok, reason = self.blacksmith.can_upgrade(item_id)
        button(target, ACTION_RECT,
               "MAX LEVEL" if self.blacksmith.is_max(item_id) else "UPGRADE",
               self.hover == "act", accent=(214, 132, 92), enabled=ok)
        if not ok and reason:
            draw_text(target, reason[:64], DETAIL.x + 20, DETAIL.bottom - 88, 1,
                      (220, 138, 132), spacing=1)
        glow = 20 + int(4 * (1.0 + math.sin(self.time * 4.0)))
        accent_glow(target, ACTION_RECT.center, glow, (196, 104, 78), alpha=24)

    def _draw_confirm(self, target: pygame.Surface) -> None:
        box = pygame.Rect(DETAIL.x + 20, DETAIL.y + 150,
                          DETAIL.w - 40, 276)
        panel(target, box, fill=(14, 10, 20, 252), edge=(226, 132, 92),
              inner=(48, 32, 44))
        item = get_item(self.item_id())
        level = self.blacksmith.level(self.item_id()) if item else 0
        name = f"{item.name} +{level}" if item else "ITEM"
        draw_text(target, "CONFIRM FORGE", box.x + 18, box.y + 18, 2,
                  (238, 178, 136), spacing=1)
        draw_text(target, f"{name[:40]} TO +{level + 1}", box.x + 18,
                  box.y + 62, 1, (230, 212, 236), spacing=1)
        cost = self.blacksmith.next_cost(self.item_id())
        draw_text(target, f"COST {cost['gold']} GOLD", box.x + 18,
                  box.y + 92, 1, (238, 196, 96), spacing=1)
        for index, (material_id, quantity) in enumerate(cost["materials"].items()):
            mat = get_item(material_id)
            have = self.inventory.count(material_id)
            line = f"{mat.name if mat else material_id} {have}/{quantity}"
            draw_text(target, line[:56], box.x + 18, box.y + 118 + index * 20, 1,
                      (126, 208, 146) if have >= quantity else (232, 128, 128))
        draw_text(target, "BONUS IS PERMANENT", box.x + 18, box.y + 216, 1,
                  (180, 148, 220), spacing=1)
        button(target, CONFIRM_RECT, "FORGE", True, accent=(214, 132, 92))
        button(target, CANCEL_RECT, "CANCEL", False)


__all__ = ["BlacksmithScreen", "WINDOW"]
