"""Frame animation helpers built on pygame surfaces."""
from __future__ import annotations

import pygame


class Animation:
    """A small looping (or one-shot) frame animation."""

    def __init__(self, frames: list[pygame.Surface], fps: float, loop: bool = True) -> None:
        self.frames = frames
        self.fps = max(1.0, fps)
        self.loop = loop
        self.time = 0.0
        self.index = 0
        self.finished = False

    def reset(self) -> None:
        self.time = 0.0
        self.index = 0
        self.finished = False

    def update(self, dt: float) -> None:
        if not self.frames or self.finished:
            return
        self.time += dt
        duration = len(self.frames) / self.fps
        if self.time >= duration:
            if self.loop:
                self.time %= duration
                self.index = int(self.time * self.fps) % len(self.frames)
            else:
                self.time = duration
                self.index = len(self.frames) - 1
                self.finished = True
        else:
            self.index = int(self.time * self.fps) % len(self.frames)

    @property
    def image(self) -> pygame.Surface:
        return self.frames[self.index]


class CharacterAnimator:
    """Maps action + facing names onto rows of the original 64x64 sheet."""

    def __init__(self, sheet: pygame.Surface, metadata: dict) -> None:
        self.animations: dict[str, Animation] = {}
        fw, fh = metadata["frame_size"]
        columns = metadata["columns"]
        for row_info in metadata["rows"]:
            row = row_info["row"]
            frames = []
            for col in range(row_info["frames"]):
                if col >= columns:
                    break
                frames.append(sheet.subsurface((col * fw, row * fh, fw, fh)))
            self.animations[row_info["name"]] = Animation(
                frames, row_info["fps"], row_info["loop"]
            )
        self.current_name = "idle_down"
        self.current = self.animations[self.current_name]

    def play(self, action: str, direction: str, restart: bool = False) -> None:
        name = f"{action}_{direction}"
        if name not in self.animations:
            name = f"{action}_down"
        if name == self.current_name and not restart:
            return
        self.current_name = name
        self.current = self.animations[name]
        self.current.reset()

    def update(self, dt: float) -> None:
        self.current.update(dt)

    @property
    def image(self) -> pygame.Surface:
        return self.current.image

    @property
    def finished(self) -> bool:
        return self.current.finished
