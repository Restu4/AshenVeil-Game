"""Compact character status readout shown inside the inventory."""
from __future__ import annotations

import pygame

from scripts.pixel_font import draw_text
from scripts.player_stats import PlayerStats, format_stat
from scripts.ui.ui_common import panel

ROWS = (
    ("level", "CHARACTER LEVEL"),
    ("hp", "HEALTH"),
    ("attack", "ATTACK DAMAGE"),
    ("defense", "DEFENSE"),
    ("speed", "MOVEMENT SPEED"),
    ("crit_chance", "CRITICAL CHANCE"),
    ("crit_damage", "CRITICAL DAMAGE"),
    ("max_void", "MAXIMUM VOID"),
)


class CharacterStatus:
    """Draws the eight required stats from the live PlayerStats snapshot."""

    def draw(self, target: pygame.Surface, rect: pygame.Rect, player,
             stats: PlayerStats, skills=None) -> None:
        panel(target, rect, fill=(10, 8, 15, 224), edge=(72, 60, 88))
        draw_text(target, "CHARACTER", rect.x + 12, rect.y + 9, 1,
                  (204, 186, 228), spacing=1)
        pygame.draw.line(target, (78, 62, 98),
                         (rect.x + 10, rect.y + 22),
                         (rect.right - 10, rect.y + 22), 1)

        values = {
            "level": str(int(player.level)),
            "hp": f"{int(round(player.health))}/{int(round(stats.max_hp))}",
            "attack": format_stat("attack", stats.attack),
            "defense": format_stat("defense", stats.defense),
            "speed": format_stat("speed", stats.speed),
            "crit_chance": format_stat("crit_chance", stats.crit_chance),
            "crit_damage": format_stat("crit_damage", stats.crit_damage),
            "max_void": format_stat("max_void", stats.max_void),
        }
        for index, (key, label) in enumerate(ROWS):
            y = rect.y + 29 + index * 14
            draw_text(target, label, rect.x + 12, y, 1, (140, 130, 150),
                      spacing=1)
            color = (224, 212, 238)
            if key == "hp" and player.health < stats.max_hp * 0.3:
                color = (228, 96, 104)
            if key == "max_void" and skills is not None:
                energy = getattr(skills, "energy", None)
                if energy is not None:
                    values[key] = (f"{int(round(energy.current))}"
                                   f"/{int(round(energy.maximum))}")
            width = len(values[key]) * 6
            draw_text(target, values[key], rect.right - 12 - width, y, 1,
                      color, spacing=1)


__all__ = ["ROWS", "CharacterStatus"]
