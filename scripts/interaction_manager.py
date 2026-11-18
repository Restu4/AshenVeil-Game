"""Contextual ``G`` interaction for the village hub.

``E`` is Shadow Step and ``F`` is Eclipse, so the existing contextual pickup
key ``G`` is reused: when a survivor is close enough and unobstructed, ``G``
starts a conversation; otherwise it falls back to the original loot pickup.
Keeping this decision in one small module means the key can never fire a skill
or a duplicate action.
"""
from __future__ import annotations

import math

import pygame

from scripts.pixel_font import draw_text, text_width


class InteractionManager:
    def __init__(self, npcs, collision, loot=None) -> None:
        self.npcs = npcs
        self.collision = collision
        self.loot = loot

    # ------------------------------------------------------------------
    @staticmethod
    def distance(player, npc) -> float:
        return math.hypot(player.x - npc.x, player.y - npc.y)

    def visible(self, player, npc) -> bool:
        """True when no solid lies between the player and the survivor.

        The probe stops just short of the NPC's own foot box; otherwise the
        target's own collision rectangle would always report a false wall.
        """
        dx = player.x - npc.x
        dy = player.y - npc.y
        distance = math.hypot(dx, dy)
        if distance < 1.0:
            return True
        ux, uy = dx / distance, dy / distance
        target_x = npc.x + ux * 18.0
        target_y = npc.y + uy * 18.0
        return not self.collision.segment_blocked(
            player.x, player.y, target_x, target_y, 2.0
        )

    def find(self, player):
        """Return the nearest reachable NPC in range, or ``None``."""
        best = None
        best_distance = float("inf")
        for npc in self.npcs.npcs:
            distance = self.distance(player, npc)
            if distance > npc.radius or distance >= best_distance:
                continue
            if not self.visible(player, npc):
                continue
            best, best_distance = npc, distance
        return best

    # ------------------------------------------------------------------
    def interact(self, player, inventory) -> str:
        """Run one ``G`` press; return ``'talk:<id>'`` or ``'loot'``."""
        npc = self.find(player)
        if npc is not None:
            npc.begin_interaction(player)
            return f"talk:{npc.id}"
        if self.loot is not None and self.loot.try_pickup(player, inventory):
            return "loot"
        return ""

    @staticmethod
    def draw_prompt(target: pygame.Surface, player, npc, camera) -> None:
        """Small name + key badge above the survivor, like the loot prompt."""
        sx, sy = camera.to_screen(npc.x, npc.y)
        label = npc.prompt
        width = text_width(label, 1, 1) + 14
        box_x = int(sx - width / 2)
        box_y = int(sy - 78)
        if box_x < 0 or box_x + width > target.get_width():
            return
        if box_y < 0 or box_y + 16 > target.get_height():
            return
        target.fill((8, 6, 13), (box_x, box_y, width, 15))
        pygame.draw.rect(target, npc.accent,
                         (box_x, box_y, width, 15), 1)
        draw_text(target, label, box_x + 7, box_y + 4, 1, (232, 220, 246))
        name = npc.name
        nw = text_width(name, 1, 1)
        if nw + 14 > target.get_width():
            return
        draw_text(target, name, int(sx - nw / 2), box_y - 14, 1,
                  npc.accent, shadow=(4, 3, 8))


__all__ = ["InteractionManager"]
