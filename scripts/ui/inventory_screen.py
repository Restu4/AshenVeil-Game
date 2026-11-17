"""Full inventory overlay: grid, equipment, character, details and actions.

The overlay is drawn directly onto the fixed 1280x720 canvas; the existing
``Game._ui_event`` already maps window mouse coordinates, so no extra scaling
logic lives here.  Gameplay is paused by ``Game`` while this screen is open.
"""
from __future__ import annotations

import pygame

from scripts.item_database import ITEM_DIR  # noqa: F401  (data dir is shipped)
from scripts.item_database import get_item
from scripts.pixel_font import draw_text, text_width
from scripts.ui.character_status import CharacterStatus
from scripts.ui.equipment_panel import EquipmentPanel
from scripts.ui.item_icons import draw_item_icon
from scripts.ui.item_tooltip import ItemTooltip
from scripts.ui.ui_common import button, panel

WINDOW = pygame.Rect(64, 36, 1152, 648)
LEFT_RECT = pygame.Rect(80, 84, 360, 376)
STATUS_RECT = pygame.Rect(80, 468, 360, 152)
RIGHT_RECT = pygame.Rect(452, 84, 748, 536)
DETAILS_RECT = pygame.Rect(464, 432, 724, 180)
FOOTER_RECT = pygame.Rect(80, 628, 1120, 52)

GRID_COLS = 7
GRID_ROWS = 4
CELL = 68
STEP = 74
GRID_X = RIGHT_RECT.x + (RIGHT_RECT.w - GRID_COLS * STEP + (STEP - CELL)) // 2
GRID_Y = RIGHT_RECT.y + 42
CLOSE_RECT = pygame.Rect(FOOTER_RECT.right - 138, FOOTER_RECT.y + 11,
                         126, 30)

REVEAL_TIME = 0.16


class InventoryScreen:
    def __init__(self, player, inventory, equipment, stats, skills,
                 notify=None, on_drop=None) -> None:
        self.player = player
        self.inventory = inventory
        self.equipment = equipment
        self.stats = stats
        self.skills = skills
        self.notify = notify
        self.on_drop = on_drop
        self.equipment_panel = EquipmentPanel()
        self.status_panel = CharacterStatus()
        self.tooltip = ItemTooltip()
        self.selected: tuple[str, object] | None = None
        self.hover: int | None = None
        self.confirm_drop = False
        self.time = 0.0
        self.reveal = 0.0
        self.cells = [
            pygame.Rect(GRID_X + col * STEP, GRID_Y + row * STEP, CELL, CELL)
            for row in range(GRID_ROWS) for col in range(GRID_COLS)
        ]

    # ------------------------------------------------------------------
    def open(self) -> None:
        self.reveal = 0.0
        self.time = 0.0
        self.confirm_drop = False
        if self.selected is None:
            self.selected = ("bag", 0) if self.inventory.entries else None

    def update(self, dt: float) -> None:
        self.time += max(0.0, dt)
        self.reveal = min(1.0, self.reveal + max(0.0, dt) / REVEAL_TIME)

    def _say(self, text: str) -> None:
        if callable(self.notify):
            self.notify(text)

    # ------------------------------------------------------------------
    def selected_item(self):
        if self.selected is None:
            return None
        source, key = self.selected
        if source == "bag":
            entry = self.inventory.entry_at(int(key))
            return entry.item if entry is not None else None
        if source == "equip":
            return self.equipment.equipped_item(str(key))
        return None

    # ------------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event) -> str | None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_i):
                return "close"
            return None
        if event.type == pygame.MOUSEMOTION:
            self.hover = self._cell_at(event.pos)
            return None
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return None
        pos = event.pos

        if CLOSE_RECT.collidepoint(pos):
            return "close"

        if self.confirm_drop:
            rects = self.tooltip.confirmation_rects
            if rects.get("cancel") is not None and rects["cancel"].collidepoint(pos):
                self.confirm_drop = False
                return None
            if rects.get("confirm") is not None and rects["confirm"].collidepoint(pos):
                self._confirm_drop()
                self.confirm_drop = False
                return None
            return None

        slot = self.equipment_panel.slot_at(pos)
        if slot is not None:
            self.selected = ("equip", slot)
            return None

        cell = self._cell_at(pos)
        if cell is not None:
            self.selected = ("bag", cell)
            return None

        item = self.selected_item()
        rects = self.tooltip.button_rects(DETAILS_RECT)
        state = self.tooltip.enabled(item, self.inventory, self.equipment,
                                     self.selected[0] if self.selected else "")
        for key, rect in rects.items():
            if not rect.collidepoint(pos) or not state[key]:
                continue
            if key == "equip":
                self.equipment.equip(item.item_id)
            elif key == "unequip":
                slot = self.selected[1] if self.selected else None
                self.equipment.unequip(str(slot))
            elif key == "use":
                self.inventory.use(item.item_id)
            elif key == "drop":
                self.confirm_drop = True
            return None
        return None

    def _cell_at(self, pos: tuple[int, int]) -> int | None:
        for index, rect in enumerate(self.cells):
            if rect.collidepoint(pos):
                return index
        return None

    def _confirm_drop(self) -> None:
        if self.selected is None:
            return
        source, key = self.selected
        if source == "equip":
            self.equipment.unequip(str(key))
            return
        index = int(key)
        entry = self.inventory.entry_at(index)
        if entry is None:
            return
        item_id, quantity = entry.item_id, entry.quantity
        self.inventory.drop(index)
        if callable(self.on_drop):
            self.on_drop(item_id, quantity)
        self.selected = None

    # ------------------------------------------------------------------
    def draw(self, target: pygame.Surface) -> None:
        # Fade only: keeping every panel at a fixed rect means mouse hit tests
        # stay exact from the first frame.
        dy = 0
        alpha = int(190 * self.reveal)
        dim = pygame.Surface(target.get_size(), pygame.SRCALPHA)
        dim.fill((5, 4, 9, alpha))
        target.blit(dim, (0, 0))

        window = WINDOW.move(0, dy)
        left = LEFT_RECT.move(0, dy)
        status = STATUS_RECT.move(0, dy)
        right = RIGHT_RECT.move(0, dy)
        details = DETAILS_RECT.move(0, dy)
        footer = FOOTER_RECT.move(0, dy)

        panel(target, window, fill=(12, 9, 17, 246), edge=(88, 68, 108),
              inner=(34, 27, 44))
        draw_text(target, "INVENTORY", window.x + 18, window.y + 10, 2,
                  (226, 208, 244), spacing=1)
        hint = "I CLOSE   ESC BACK"
        draw_text(target, hint, window.right - 18 - text_width(hint, 1, 1),
                  window.y + 15, 1, (150, 138, 166), spacing=1)

        self.equipment_panel.draw(target, left, self.player, self.equipment,
                                  self.time)
        self.status_panel.draw(target, status, self.player, self.stats,
                               self.skills)

        panel(target, right, fill=(9, 7, 13, 234), edge=(70, 58, 86))
        draw_text(target, "SATCHEL", right.x + 12, right.y + 9, 1,
                  (204, 186, 228), spacing=1)
        count_label = f"{self.inventory.used:02d}/{self.inventory.capacity:02d}"
        draw_text(target, count_label,
                  right.right - 12 - text_width(count_label, 1, 1),
                  right.y + 9, 1, (150, 138, 166), spacing=1)
        self._draw_grid(target, dy)

        self.tooltip.draw(target, details, self.selected_item(),
                          self.inventory, self.equipment, self.stats,
                          self.selected[0] if self.selected else "",
                          confirm_drop=self.confirm_drop)

        panel(target, footer, fill=(10, 8, 15, 238), edge=(70, 58, 86))
        draw_text(target, f"GOLD {self.inventory.gold:05d}", footer.x + 18,
                  footer.y + 18, 1, (232, 190, 96), spacing=1)
        carrying = (f"CARRYING {self.inventory.used}"
                    f"/{self.inventory.capacity}")
        draw_text(target, carrying, footer.x + 250, footer.y + 18, 1,
                  (176, 164, 190), spacing=1)
        draw_text(target, "G PICK UP   I CLOSE", footer.x + 470,
                  footer.y + 18, 1, (150, 140, 166), spacing=1)
        close = CLOSE_RECT.move(0, dy)
        button(target, close, "CLOSE (I)", True)

    def _draw_grid(self, target: pygame.Surface, dy: int) -> None:
        for index, rect in enumerate(self.cells[:self.inventory.capacity]):
            cell = rect.move(0, dy)
            entry = self.inventory.entry_at(index)
            item = entry.item if entry is not None else None
            selected = (self.selected is not None
                        and self.selected[0] == "bag"
                        and self.selected[1] == index)
            hovered = self.hover == index
            color = item.rarity_color if item is not None else (52, 45, 62)
            if selected:
                color = (222, 196, 250)
            elif hovered and item is not None:
                color = (168, 148, 196)
            target.fill((16, 13, 22), cell)
            pygame.draw.rect(target, color, cell, 1)
            pygame.draw.rect(target, (30, 25, 38), cell.inflate(-4, -4), 1)
            if item is None:
                continue
            draw_item_icon(target, item, cell.x + 22, cell.y + 8, scale=1)
            if entry is not None and entry.quantity > 1:
                label = f"X{entry.quantity}"
                draw_text(target, label, cell.right - 4 - len(label) * 6,
                          cell.bottom - 14, 1, (226, 216, 238), spacing=1)
            if self.equipment.is_equipped(item.item_id):
                pygame.draw.circle(target, (196, 148, 255),
                                   (cell.x + 8, cell.y + 8), 3)


__all__ = [
    "CLOSE_RECT", "DETAILS_RECT", "GRID_COLS", "GRID_ROWS", "LEFT_RECT",
    "RIGHT_RECT", "STATUS_RECT", "WINDOW", "InventoryScreen",
]
