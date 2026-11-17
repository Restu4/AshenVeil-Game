"""Dedicated Void skill tree overlay: three branches, unlocked states, costs.

Every card maps to one node in ``skill_tree_config``.  Buying a card mutates the
shared ExpManager through SkillTreeManager, so requirements, points and saves
are checked in exactly one place.
"""
from __future__ import annotations

import pygame

from scripts.pixel_font import draw_text, text_width
from scripts.skill_tree_config import BRANCHES, nodes_for_branch
from scripts.ui.skill_tree_manager_view import draw_node_card
from scripts.ui.ui_common import button, panel, wrap_text

WINDOW = pygame.Rect(64, 36, 1152, 648)
COLUMN_W = 360
COLUMN_GAP = 20
COLUMN_X = (80, 460, 840)
HEADER_Y = 84
CARD_Y = 140
CARD_H = 104
CARD_GAP = 10
FOOTER = pygame.Rect(80, 628, 1120, 52)
CLOSE_RECT = pygame.Rect(FOOTER.right - 138, FOOTER.y + 11, 126, 30)

CARD_RECTS: dict[str, pygame.Rect] = {}
for _branch_index, (_code, _label, _color) in enumerate(BRANCHES):
    for _node_index, _node in enumerate(nodes_for_branch(_code)):
        CARD_RECTS[_node.node_id] = pygame.Rect(
            COLUMN_X[_branch_index],
            CARD_Y + _node_index * (CARD_H + CARD_GAP),
            COLUMN_W,
            CARD_H,
        )

REVEAL_TIME = 0.16


class SkillTreeScreen:
    def __init__(self, player, tree, notify=None) -> None:
        self.player = player
        self.tree = tree
        self.notify = notify
        self.reveal = 0.0
        self.hover: str | None = None

    # ------------------------------------------------------------------
    def open(self) -> None:
        self.reveal = 0.0
        self.hover = None

    def update(self, dt: float) -> None:
        self.reveal = min(1.0, self.reveal + max(0.0, dt) / REVEAL_TIME)

    def _say(self, text: str) -> None:
        if callable(self.notify):
            self.notify(text)

    # ------------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event) -> str | None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_t):
                return "close"
            return None
        if event.type == pygame.MOUSEMOTION:
            self.hover = None
            for node_id, rect in CARD_RECTS.items():
                if rect.collidepoint(event.pos):
                    self.hover = node_id
                    break
            return None
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return None
        if CLOSE_RECT.collidepoint(event.pos):
            return "close"
        for node_id, rect in CARD_RECTS.items():
            if not rect.collidepoint(event.pos):
                continue
            ok, message = self.tree.purchase(node_id)
            self._say(message)
            return None
        return None

    # ------------------------------------------------------------------
    def draw(self, target: pygame.Surface) -> None:
        dim = pygame.Surface(target.get_size(), pygame.SRCALPHA)
        dim.fill((5, 4, 9, int(190 * self.reveal)))
        target.blit(dim, (0, 0))

        panel(target, WINDOW, fill=(12, 9, 17, 246), edge=(88, 68, 108),
              inner=(34, 27, 44))
        draw_text(target, "VOID SKILL TREE", WINDOW.x + 18, WINDOW.y + 10, 2,
                  (226, 208, 244), spacing=1)
        hint = "T CLOSE   ESC BACK"
        draw_text(target, hint,
                  WINDOW.right - 18 - text_width(hint, 1, 1),
                  WINDOW.y + 15, 1, (150, 138, 166), spacing=1)

        for column, (code, label, color) in enumerate(BRANCHES):
            head = pygame.Rect(COLUMN_X[column], HEADER_Y, COLUMN_W, 42)
            panel(target, head, fill=(14, 10, 21, 232), edge=color)
            draw_text(target, f"BRANCH {code}  {label}", head.x + 12,
                      head.y + 13, 1, color, spacing=1)
            for node in nodes_for_branch(code):
                draw_node_card(
                    target,
                    CARD_RECTS[node.node_id],
                    node,
                    self.tree.state(node.node_id),
                    self.hover == node.node_id,
                )

        panel(target, FOOTER, fill=(10, 8, 15, 238), edge=(70, 58, 86))
        points = self.tree.points
        draw_text(target, f"SKILL POINTS {points:02d}", FOOTER.x + 18,
                  FOOTER.y + 18, 1, (232, 190, 96), spacing=1)
        draw_text(target, "CLICK A NODE TO UNLOCK", FOOTER.x + 300,
                  FOOTER.y + 18, 1, (150, 140, 166), spacing=1)
        draw_text(target, "LEVEL AND PREREQUISITES APPLY", FOOTER.x + 580,
                  FOOTER.y + 18, 1, (150, 140, 166), spacing=1)
        button(target, CLOSE_RECT, "CLOSE (T)", True)


__all__ = ["CARD_RECTS", "CLOSE_RECT", "SkillTreeScreen"]
