"""ASHEN VEIL — a dark fantasy hack & slash in the Ashen Village."""
from __future__ import annotations

import asyncio
import sys

import pygame

from settings import FPS, SCREEN_H, SCREEN_W
from scripts.asset_loader import Assets
from scripts.atmosphere import Atmosphere
from scripts.camera import Camera
from scripts.combat_config import DASH_KEY_NAME
from scripts.combat_manager import CombatManager
from scripts.effects import Effects
from scripts.hud import HUD
from scripts.level_config import get_level, next_level_id
from scripts.level_manager import LevelManager
from scripts.pixel_font import draw_text
from scripts.player import Player
from scripts.progression_manager import ProgressionManager
from scripts.skill_manager import SkillManager
from scripts.ui.level_select import LevelSelect
from scripts.ui.main_menu import MainMenu
from scripts.ui.victory_screen import VictoryScreen
from scripts.village_layout import (
    ARENA_CAMERA_LIFT,
    SPAWN,
    SPAWN_FACING,
)
from scripts.world import World

IS_WEB = sys.platform == "emscripten"

MENU = "MENU"
SELECT = "SELECT"
PLAY = "PLAY"
VICTORY = "VICTORY"


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
        self.skills = SkillManager(self.player, self.combat, self.camera)
        self.hud = HUD()
        self.clock = pygame.time.Clock()

        # Progression + level flow.  The Game starts attached to the live
        # Level 01 run (tests and tools construct Game and play immediately);
        # only main() opens the title screen.
        self.progression = ProgressionManager()
        self.level = LevelManager(
            self.assets, self.world, self.player, self.combat, self.camera,
            self.effects, self.skills, self.progression,
        )
        self.menu = MainMenu(self.progression)
        self.level_select = LevelSelect(self.assets, self.progression)
        self.victory = VictoryScreen(self.progression)
        self.state = PLAY
        self.completed_level_id = "01"

        self.running = True
        self.debug = False
        self.time = 0.0
        # Skill keys are fixed to Q/E/R/F.  The dash key is configurable, but it
        # must never alias a skill key or one keypress would mean two things.
        self.skill_keys = {
            "Q": pygame.K_q,
            "E": pygame.K_e,
            "R": pygame.K_r,
            "F": pygame.K_f,
        }
        self.dash_key = getattr(pygame, f"K_{DASH_KEY_NAME.lower()}", pygame.K_c)
        if self.dash_key in self.skill_keys.values():
            self.dash_key = pygame.K_c
        self._scaled: pygame.Surface | None = None
        self._scaled_size = (0, 0)
        if not IS_WEB:
            pygame.mouse.set_visible(False)

    # ------------------------------------------------------------------
    # Screen flow
    # ------------------------------------------------------------------
    def open_menu(self) -> None:
        self.state = MENU
        self.menu.reset()
        self.combat.spawner.enabled = False
        self._show_mouse()

    def open_level_select(self, level_id: str | None = None) -> None:
        self.state = SELECT
        if level_id is not None:
            self.level_select.focus(level_id)
        self._show_mouse()

    def start_level(self, level_id: str) -> bool:
        if not self.level.begin_level(level_id):
            return False
        self.state = PLAY
        self._hide_mouse()
        return True

    def _open_victory(self) -> None:
        self.completed_level_id = self.level.level_id
        new_unlock, save_ok = self.level.record_victory()
        following = next_level_id(self.completed_level_id)
        next_level = get_level(following) if following else None
        self.victory.open(self.level.level, next_level, save_ok=save_ok)
        self.state = VICTORY
        self.level.boss.defeated = True
        self._show_mouse()

    def _show_mouse(self) -> None:
        if not IS_WEB:
            pygame.mouse.set_visible(True)

    @staticmethod
    def _hide_mouse() -> None:
        if not IS_WEB:
            pygame.mouse.set_visible(False)

    # ------------------------------------------------------------------
    def _ui_event(self, event: pygame.event.Event) -> pygame.event.Event:
        """Map window mouse coordinates onto the fixed 1280x720 canvas."""
        if event.type not in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN,
                              pygame.MOUSEBUTTONUP):
            return event
        window = pygame.display.get_surface()
        if window is None:
            return event
        ww, wh = window.get_size()
        if (ww, wh) == (SCREEN_W, SCREEN_H):
            return event
        scale = min(ww / SCREEN_W, wh / SCREEN_H)
        dw = max(1, int(SCREEN_W * scale))
        dh = max(1, int(SCREEN_H * scale))
        ox = (ww - dw) // 2
        oy = (wh - dh) // 2
        pos = getattr(event, "pos", (0, 0))
        mapped = (int((pos[0] - ox) / max(1e-5, scale)),
                  int((pos[1] - oy) / max(1e-5, scale)))
        attrs = dict(event.dict)
        attrs["pos"] = mapped
        return pygame.event.Event(event.type, attrs)

    # ------------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
            return
        if event.type == pygame.VIDEORESIZE and not IS_WEB:
            try:
                self.window = pygame.display.set_mode(event.size,
                                                      pygame.RESIZABLE)
            except pygame.error:
                pass
            return

        if self.state == MENU:
            action = self.menu.handle_event(self._ui_event(event))
            if action == "begin":
                self.start_level("01")
            elif action == "select":
                self.open_level_select(self.progression.next_unplayed_level())
            elif action == "quit":
                self.running = False
            return

        if self.state == SELECT:
            action = self.level_select.handle_event(self._ui_event(event))
            if action == "back":
                self.open_menu()
            elif isinstance(action, tuple) and action[0] == "play":
                self.start_level(action[1])
            return

        if self.state == VICTORY:
            action = self.victory.handle_event(self._ui_event(event))
            if action == "continue":
                self.open_level_select(
                    self.progression.selection_after_victory(
                        self.completed_level_id))
            elif action == "select":
                self.open_level_select(self.completed_level_id)
            return

        # ---- PLAY ----------------------------------------------------
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.player.combat.dead:
                self.restart()
            else:
                self.player.request_attack()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            if not self.player.combat.dead:
                self.player.request_dash()
        elif event.type == pygame.KEYDOWN:
            if self.player.combat.dead:
                if event.key == pygame.K_ESCAPE and not IS_WEB:
                    self.running = False
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER,
                                   pygame.K_SPACE):
                    self.restart()
                return
            if event.key == pygame.K_ESCAPE and not IS_WEB:
                self.running = False
            elif event.key == pygame.K_SPACE:
                self.player.request_dodge()
            elif event.key in self.skill_keys.values():
                # Exactly one skill per keypress; the mapping is explicit so Q
                # can never fire a second ability through another branch.
                for skill_key, code in self.skill_keys.items():
                    if event.key == code:
                        self.skills.try_cast(skill_key)
                        break
            elif event.key == self.dash_key:
                self.player.request_dash()
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
        self.skills.reset()
        self.effects.clear()
        self.camera.snap(self.player.x + self.player.look[0],
                         self.player.y + self.player.look[1])
        self.level.on_restart()
        self.state = PLAY
        self._hide_mouse()

    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        if self.state in (MENU, SELECT, VICTORY):
            screen = (self.menu if self.state == MENU else
                      self.level_select if self.state == SELECT else
                      self.victory)
            screen.update(dt)
            self.world.update(dt)
            self.atmosphere.update(dt, self.player, self.camera)
            self.effects.update(dt)
            self.time += dt
            return

        # ---- PLAY ----------------------------------------------------
        sim_dt = self.combat.consume_hit_stop(dt)
        if not self.level.blocking:
            keys = pygame.key.get_pressed()
            self.player.update(sim_dt, keys, self.world.collision)
            self.combat.update(sim_dt)
            self.skills.update(sim_dt)
            self.level.update(dt)
            if self.level.consume_victory():
                self._open_victory()
                return
        else:
            self.level.update(dt)

        look_x, look_y = self.player.look
        focus_y = self.player.y
        if self.level.boss.active:
            focus_y -= ARENA_CAMERA_LIFT
        self.camera.update(sim_dt, self.player.x, focus_y, look_x, look_y)
        self.world.update(sim_dt)
        self.atmosphere.update(sim_dt, self.player, self.camera)
        self.effects.update(sim_dt)
        self.hud.update(dt, self.player)
        self.time += dt

    # ------------------------------------------------------------------
    def draw(self) -> None:
        if self.state == MENU:
            self._draw_world()
            self.menu.draw(self.canvas, self.assets)
            return
        if self.state == SELECT:
            self._draw_world()
            self.level_select.draw(self.canvas)
            return
        if self.state == VICTORY:
            self._draw_world()
            self.effects.draw_world(self.canvas, self.camera)
            self.combat.draw_projectiles(self.canvas, self.camera)
            self.victory.draw(self.canvas)
            return

        # ---- PLAY ----------------------------------------------------
        self._draw_world()
        self.level.draw_world_overlay(self.canvas, self.camera)
        self.skills.draw_world(self.canvas, self.camera)
        self.effects.draw_world(self.canvas, self.camera)
        self.combat.draw_projectiles(self.canvas, self.camera)
        self.skills.draw_overlay(self.canvas)
        self.effects.draw_overlay(self.canvas, self.camera)
        self.hud.draw(self.canvas, self.player, self.combat, self.camera,
                      self.skills, stage=self.level, boss=self.level.boss)
        self.level.draw_overlay(self.canvas)
        if self.debug:
            self.world.debug_draw(self.canvas, self.camera, self.player)
            self.combat.debug_draw(self.canvas, self.camera)
            self.level.boss.debug_draw(self.canvas, self.camera)
            draw_text(self.canvas, f"FPS {int(self.clock.get_fps()):02d}",
                      24, 132, 1, (112, 255, 145), spacing=1)
            draw_text(self.canvas,
                      f"X {int(self.player.x)}  Y {int(self.player.y)}  "
                      f"SPD {int(self.player.speed)}",
                      24, 144, 1, (112, 255, 145), spacing=1)
            draw_text(self.canvas,
                      f"STATE {self.player.state}  "
                      f"STAGE {self.player.combat.attack_stage}  "
                      f"ENEMIES {self.combat.alive_count}  "
                      f"SPAWNED {self.combat.spawner.total_spawned}"
                      f"/{self.combat.spawner.max_total}",
                      24, 156, 1, (112, 255, 145), spacing=1)
            draw_text(self.canvas,
                      f"COMBO {self.player.combat.combo_count}  "
                      f"DASH {int(self.player.dash_ready_ratio * 100)} PCT  "
                      f"HITSTOP {self.combat.hit_stop * 1000:.0f}ms",
                      24, 168, 1, (112, 255, 145), spacing=1)
            draw_text(self.canvas,
                      f"VE {int(self.skills.energy.current):03d}  "
                      f"Q {self.skills.burst.timer:.1f}  "
                      f"E {self.skills.shadow.timer:.1f}  "
                      f"R {self.skills.slash.timer:.1f}  "
                      f"F {self.skills.eclipse.timer:.1f}",
                      24, 180, 1, (188, 148, 255), spacing=1)
            draw_text(self.canvas,
                      f"PROJ {len(self.combat.projectiles.projectiles)}  "
                      f"TYPES {','.join(sorted({e.key for e in self.combat.enemies}))}",
                      24, 192, 1, (188, 148, 255), spacing=1)
            draw_text(self.canvas, "F1 DEBUG  H HINTS", 24, 204, 1,
                      (112, 255, 145), spacing=1)

    def _draw_world(self) -> None:
        self.world.draw(self.canvas, self.camera, self.player,
                        self.combat.enemies)
        self.atmosphere.draw(self.canvas, self.camera, self.player)

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
    game.open_menu()
    await game.run()


if __name__ == "__main__":
    asyncio.run(main())
