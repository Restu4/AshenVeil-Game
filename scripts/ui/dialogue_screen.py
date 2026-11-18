"""Conversation overlay for the three Ashen Village survivors.

The portrait is a real NPC sprite frame, the text comes from data, and every
choice is routed through DialogueManager so flags, seen IDs and saves stay in
one authority.  A short reveal and a breathing selection glow keep the screen
alive without affecting gameplay (the world is frozen while it is open).
"""
from __future__ import annotations

import math

import pygame

from scripts.pixel_font import draw_text, text_width
from scripts.ui.ui_common import (
    accent_glow, button, draw_lines, panel, wrap_text,
)

WINDOW = pygame.Rect(88, 336, 1104, 336)
PORTRAIT = pygame.Rect(WINDOW.x + 20, WINDOW.y + 54, 168, 168)
TEXT_RECT = pygame.Rect(PORTRAIT.right + 26, WINDOW.y + 54,
                        WINDOW.right - PORTRAIT.right - 46, 168)
CHOICE_X = PORTRAIT.right + 26
CHOICE_W = WINDOW.right - CHOICE_X - 28
CHOICE_Y = WINDOW.y + 234
CHOICE_H = 32
CHOICE_GAP = 8
CLOSE_RECT = pygame.Rect(WINDOW.right - 146, WINDOW.y + 10, 126, 28)
REVEAL_TIME = 0.18


class DialogueScreen:
    def __init__(self, dialogue, npcs, notify=None) -> None:
        self.dialogue = dialogue
        self.npcs = npcs
        self.notify = notify
        self.reveal = 0.0
        self.time = 0.0
        self.cursor = 0
        self.hover: int | None = None

    # ------------------------------------------------------------------
    def open(self) -> None:
        self.reveal = 0.0
        self.time = 0.0
        self.cursor = 0
        self.hover = None

    def update(self, dt: float) -> None:
        dt = max(0.0, dt)
        self.time += dt
        self.reveal = min(1.0, self.reveal + dt / REVEAL_TIME)
        self.dialogue.update(dt)

    def npc(self):
        return self.npcs.get(self.dialogue.npc_id)

    def choice_rects(self) -> list[pygame.Rect]:
        count = len(self.dialogue.choices)
        return [
            pygame.Rect(CHOICE_X, CHOICE_Y + index * (CHOICE_H + CHOICE_GAP),
                        CHOICE_W, CHOICE_H)
            for index in range(count)
        ]

    # ------------------------------------------------------------------
    def _say(self, text: str) -> None:
        if callable(self.notify):
            self.notify(text)

    def _activate(self, index: int | None = None) -> str:
        """Commit the current choice/continue; return an action for Game."""
        dialog = self.dialogue
        if dialog.has_choices:
            picked = dialog.choices if index is None else [dialog.choices[index]]
            if index is None:
                index = self.cursor
            if index < 0 or index >= len(dialog.choices):
                return ""
            action = dialog.choose(index)
            self.cursor = 0
            self.hover = None
            if not dialog.active:
                return action or "close"
            return action
        action = dialog.advance()
        self.cursor = 0
        if not dialog.active:
            return action or "close"
        return action

    def handle_event(self, event: pygame.event.Event) -> str | None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.dialogue.close()
                return "close"
            choices = self.dialogue.choices
            if event.key in (pygame.K_UP, pygame.K_w):
                if choices:
                    self.cursor = (self.cursor - 1) % len(choices)
                return None
            if event.key in (pygame.K_DOWN, pygame.K_s):
                if choices:
                    self.cursor = (self.cursor + 1) % len(choices)
                return None
            if event.key in (pygame.K_SPACE, pygame.K_RETURN,
                             pygame.K_KP_ENTER, pygame.K_g):
                return self._activate()
            return None
        if event.type == pygame.MOUSEMOTION:
            self.hover = None
            for index, rect in enumerate(self.choice_rects()):
                if rect.collidepoint(event.pos):
                    self.hover = index
                    break
            return None
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return None
        pos = event.pos
        if CLOSE_RECT.collidepoint(pos):
            self.dialogue.close()
            return "close"
        for index, rect in enumerate(self.choice_rects()):
            if rect.collidepoint(pos):
                return self._activate(index)
        if not self.dialogue.has_choices:
            return self._activate()
        return None

    # ------------------------------------------------------------------
    def draw(self, target: pygame.Surface) -> None:
        dim = pygame.Surface(target.get_size(), pygame.SRCALPHA)
        dim.fill((5, 4, 9, int(150 * self.reveal)))
        target.blit(dim, (0, 0))

        npc = self.npc()
        accent = npc.accent if npc is not None else (176, 126, 244)
        panel(target, WINDOW, fill=(12, 9, 17, 248), edge=accent,
              inner=(34, 27, 44))

        title = npc.name if npc is not None else "THE KEEPER"
        subtitle = npc.title if npc is not None else ""
        draw_text(target, title, WINDOW.x + 20, WINDOW.y + 12, 2,
                  (232, 214, 250), spacing=1)
        if subtitle:
            draw_text(target, subtitle, WINDOW.x + 20 + text_width(title, 2, 1) + 18,
                      WINDOW.y + 24, 1, accent, spacing=1)
        hint = "G SELECT   ESC CLOSE"
        draw_text(target, hint,
                  WINDOW.right - 14 - text_width(hint, 1, 1),
                  WINDOW.y + 18, 1, (150, 138, 166), spacing=1)

        # Real NPC sprite, idle frame 0, presented as a portrait.
        target.fill((18, 14, 24), PORTRAIT)
        if npc is not None:
            frame = npc.frames.get("down", [None])[0]
            if frame is not None:
                portrait = pygame.transform.scale(frame, PORTRAIT.size)
                target.blit(portrait, PORTRAIT.topleft)
        pygame.draw.rect(target, accent, PORTRAIT, 2)
        glyph_x = PORTRAIT.x + 8
        glyph_y = PORTRAIT.bottom - 24
        draw_text(target, "G  TALK" if npc is None else npc.prompt,
                  glyph_x, glyph_y, 1, (228, 210, 244), shadow=(2, 2, 6))

        panel(target, TEXT_RECT, fill=(8, 6, 13, 218), edge=(68, 56, 84))
        visible = int(len(self.dialogue.text) * self.reveal)
        lines = wrap_text(self.dialogue.text[:visible], TEXT_RECT.w - 24, 1)
        draw_lines(target, lines[:8], TEXT_RECT.x + 12, TEXT_RECT.y + 14, 1,
                   (222, 212, 236), line_gap=7)

        choices = self.dialogue.choices
        if choices:
            for index, (label, rect) in enumerate(zip(choices, self.choice_rects())):
                selected = index == self.cursor
                hovered = index == self.hover
                if selected or hovered:
                    radius = 22 + int(4 * (1.0 + math.sin(self.time * 5.0)))
                    accent_glow(target, rect.center, radius, accent, alpha=34)
                button(target, rect, str(label.get("label", "")),
                       selected or hovered, accent=accent)
                num = f"{index + 1:02d}"
                draw_text(target, num, rect.x + 8, rect.y + 10, 1,
                          accent if selected else (110, 98, 132))
        else:
            prompt = "G / SPACE  CONTINUE"
            draw_text(target, prompt, CHOICE_X + 4, CHOICE_Y + 6, 1,
                      (188, 168, 216), spacing=1)

        page = f"PAGE {self.dialogue.page_index + 1:02d}/{len(self.dialogue.pages):02d}"
        draw_text(target, page, WINDOW.x + 20, WINDOW.bottom - 26, 1,
                  (140, 128, 156), spacing=1)
        flags = len(self.dialogue.flags)
        if flags:
            label = f"NOTES {flags:02d}"
            draw_text(target, label, WINDOW.right - 20 - text_width(label, 1, 1),
                      WINDOW.bottom - 26, 1, accent, spacing=1)
        button(target, CLOSE_RECT, "CLOSE", False)


__all__ = ["DialogueScreen", "WINDOW"]
