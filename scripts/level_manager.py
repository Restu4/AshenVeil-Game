"""Level 01 stage script: village -> corrupted path -> shrine -> boss arena.

The level manager owns *flow*, not combat.  It decides which scripted group is
alive, when a stage is cleared, when the veil gate opens, and when the boss
encounter begins.  Damage still flows through ``CombatManager`` and the boss
still owns its phases.

Stage map (Level 01):
  1 ABANDONED VILLAGE   clear the opening trio
  2 CORRUPTED PATH      break the Corrupted Warden and its escort
  3 FORGOTTEN SHRINE    walk into the veil gate
  4 BOSS ARENA          defeat the Hollow Guardian (no retreat)
"""
from __future__ import annotations

import math
from dataclasses import replace

import pygame

from scripts.boss_manager import BossManager
from scripts.enemy_config import get_archetype
from scripts.level_config import get_level
from scripts.pixel_font import draw_text
from scripts.ui.stage_hud import StageHUD
from scripts.village_layout import (
    ARENA_PLAYER_SPAWN,
    SPAWN,
    SPAWN_FACING,
)

STAGE_TOTAL = 4
TRANSITION_TIME = 0.42
PORTAL_RADIUS = 54.0

WARDEN = replace(
    get_archetype("fallen_knight"),
    key="corrupted_warden",
    name="CORRUPTED WARDEN",
    subtitle="ELITE OF THE WESTERN PATH",
    max_health=320.0,
    damage=22.0,
    detection=360.0,
    attack_range=58.0,
    attack_cooldown=1.05,
    windup=0.60,
    active=0.18,
    recovery=0.52,
    chase_speed=116.0,
    half_w=17.0,
    half_h=12.0,
    hurt_time=0.18,
    hit_flash=0.10,
    death_time=0.62,
    swipe_color=(212, 116, 206),
)

# Scripted stage-2 positions, spread along the corrupted west road.
WARDEN_SPAWN = (902.0, 1122.0)
ESCORT_SPAWNS = (
    ("void_stalker", 814.0, 1068.0),
    ("ashen_cultist", 986.0, 1186.0),
)


class LevelManager:
    def __init__(self, assets, world, player, combat, camera, effects,
                 skills, progression) -> None:
        self.assets = assets
        self.world = world
        self.player = player
        self.combat = combat
        self.camera = camera
        self.effects = effects
        self.skills = skills
        self.progression = progression
        self.boss = BossManager(assets, world, player, combat, camera, effects)

        self.level_id = "01"
        self.stage_index = 0
        self.stage_enemy_ids: set[int] = set()
        self.stage_elapsed = 0.0

        self.transition_phase = ""
        self.transition_t = 0.0
        self.victory_ready = False
        self.victory_consumed = False
        self.victory_recorded = False

        self.banner_timer = 0.0
        self.banner_total = 1.0
        self.banner_title = ""
        self.banner_subtitle = ""

        self.stage_hud = StageHUD()
        self.last_save_ok = True

        # Attach to the run the Game already built (the opening trio).
        self.on_restart(show_banner=False)

    # ------------------------------------------------------------------
    # Static/derived data used by the HUD and tests
    # ------------------------------------------------------------------
    @property
    def level(self):
        return get_level(self.level_id)

    @property
    def stage(self):
        stages = self.level.stages
        if not stages:
            return None
        return stages[min(self.stage_index, len(stages) - 1)]

    @property
    def stage_number(self) -> int:
        return self.stage_index + 1

    @property
    def stage_total(self) -> int:
        return STAGE_TOTAL

    @property
    def stage_name(self) -> str:
        stage = self.stage
        return stage.name if stage else "THE VEIL"

    @property
    def objective(self) -> str:
        stage = self.stage
        return stage.objective if stage else ""

    @property
    def objective_detail(self) -> str:
        stage = self.stage_index
        if stage in (0, 1):
            remaining = self._stage_alive()
            return f"FOES REMAIN {remaining:02d}"
        if stage == 2:
            distance = math.hypot(self.player.x - self.stage.x,
                                  self.player.y - self.stage.y)
            return f"VEIL GATE {int(distance):04d} PX"
        if stage == 3:
            return "NO RETREAT  ·  NO MERCY"
        return ""

    @property
    def stages_cleared(self) -> int:
        return self.progression.stages_cleared(self.level_id)

    @property
    def blocking(self) -> bool:
        return bool(self.transition_phase)

    @property
    def in_boss_fight(self) -> bool:
        return self.boss.in_fight

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def on_restart(self, show_banner: bool = True) -> None:
        """Reset flow onto an already-built run (Game.restart / __init__)."""
        self.boss.stop()
        self.level_id = "01"
        self.stage_index = 0
        self.stage_elapsed = 0.0
        self.stage_enemy_ids = {e.id for e in self.combat.enemies if e.alive}
        self.transition_phase = ""
        self.transition_t = 0.0
        self.victory_ready = False
        self.victory_consumed = False
        self.victory_recorded = False
        self.combat.spawner.enabled = False
        self.player.level = self.progression.player_level
        if show_banner:
            self._banner("STAGE 1  ·  ABANDONED VILLAGE",
                         "CUT DOWN THE RISEN DEAD", 3.4)

    def begin_level(self, level_id: str) -> bool:
        """Start a level from the menu, rebuilding the player and stage 1."""
        level = get_level(level_id)
        if not level.playable:
            return False
        if not self.progression.is_playable(level_id):
            return False

        self.level_id = level_id
        self.player.level = self.progression.player_level
        self.player.reset(SPAWN[0], SPAWN[1], SPAWN_FACING)
        self.combat.restart(spawn=False)
        self.skills.reset()
        self.effects.clear()
        self.boss.stop()
        self.combat.spawner.reset(spawn_group=True)
        self.combat.spawner.enabled = False
        self.stage_index = 0
        self.stage_elapsed = 0.0
        self.stage_enemy_ids = {e.id for e in self.combat.enemies if e.alive}
        self.transition_phase = ""
        self.transition_t = 0.0
        self.victory_ready = False
        self.victory_consumed = False
        self.victory_recorded = False
        self.camera.snap(self.player.x + self.player.look[0],
                         self.player.y + self.player.look[1])
        self._banner("STAGE 1  ·  ABANDONED VILLAGE",
                     "CUT DOWN THE RISEN DEAD", 3.4)
        return True

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        self.stage_hud.update(dt)
        if self.banner_timer > 0.0:
            self.banner_timer = max(0.0, self.banner_timer - dt)

        if self.transition_phase:
            self._update_transition(dt)
            self.boss.update(dt)
            return

        self.stage_elapsed += dt
        self.boss.update(dt)

        if self.boss.victory_ready:
            self.victory_ready = True

        if self.stage_index in (0, 1):
            if self._stage_alive() == 0 and self.stage_elapsed > 0.6:
                self._clear_enemy_stage()
        elif self.stage_index == 2:
            stage = self.stage
            if math.hypot(self.player.x - stage.x,
                          self.player.y - stage.y) <= PORTAL_RADIUS:
                self._begin_arena()
        elif self.stage_index == 3:
            if self.boss.victory_ready:
                self.victory_ready = True

    def consume_victory(self) -> bool:
        if self.victory_ready and not self.victory_consumed:
            self.victory_consumed = True
            return True
        return False

    def record_victory(self) -> tuple[bool, bool]:
        """Mark the level complete once.  Returns (new_unlock, save_ok)."""
        if self.victory_recorded:
            return False, True
        self.victory_recorded = True
        new_unlock = self.progression.complete_level(self.level_id)
        self.last_save_ok = self.progression.save_now()
        return new_unlock, self.last_save_ok

    # ------------------------------------------------------------------
    def _stage_alive(self) -> int:
        if not self.stage_enemy_ids:
            return 0
        return sum(1 for enemy in self.combat.enemies
                   if enemy.alive and enemy.id in self.stage_enemy_ids)

    def _clear_enemy_stage(self) -> None:
        cleared = self.stage_index + 1
        self.progression.record_stage(self.level_id, cleared)
        if self.stage_index == 0:
            self._enter_corrupted_path()
        else:
            self._enter_shrine()

    def _enter_corrupted_path(self) -> None:
        self.stage_index = 1
        self.stage_elapsed = 0.0
        self.stage_enemy_ids = set()
        self.combat.spawner.enabled = False
        warden = self.combat.spawner.spawn_at(
            WARDEN.key, WARDEN_SPAWN[0], WARDEN_SPAWN[1],
            facing="right", archetype=WARDEN,
        )
        if warden is not None:
            self.stage_enemy_ids.add(warden.id)
        for key, x, y in ESCORT_SPAWNS:
            enemy = self.combat.spawner.spawn_at(key, x, y)
            if enemy is not None:
                self.stage_enemy_ids.add(enemy.id)
        self.combat.spawner.enabled = False
        self.effects.spawn_flash((26, 12, 34), 0.20)
        self.camera.shake(3.0, 0.18)
        self._banner("STAGE 2  ·  CORRUPTED PATH",
                     "THE WARDEN KNOWS YOUR NAME", 3.4)

    def _enter_shrine(self) -> None:
        self.stage_index = 2
        self.stage_elapsed = 0.0
        self.stage_enemy_ids = set()
        self.combat.spawner.enabled = False
        self.combat.engaged = None
        self.combat.engaged_timer = 0.0
        self.effects.spawn_flash((32, 14, 48), 0.28)
        self.camera.shake(2.0, 0.22)
        self._banner("STAGE 3  ·  FORGOTTEN SHRINE",
                     "STEP INTO THE VEIL GATE", 3.4)

    # ------------------------------------------------------------------
    # Arena entrance
    # ------------------------------------------------------------------
    def _begin_arena(self) -> None:
        if self.transition_phase:
            return
        self.stage_index = 3
        self.stage_elapsed = 0.0
        self.progression.record_stage(self.level_id, 3)
        self.transition_phase = "out"
        self.transition_t = 0.0
        self.effects.spawn_flash((36, 16, 54), 0.34)
        self.camera.shake(5.0, 0.30)

    def _update_transition(self, dt: float) -> None:
        self.transition_t += dt
        if self.transition_phase == "out":
            if self.transition_t >= TRANSITION_TIME:
                self._teleport_to_arena()
        else:
            if self.transition_t >= TRANSITION_TIME:
                self.transition_phase = ""
                self.transition_t = 0.0

    def _teleport_to_arena(self) -> None:
        player = self.player
        player.x, player.y = ARENA_PLAYER_SPAWN
        player.vx = player.vy = 0.0
        player.knockback_x = player.knockback_y = 0.0
        player.facing = "up"
        player.combat.reset()
        self.camera.snap(player.x + player.look[0],
                         player.y + player.look[1])
        self.combat.engaged = None
        self.combat.engaged_timer = 0.0
        self.boss.start(entrance_shake=True)
        self.stage_enemy_ids = set()
        self.transition_phase = "in"
        self.transition_t = 0.0
        self._banner("STAGE 4  ·  BOSS ARENA",
                     "THE HOLLOW GUARDIAN AWAKENS", 3.6)

    @property
    def transition_alpha(self) -> int:
        if not self.transition_phase:
            return 0
        k = min(1.0, self.transition_t / TRANSITION_TIME)
        if self.transition_phase == "out":
            return int(255 * k)
        return int(255 * (1.0 - k))

    # ------------------------------------------------------------------
    # Drawing hooks
    # ------------------------------------------------------------------
    def draw_world_overlay(self, target: pygame.Surface, camera) -> None:
        """Objective marker: a pulsing veil-gate ring at the shrine."""
        if self.stage_index != 2 or self.transition_phase:
            return
        stage = self.stage
        sx, sy = camera.to_screen(stage.x, stage.y - 18)
        if sx < -80 or sx > 1360 or sy < -80 or sy > 800:
            return
        pulse = 0.5 + 0.5 * math.sin(self.stage_hud.time * 3.2)
        radius = int(30 + 8 * pulse)
        ring = pygame.Surface((radius * 2 + 8, radius * 2 + 8),
                              pygame.SRCALPHA)
        pygame.draw.circle(ring, (170, 112, 232, 120),
                           (radius + 4, radius + 4), radius, 2)
        pygame.draw.circle(ring, (216, 176, 255, 70),
                           (radius + 4, radius + 4), max(3, radius - 10), 1)
        target.blit(ring, (sx - radius - 4, sy - radius - 4))
        draw_text(target, "VEIL GATE", sx, sy - radius - 16, 1,
                  (206, 168, 246), spacing=1, center=True)

    def draw_overlay(self, target: pygame.Surface) -> None:
        alpha = self.transition_alpha
        if alpha > 0:
            veil = pygame.Surface(target.get_size(), pygame.SRCALPHA)
            veil.fill((5, 3, 9, min(255, alpha)))
            target.blit(veil, (0, 0))
        self.stage_hud.draw_banner(target, self)

    # ------------------------------------------------------------------
    def _banner(self, title: str, subtitle: str, seconds: float) -> None:
        self.banner_title = title
        self.banner_subtitle = subtitle
        self.banner_timer = seconds
        self.banner_total = max(0.001, seconds)


__all__ = ["LevelManager", "WARDEN", "STAGE_TOTAL"]
