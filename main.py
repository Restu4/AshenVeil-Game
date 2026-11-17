"""ASHEN VEIL — a first-playable dark fantasy village prototype."""
from __future__ import annotations

import asyncio
import sys

import pygame

from settings import FPS, SCREEN_H, SCREEN_W
from scripts.asset_loader import Assets
from scripts.atmosphere import Atmosphere
from scripts.camera import Camera
from scripts.combat_manager import CombatManager
from scripts.effects import Effects
from scripts.hud import HUD
from scripts.pixel_font import draw_text
from scripts.player import Player
from scripts.village_layout import SPAWN, SPAWN_FACING
from scripts.world import World

IS_WEB = sys.platform == "emscripten"


class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("ASHEN VEIL — ASHEN VILLAGE")
        flags = 0 if IS_WEB else pygame.RESIZABLE
        try:
            self.window = pygame.display.set_mode((SCREEN_W, SCREEN_H), flags)
        except pygame.error:
            self.window = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.canvas = pygame.Surface((SCREEN_W, SCREEN_H)).convert()

        self.assets = Assets()
        self.world = World(self.assets, (SCREEN_W, SCREEN_H))
        self.player = Player(self.assets, SPAWN[0], SPAWN[1], SPAWN_FACING)
        self.camera = Camera(self.player.x, self.player.y)
        self.camera.snap(self.player.x + self.player.look[0],
                         self.player.y + self.player.look[1])
        self.atmosphere = Atmosphere(self.world.lights)
        self.effects = Effects()
        self.combat = CombatManager(self.assets, self.world, self.player,
                                    self.camera, self.effects)
        self.hud = HUD()
        self.clock = pygame.time.Clock()

        self.running = True
        self.debug = False
        self.time = 0.0
        self._scaled: pygame.Surface | None = None
        self._scaled_size = (0, 0)
        if not IS_WEB:
            pygame.mouse.set_visible(False)

    # ------------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.VIDEORESIZE and not IS_WEB:
            try:
                self.window = pygame.display.set_mode(event.size, pygame.RESIZABLE)
            except pygame.error:
                pass
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.player.combat.dead:
                self.restart()
            else:
                self.player.request_attack()
        elif event.type == pygame.KEYDOWN:
            if self.player.combat.dead:
                if event.key == pygame.K_ESCAPE and not IS_WEB:
                    self.running = False
                elif event.key in (pygame.K_r, pygame.K_RETURN,
                                   pygame.K_KP_ENTER, pygame.K_SPACE):
                    self.restart()
                return
            if event.key == pygame.K_ESCAPE and not IS_WEB:
                self.running = False
            elif event.key == pygame.K_SPACE:
                self.player.request_dodge()
            elif event.key in (pygame.K_F1, pygame.K_F3):
                self.debug = not self.debug
            elif event.key == pygame.K_h:
                self.hud.toggle_help()
            elif event.key == pygame.K_F11 and not IS_WEB:
                pygame.display.toggle_fullscreen()

    # ------------------------------------------------------------------
    def restart(self) -> None:
        self.player.reset(SPAWN[0], SPAWN[1], SPAWN_FACING)
        self.combat.restart()
        self.effects.clear()
        self.camera.snap(self.player.x + self.player.look[0],
                         self.player.y + self.player.look[1])

    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        keys = pygame.key.get_pressed()
        self.player.update(dt, keys, self.world.collision)
        self.combat.update(dt)
        look_x, look_y = self.player.look
        self.camera.update(dt, self.player.x, self.player.y, look_x, look_y)
        self.world.update(dt)
        self.atmosphere.update(dt, self.player, self.camera)
        self.effects.update(dt)
        self.hud.update(dt, self.player)
        self.time += dt

    # ------------------------------------------------------------------
    def draw(self) -> None:
        self.world.draw(self.canvas, self.camera, self.player, self.combat.enemies)
        self.atmosphere.draw(self.canvas, self.camera, self.player)
        self.effects.draw_world(self.canvas, self.camera)
        self.effects.draw_overlay(self.canvas, self.camera)
        self.hud.draw(self.canvas, self.player, self.combat.engaged)
        if self.debug:
            self.world.debug_draw(self.canvas, self.camera, self.player)
            self.combat.debug_draw(self.canvas, self.camera)
            draw_text(self.canvas, f"FPS {int(self.clock.get_fps()):02d}",
                      24, 132, 1, (112, 255, 145), spacing=1)
            draw_text(self.canvas,
                      f"X {int(self.player.x)}  Y {int(self.player.y)}  "
                      f"SPD {int(self.player.speed)}",
                      24, 144, 1, (112, 255, 145), spacing=1)
            draw_text(self.canvas,
                      f"STATE {self.player.state}  "
                      f"ENEMIES {len(self.combat.enemies)}",
                      24, 156, 1, (112, 255, 145), spacing=1)
            draw_text(self.canvas, "F1 DEBUG  H HINTS", 24, 168, 1,
                      (112, 255, 145), spacing=1)

    # ------------------------------------------------------------------
    def present(self) -> None:
        window = pygame.display.get_surface()
        if window is None:
            return
        ww, wh = window.get_size()
        if (ww, wh) == (SCREEN_W, SCREEN_H):
            window.blit(self.canvas, (0, 0))
        else:
            scale = min(ww / SCREEN_W, wh / SCREEN_H)
            dw = max(1, int(SCREEN_W * scale))
            dh = max(1, int(SCREEN_H * scale))
            if self._scaled_size != (dw, dh):
                self._scaled = pygame.Surface((dw, dh)).convert()
                self._scaled_size = (dw, dh)
            pygame.transform.scale(self.canvas, (dw, dh), self._scaled)
            window.fill((0, 0, 0))
            window.blit(self._scaled, ((ww - dw) // 2, (wh - dh) // 2))
        pygame.display.flip()

    # ------------------------------------------------------------------
    async def run(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)
            for event in pygame.event.get():
                self.handle_event(event)
            self.update(dt)
            self.draw()
            self.present()
            await asyncio.sleep(0)
        pygame.quit()


async def main() -> None:
    game = Game()
    await game.run()


if __name__ == "__main__":
    asyncio.run(main())
