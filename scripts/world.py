"""World loading, culling, Y-sorting and rendering."""
from __future__ import annotations

import pygame

from settings import WORLD_H, WORLD_W
from scripts.collision import CollisionWorld
from scripts.village_layout import ALL_PROPS, LIGHTS, SPAWN, Light


class PropInstance:
    __slots__ = ("name", "x", "y", "image", "w", "h", "sort_y")

    def __init__(self, prop, image: pygame.Surface) -> None:
        self.name = prop.name
        self.x = prop.x
        self.y = prop.y
        self.image = image
        self.w = image.get_width()
        self.h = image.get_height()
        self.sort_y = float(prop.y)

    def bounds(self) -> pygame.Rect:
        return pygame.Rect(
            int(self.x - self.w / 2 - 6),
            int(self.y - self.h - 6),
            self.w + 12,
            self.h + 12,
        )

    def draw(self, target: pygame.Surface, offset: tuple[int, int]) -> None:
        ox, oy = offset
        target.blit(self.image, (int(self.x - self.w / 2) - ox,
                                 int(self.y - self.h) - oy))


class World:
    def __init__(self, assets, canvas_size: tuple[int, int]) -> None:
        self.assets = assets
        self.canvas_w, self.canvas_h = canvas_size
        self.ground = assets.ground
        self.lights: list[Light] = list(LIGHTS)

        self.props: list[PropInstance] = []
        self._flipped: dict[str, pygame.Surface] = {}
        for prop in ALL_PROPS:
            base = assets.image(prop.name)
            if prop.scale != 1.0:
                base = pygame.transform.scale(
                    base,
                    (max(1, int(base.get_width() * prop.scale)),
                     max(1, int(base.get_height() * prop.scale))),
                )
            if prop.flip:
                key = f"{prop.name}:{prop.scale}"
                image = self._flipped.get(key)
                if image is None:
                    image = pygame.transform.flip(base, True, False)
                    self._flipped[key] = image
            else:
                image = base
            self.props.append(PropInstance(prop, image))

        self.collision = CollisionWorld(ALL_PROPS, assets.dims)
        self.spawn = SPAWN

    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        pass

    def draw(self, target: pygame.Surface, camera, player) -> None:
        ox, oy = camera.offset
        view = camera.visible_rect(140)

        # Ground is one baked image; blit only the visible source rectangle.
        sx = max(0, ox)
        sy = max(0, oy)
        sw = min(self.canvas_w, WORLD_W - sx)
        sh = min(self.canvas_h, WORLD_H - sy)
        if sw > 0 and sh > 0:
            target.blit(self.ground, (sx - ox, sy - oy),
                        area=pygame.Rect(sx, sy, sw, sh))

        # Cull by each sprite's true bounding box, then sort by ground contact.
        visible: list[tuple[float, PropInstance]] = []
        for prop in self.props:
            if prop.bounds().colliderect(view):
                visible.append((prop.sort_y, prop))
        drawables: list[tuple[float, object]] = [(y, p) for y, p in visible]
        drawables.append((player.sort_y, player))
        drawables.sort(key=lambda item: item[0])

        for _, item in drawables:
            if item is player:
                player.draw(target, (ox, oy))
            else:
                item.draw(target, (ox, oy))

    # ------------------------------------------------------------------
    def debug_draw(self, target: pygame.Surface, camera, player) -> None:
        self.collision.debug_draw(target, camera.offset)
        player.debug_draw(target, camera.offset)
        for light in self.lights:
            sx, sy = camera.to_screen(light.x, light.y)
            pygame.draw.circle(target, (120, 90, 255), (sx, sy), int(light.radius), 1)
