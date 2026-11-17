"""Node card renderer shared by the skill tree screen."""
from __future__ import annotations

import pygame

from scripts.pixel_font import draw_text, text_width
from scripts.skill_tree_config import NODES_BY_ID
from scripts.skill_tree_manager import LOCKED, OWNED
from scripts.ui.ui_common import panel, wrap_text

STATE_COLOR = {
    OWNED: (236, 194, 106),
    "AVAILABLE": (198, 154, 244),
    LOCKED: (96, 88, 108),
}
STATE_LABEL = {
    OWNED: "OWNED",
    "AVAILABLE": "AVAILABLE",
    LOCKED: "LOCKED",
}


def draw_node_card(target: pygame.Surface, rect: pygame.Rect, node,
                   state: str, hovered: bool = False) -> None:
    color = STATE_COLOR.get(state, STATE_COLOR[LOCKED])
    fill = (18, 13, 26, 236) if state != LOCKED else (12, 10, 16, 226)
    if hovered and state == "AVAILABLE":
        fill = (28, 19, 40, 244)
    panel(target, rect, fill=fill, edge=color, inner=(32, 26, 42))

    draw_text(target, node.name, rect.x + 12, rect.y + 9, 1, color, spacing=1)
    label = STATE_LABEL.get(state, "LOCKED")
    draw_text(target, label, rect.right - 12 - text_width(label, 1, 1),
              rect.y + 9, 1, color, spacing=1)
    pygame.draw.line(target, (74, 62, 90),
                     (rect.x + 10, rect.y + 23),
                     (rect.right - 10, rect.y + 23), 1)

    lines = wrap_text(node.effect, rect.w - 26)[:2]
    for index, line in enumerate(lines):
        draw_text(target, line, rect.x + 12, rect.y + 31 + index * 13, 1,
                  (196, 182, 212) if state != LOCKED else (124, 114, 136),
                  spacing=1)

    need = f"LEVEL {node.level_req}"
    if node.requires:
        first = NODES_BY_ID.get(node.requires[0])
        need += f"  NEEDS {first.name if first else node.requires[0].upper()}"
    draw_text(target, need[:56], rect.x + 12, rect.bottom - 17, 1,
              (140, 128, 156), spacing=1)
    cost = f"COST {node.cost}"
    draw_text(target, cost, rect.right - 12 - text_width(cost, 1, 1),
              rect.bottom - 17, 1, (214, 178, 112), spacing=1)


__all__ = ["draw_node_card"]
