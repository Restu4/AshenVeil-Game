"""Character status overlay: portrait, level, EXP, attributes and derived stats.

Gameplay is frozen by ``Game`` while this screen is open.  Point allocation is
mouse driven; every change goes through ExpManager so negative points, invalid
attributes and duplicate spending are impossible.
"""
from __future__ import annotations

import pygame

from scripts.pixel_font import draw_text, text_width
from scripts.progression_config import (
    ATTRIBUTE_EFFECTS,
    ATTRIBUTE_KEYS,
    ATTRIBUTE_LABELS,
    MAX_ATTRIBUTE_RANK,
)
from scripts.ui.ui_common import button, panel

WINDOW = pygame.Rect(64, 36, 1152, 648)
LEFT = pygame.Rect(80, 84, 360, 376)
RIGHT = pygame.Rect(452, 84, 748, 376)
DETAILS = pygame.Rect(80, 476, 1120, 140)
FOOTER = pygame.Rect(80, 628, 1120, 52)
CLOSE_RECT = pygame.Rect(FOOTER.right - 138, FOOTER.y + 11, 126, 30)
RESET_RECT = pygame.Rect(RIGHT.right - 158, RIGHT.bottom - 48, 146, 30)
PORTRAIT = pygame.Rect(LEFT.x + 80, LEFT.y + 48, 200, 200)
ROW_Y = RIGHT.y + 62
ROW_GAP = 56
PLUS_RECTS = tuple(
    pygame.Rect(RIGHT.right - 58, ROW_Y + i * ROW_GAP + 4, 34, 28)
    for i in range(len(ATTRIBUTE_KEYS))
)
REVEAL_TIME = 0.16


class CharacterScreen:
    def __init__(self, player, exp, stats, equipment, notify=None) -> None:
        self.player = player
        self.exp = exp
        self.stats = stats
        self.equipment = equipment
        self.notify = notify
        self.reveal = 0.0
        self.hover: int | None = None
        self.confirm_reset = False

    # ------------------------------------------------------------------
    def open(self) -> None:
        self.reveal = 0.0
        self.confirm_reset = False

    def update(self, dt: float) -> None:
        self.reveal = min(1.0, self.reveal + max(0.0, dt) / REVEAL_TIME)

    def _say(self, text: str) -> None:
        if callable(self.notify):
            self.notify(text)

    # ------------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event) -> str | None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_p):
                return "close"
            return None
        if event.type == pygame.MOUSEMOTION:
            self.hover = None
            for index, rect in enumerate(PLUS_RECTS):
                if rect.collidepoint(event.pos):
                    self.hover = index
                    break
            return None
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return None
        pos = event.pos
        if CLOSE_RECT.collidepoint(pos):
            return "close"
        if RESET_RECT.collidepoint(pos):
            if not self.confirm_reset:
                self.confirm_reset = True
            elif self.exp.reset_attributes():
                self._say("ATTRIBUTE POINTS REFUNDED")
                self.confirm_reset = False
            else:
                self.confirm_reset = False
            return None
        self.confirm_reset = False
        for index, rect in enumerate(PLUS_RECTS):
            if not rect.collidepoint(pos):
                continue
            key = ATTRIBUTE_KEYS[index]
            if self.exp.allocate_attribute(key):
                self._say(f"{ATTRIBUTE_LABELS[key]} INCREASED")
            else:
                self._say("NO ATTRIBUTE POINTS")
            return None
        return None

    # ------------------------------------------------------------------
    def draw(self, target: pygame.Surface) -> None:
        dim = pygame.Surface(target.get_size(), pygame.SRCALPHA)
        dim.fill((5, 4, 9, int(190 * self.reveal)))
        target.blit(dim, (0, 0))

        panel(target, WINDOW, fill=(12, 9, 17, 246), edge=(88, 68, 108),
              inner=(34, 27, 44))
        draw_text(target, "THE WANDERER", WINDOW.x + 18, WINDOW.y + 10, 2,
                  (226, 208, 244), spacing=1)
        hint = "P CLOSE   ESC BACK"
        draw_text(target, hint,
                  WINDOW.right - 18 - text_width(hint, 1, 1),
                  WINDOW.y + 15, 1, (150, 138, 166), spacing=1)

        self._draw_identity(target)
        self._draw_attributes(target)
        self._draw_details(target)

        panel(target, FOOTER, fill=(10, 8, 15, 238), edge=(70, 58, 86))
        draw_text(target, f"ATTRIBUTE POINTS {self.exp.attribute_points:02d}",
                  FOOTER.x + 18, FOOTER.y + 18, 1, (232, 190, 96), spacing=1)
        draw_text(target, f"SKILL POINTS {self.exp.skill_points:02d}",
                  FOOTER.x + 300, FOOTER.y + 18, 1, (196, 158, 238), spacing=1)
        draw_text(target, "P STATUS   T SKILL TREE", FOOTER.x + 540,
                  FOOTER.y + 18, 1, (150, 140, 166), spacing=1)
        button(target, CLOSE_RECT, "CLOSE (P)", True)

    # ------------------------------------------------------------------
    def _draw_identity(self, target: pygame.Surface) -> None:
        panel(target, LEFT, fill=(10, 8, 15, 224), edge=(72, 60, 88))
        draw_text(target, "CHARACTER", LEFT.x + 12, LEFT.y + 9, 1,
                  (204, 186, 228), spacing=1)
        pygame.draw.line(target, (78, 62, 98),
                         (LEFT.x + 10, LEFT.y + 22),
                         (LEFT.right - 10, LEFT.y + 22), 1)

        # The real player sprite, taken from the live animator (no new art).
        frame = None
        animator = getattr(self.player, "animator", None)
        animation = getattr(animator, "animations", {}).get("idle_down")
        if animation is not None and animation.frames:
            frame = animation.frames[0]
        target.fill((18, 14, 24), PORTRAIT)
        if frame is not None:
            portrait = pygame.transform.scale(frame, PORTRAIT.size)
            target.blit(portrait, PORTRAIT.topleft)
        pygame.draw.rect(target, (126, 100, 158), PORTRAIT, 2)

        y = LEFT.y + 258
        draw_text(target, f"LEVEL {self.exp.level:02d}", LEFT.x + 14, y, 2,
                  (236, 216, 252), spacing=1)
        if self.exp.is_max:
            exp_text = "EXP MAX"
        else:
            exp_text = f"EXP {self.exp.exp}/{self.exp.exp_required}"
        draw_text(target, exp_text, LEFT.x + 14, y + 26, 1,
                  (178, 158, 206), spacing=1)
        bar = pygame.Rect(LEFT.x + 14, y + 42, LEFT.w - 28, 8)
        pygame.draw.rect(target, (6, 5, 10), bar)
        pygame.draw.rect(target, (132, 98, 190),
                         (bar.x, bar.y, int(bar.w * self.exp.exp_ratio), bar.h))
        pygame.draw.rect(target, (104, 84, 130), bar, 1)
        total = f"TOTAL EXP {self.exp.total_exp}"
        draw_text(target, total, LEFT.right - 14 - text_width(total, 1, 1),
                  LEFT.bottom - 24, 1, (140, 128, 156), spacing=1)

    # ------------------------------------------------------------------
    def _draw_attributes(self, target: pygame.Surface) -> None:
        panel(target, RIGHT, fill=(10, 8, 15, 224), edge=(72, 60, 88))
        draw_text(target, "ATTRIBUTES", RIGHT.x + 12, RIGHT.y + 9, 1,
                  (204, 186, 228), spacing=1)
        draw_text(target, f"FREE {self.exp.attribute_points:02d}",
                  RIGHT.right - 14 - text_width(
                      f"FREE {self.exp.attribute_points:02d}", 1, 1),
                  RIGHT.y + 9, 1, (232, 190, 96), spacing=1)
        pygame.draw.line(target, (78, 62, 98),
                         (RIGHT.x + 10, RIGHT.y + 22),
                         (RIGHT.right - 10, RIGHT.y + 22), 1)

        for index, key in enumerate(ATTRIBUTE_KEYS):
            y = ROW_Y + index * ROW_GAP
            value = self.exp.attributes[key]
            color = (232, 216, 248)
            if value >= MAX_ATTRIBUTE_RANK:
                color = (236, 188, 112)
            draw_text(target, ATTRIBUTE_LABELS[key], RIGHT.x + 14, y, 1,
                      color, spacing=1)
            rank = f"{value:02d}/{MAX_ATTRIBUTE_RANK:02d}"
            draw_text(target, rank,
                      RIGHT.x + 210 - text_width(rank, 1, 1), y, 1,
                      color, spacing=1)
            draw_text(target, ATTRIBUTE_EFFECTS[key], RIGHT.x + 14, y + 16, 1,
                      (136, 124, 152), spacing=1)
            enabled = (self.exp.attribute_points > 0
                       and value < MAX_ATTRIBUTE_RANK)
            rect = PLUS_RECTS[index]
            button(target, rect, "+", self.hover == index and enabled,
                   enabled=enabled)

        reset_label = "CONFIRM RESET" if self.confirm_reset else "RESET POINTS"
        button(target, RESET_RECT, reset_label, self.confirm_reset,
               accent=(214, 118, 118))

    # ------------------------------------------------------------------
    def _draw_details(self, target: pygame.Surface) -> None:
        panel(target, DETAILS, fill=(10, 8, 15, 230), edge=(70, 58, 86))
        draw_text(target, "DERIVED COMBAT STATISTICS", DETAILS.x + 14,
                  DETAILS.y + 10, 1, (204, 186, 228), spacing=1)
        pygame.draw.line(target, (72, 58, 88),
                         (DETAILS.x + 12, DETAILS.y + 24),
                         (DETAILS.right - 12, DETAILS.y + 24), 1)

        stats = self.stats
        left_stats = (
            ("ATTACK", str(int(round(stats.attack)))),
            ("MAX HP", str(int(round(stats.max_hp)))),
            ("SPEED", str(int(round(stats.speed)))),
            ("CRIT CHANCE", f"{int(round(stats.crit_chance * 100))} PCT"),
        )
        right_stats = (
            ("CRIT DAMAGE", f"{stats.crit_damage:.2f}X"),
            ("MAX VOID", str(int(round(stats.max_void)))),
            ("VOID POWER", f"{int(round(stats.void_power * 100))} PCT"),
            ("DEFENSE", str(int(round(stats.defense)))),
        )
        for column, entries in enumerate((left_stats, right_stats)):
            x = DETAILS.x + 18 + column * 540
            for index, (label, value) in enumerate(entries):
                y = DETAILS.y + 34 + index * 23
                draw_text(target, label, x, y, 1, (140, 128, 156), spacing=1)
                draw_text(target, value, x + 260 - text_width(value, 1, 1),
                          y, 1, (224, 210, 240), spacing=1)

        weapon = self.equipment.equipped_item("weapon")
        armor = self.equipment.equipped_item("armor")
        weapon_name = weapon.name if weapon is not None else "BARE HANDS"
        armor_name = armor.name if armor is not None else "NO ARMOR"
        gear = f"WEAPON {weapon_name}    ARMOR {armor_name}"
        draw_text(target, gear[:92], DETAILS.x + 18, DETAILS.bottom - 18, 1,
                  (196, 164, 224), spacing=1)


__all__ = ["CharacterScreen", "CLOSE_RECT", "PLUS_RECTS", "RESET_RECT"]
