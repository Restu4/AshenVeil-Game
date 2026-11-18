"""Asset loading and caching for ASHEN VEIL."""
from __future__ import annotations

import json

import pygame

from settings import ASSETS, ENEMY_SCALE


class Assets:
    """Loads sliced environment art and the original character sheet once."""

    def __init__(self) -> None:
        self.root = ASSETS
        self.manifest: dict[str, dict] = json.loads(
            (self.root / "sliced" / "manifest.json").read_text(encoding="utf-8")
        )
        self._images: dict[str, pygame.Surface] = {}
        self._npc_sheets: dict[str, pygame.Surface] = {}
        self._character: pygame.Surface | None = None
        self._ground: pygame.Surface | None = None
        self._enemy_art: dict[str, tuple[pygame.Surface, dict]] = {}
        self._shadow_cache: dict[tuple[int, int], pygame.Surface] = {}

    # ------------------------------------------------------------------
    def image(self, name: str) -> pygame.Surface:
        surf = self._images.get(name)
        if surf is None:
            info = self.manifest[name]
            path = self.root / info["file"].removeprefix("assets/")
            surf = pygame.image.load(str(path)).convert_alpha()
            self._images[name] = surf
        return surf

    def dims(self, name: str) -> tuple[int, int]:
        rect = self.manifest[name]["rect"]
        return rect[2], rect[3]

    def npc_sheet(self, path: str) -> pygame.Surface:
        """Load a 4x4 Phase 8 NPC idle sheet, cached like every other asset."""
        key = str(path)
        sheet = self._npc_sheets.get(key)
        if sheet is None:
            relative = key.removeprefix("assets/")
            sheet = pygame.image.load(
                str(self.root / relative)
            ).convert_alpha()
            self._npc_sheets[key] = sheet
        return sheet

    # ------------------------------------------------------------------
    @property
    def character_sheet(self) -> pygame.Surface:
        if self._character is None:
            self._character = pygame.image.load(
                str(self.root / "characters" / "ashen_veil_player_spritesheet.png")
            ).convert_alpha()
        return self._character

    @property
    def ground(self) -> pygame.Surface:
        if self._ground is None:
            self._ground = pygame.image.load(
                str(self.root / "generated" / "ground.png")
            ).convert()
        return self._ground

    # ------------------------------------------------------------------
    def enemy_art(self, name: str) -> tuple[pygame.Surface, dict]:
        """Load an enemy sheet once, scaled for the shared render size.

        Every knight re-uses the same surfaces; only the animator's frame
        indices are per-enemy, which keeps memory flat in the browser.
        """
        cached = self._enemy_art.get(name)
        if cached is not None:
            return cached
        directory = self.root / "enemies"
        sheet = pygame.image.load(str(directory / f"{name}.png")).convert_alpha()
        metadata = json.loads(
            (directory / f"{name}.json").read_text(encoding="utf-8")
        )
        if ENEMY_SCALE != 1.0:
            fw, fh = metadata["frame_size"]
            sheet = pygame.transform.scale(
                sheet,
                (int(sheet.get_width() * ENEMY_SCALE),
                 int(sheet.get_height() * ENEMY_SCALE)),
            )
            metadata = {
                **metadata,
                "frame_size": [int(fw * ENEMY_SCALE), int(fh * ENEMY_SCALE)],
            }
        cached = (sheet, metadata)
        self._enemy_art[name] = cached
        return cached

    # ------------------------------------------------------------------
    def soft_shadow(self, width: int, height: int) -> pygame.Surface:
        """Small cached soft ellipse used under the player and motes."""
        key = (max(2, width), max(2, height))
        surf = self._shadow_cache.get(key)
        if surf is None:
            surf = pygame.Surface(key, pygame.SRCALPHA)
            steps = 7
            for i in range(steps, 0, -1):
                rx = int(key[0] * i / steps / 2)
                ry = int(key[1] * i / steps / 2)
                alpha = int(34 * (1.0 - i / (steps + 1)))
                if rx > 0 and ry > 0:
                    pygame.draw.ellipse(
                        surf,
                        (6, 5, 9, max(4, alpha)),
                        (key[0] // 2 - rx, key[1] // 2 - ry, rx * 2, ry * 2),
                    )
            self._shadow_cache[key] = surf
        return surf
