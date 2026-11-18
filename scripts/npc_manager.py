"""Reusable pixel-art NPC entities for the Ashen Village survivors.

NPCs are data-driven idle characters: they never own gameplay logic beyond
animation, facing and their small collision footprint.  Dialogue, trade and
story actions are routed through their own managers by ``InteractionManager``.
"""
from __future__ import annotations

import math

import pygame

from scripts.village_data import npc_definitions

FRAME = 64
DIRECTIONS = ("down", "up", "left", "right")
DIRECTION_INDEX = {name: index for index, name in enumerate(DIRECTIONS)}
IDLE_FPS = 4.0


def _direction_from(dx: float, dy: float) -> str:
    if abs(dx) > abs(dy):
        return "right" if dx > 0 else "left"
    return "down" if dy > 0 else "up"


class NPC:
    """One idle, faceable sprite with a foot-level collision box."""

    def __init__(self, definition: dict, assets) -> None:
        self.id = str(definition.get("id", ""))
        self.name = str(definition.get("name", self.id.upper()))
        self.title = str(definition.get("title", ""))
        self.x = float(definition.get("x", 0.0))
        self.y = float(definition.get("y", 0.0))
        self.facing = str(definition.get("facing", "down")).lower()
        if self.facing not in DIRECTION_INDEX:
            self.facing = "down"
        self.radius = max(24.0, min(160.0, float(definition.get("radius", 72.0))))
        self.sheet_path = str(definition.get("sheet", ""))
        self.service = str(definition.get("service", "story")).lower()
        self.dialogue_id = str(definition.get("dialogue", self.id)).lower()
        accent = definition.get("accent", (180, 132, 240))
        self.accent = (
            int(accent[0]) if isinstance(accent, (list, tuple)) and len(accent) > 2 else 180,
            int(accent[1]) if isinstance(accent, (list, tuple)) and len(accent) > 2 else 132,
            int(accent[2]) if isinstance(accent, (list, tuple)) and len(accent) > 2 else 240,
        )

        sheet = assets.npc_sheet(self.sheet_path)
        self.frames: dict[str, list[pygame.Surface]] = {}
        for direction, row in DIRECTION_INDEX.items():
            self.frames[direction] = [
                sheet.subsurface(pygame.Rect(col * FRAME, row * FRAME,
                                             FRAME, FRAME))
                for col in range(4)
            ]
        self.shadow = assets.soft_shadow(38, 14)
        self.time = 0.0
        self.phase = len(self.id) * 0.7
        self.interacting = False
        self.talked = False
        self.interactions = 0

    # ------------------------------------------------------------------
    @property
    def sort_y(self) -> float:
        return self.y

    @property
    def prompt(self) -> str:
        if self.service == "shop":
            return "G  TRADE"
        if self.service == "blacksmith":
            return "G  FORGE"
        return "G  TALK"

    def solid_rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - 12), int(self.y - 10), 24, 14)

    def face_player(self, player) -> None:
        self.facing = _direction_from(player.x - self.x, player.y - self.y)

    def begin_interaction(self, player) -> None:
        self.face_player(player)
        self.interacting = True
        self.talked = True
        self.interactions += 1

    def end_interaction(self) -> None:
        self.interacting = False

    def update(self, dt: float) -> None:
        self.time += max(0.0, dt)

    def draw(self, target: pygame.Surface, offset: tuple[int, int]) -> None:
        ox, oy = offset
        sx = int(round(self.x)) - ox
        sy = int(round(self.y)) - oy
        target.blit(self.shadow, (sx - self.shadow.get_width() // 2,
                                  sy - self.shadow.get_height() // 2 - 1))
        frames = self.frames[self.facing]
        index = int(self.time * IDLE_FPS + self.phase) % len(frames)
        image = frames[index]
        # A one-pixel breathing movement keeps the camp alive without AI.
        bob = 1 if math.sin(self.time * 2.0 + self.phase) > 0.72 else 0
        target.blit(image, (sx - FRAME // 2, sy - 52 - bob))


class NPCManager:
    def __init__(self, assets, collision=None) -> None:
        self.assets = assets
        self.npcs = [NPC(definition, assets)
                     for definition in npc_definitions()]
        self.by_id = {npc.id: npc for npc in self.npcs}
        self.collision = None
        if collision is not None:
            self.register_collision(collision)

    # ------------------------------------------------------------------
    def register_collision(self, collision) -> None:
        """Add each NPC's foot box to the existing static collision world."""
        if self.collision is collision:
            return
        self.collision = collision
        if collision is None:
            return
        for npc in self.npcs:
            collision.add_rect(npc.solid_rect())

    def update(self, dt: float) -> None:
        for npc in self.npcs:
            npc.update(dt)

    def get(self, npc_id: str) -> NPC | None:
        return self.by_id.get(str(npc_id).lower())

    def face(self, npc: NPC, player) -> None:
        npc.face_player(player)

    def load_state(self, raw) -> None:
        if not isinstance(raw, dict):
            return
        for npc_id, entry in raw.items():
            npc = self.get(str(npc_id))
            if npc is None or not isinstance(entry, dict):
                continue
            npc.talked = bool(entry.get("talked", False))
            try:
                npc.interactions = max(0, min(9999,
                                             int(entry.get("interactions", 0))))
            except (TypeError, ValueError):
                npc.interactions = 0

    def to_state(self) -> dict:
        return {
            npc.id: {
                "talked": bool(npc.talked),
                "interactions": int(npc.interactions),
            }
            for npc in self.npcs
        }


__all__ = ["DIRECTIONS", "FRAME", "NPC", "NPCManager"]
