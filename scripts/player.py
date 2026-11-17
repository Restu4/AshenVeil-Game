"""Player character: movement, animation, vitality and combat integration."""
from __future__ import annotations

import json
import math

import pygame

from scripts.combat_config import (
    ATTACK_DAMAGE,
    ATTACK_HEAVY,
    ATTACK_KNOCKBACK,
    ATTACK_REACH,
    ATTACK_SPIN,
    ATTACK_WIDTH,
    DASH_DAMAGE,
    DASH_DURATION,
    DASH_KNOCKBACK,
    DASH_REACH,
    DASH_SPEED,
    DASH_WIDTH,
    DODGE_DURATION,
    DODGE_SPEED,
    PLAYER_HEALTH_MAX,
    PLAYER_HURT_DECAY,
)
from scripts.health import Health
from scripts.hitbox import AttackHitbox
from scripts.player_combat import (
    ATTACK_STATES,
    DASH_ATTACK,
    HURT,
    IDLE,
    RUN,
    WALK,
    PlayerCombat,
)
from scripts.animation import CharacterAnimator
from scripts.collision import CollisionWorld
from settings import (
    PLAYER_ACCEL,
    PLAYER_FRICTION,
    PLAYER_RUN_SPEED,
    PLAYER_SCALE,
    PLAYER_WALK_SPEED,
)

FRAME_W = 64
FOOT_LINE = 52          # y of the character's feet inside the 64x64 frame
HALF_W = 12.0
HALF_H = 9.0

FACING_VECTORS = {
    "down": (0.0, 1.0),
    "up": (0.0, -1.0),
    "left": (-1.0, 0.0),
    "right": (1.0, 0.0),
}


class Player:
    def __init__(self, assets, x: float, y: float, facing: str = "up") -> None:
        self.assets = assets
        metadata = json.loads(
            (assets.root / "characters" / "ashen_veil_player_spritesheet.json")
            .read_text(encoding="utf-8")
        )
        self.animator = CharacterAnimator(assets.character_sheet, metadata)
        self.scale = PLAYER_SCALE
        self.frame_w = int(round(FRAME_W * self.scale))
        self.foot_line = int(round(FOOT_LINE * self.scale))
        if self.scale != 1.0:
            for animation in self.animator.animations.values():
                animation.frames = [
                    pygame.transform.scale(
                        frame, (self.frame_w, self.frame_w)
                    )
                    for frame in animation.frames
                ]
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.knockback_x = 0.0
        self.knockback_y = 0.0
        self.facing = facing
        self.moving = False
        self.running = False
        self.speed = 0.0
        self.input_x = 0.0
        self.input_y = 0.0

        self.level = 7
        self.vitality = Health(PLAYER_HEALTH_MAX)
        self.combat = PlayerCombat(self)
        self.footstep_timer = 0.0
        self.footstep_pulse = False
        self.step_side = 0
        self._anim_attack_id = -1
        self._was_dodging = False
        self._was_dashing = False

    # ------------------------------------------------------------------
    # Compatibility accessors used by the HUD and atmosphere.
    # ------------------------------------------------------------------
    @property
    def health(self) -> float:
        return self.vitality.current

    @health.setter
    def health(self, value: float) -> None:
        self.vitality.current = float(value)
        self.vitality.clamp()

    @property
    def health_max(self) -> float:
        return self.vitality.maximum

    @property
    def dash_ready_ratio(self) -> float:
        return self.combat.dash_ready_ratio

    # ------------------------------------------------------------------
    # Combat intent (called from event handling so clicks are never lost).
    # ------------------------------------------------------------------
    def request_attack(self) -> None:
        self.combat.request_attack()

    def request_dodge(self) -> None:
        self.combat.request_dodge()

    def request_dash(self) -> None:
        self.combat.request_dash()

    def take_damage(self, amount: float, source_x: float, source_y: float) -> bool:
        return self.combat.take_damage(amount, source_x, source_y)

    # ------------------------------------------------------------------
    def update(self, dt: float, keys, collision: CollisionWorld) -> None:
        dt = max(0.0, min(dt, 0.05))
        ix = 0.0
        iy = 0.0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            ix -= 1.0
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            ix += 1.0
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            iy -= 1.0
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            iy += 1.0

        length = math.hypot(ix, iy)
        if length > 1.0:
            ix /= length
            iy /= length
        self.input_x, self.input_y = ix, iy
        self.moving = length > 0.0

        combat = self.combat
        combat.update(dt)

        if combat.dead:
            self.vx = self.vy = 0.0
            self.knockback_x = self.knockback_y = 0.0
            self.moving = False
            self.running = False
            self.speed = 0.0
            self.footstep_pulse = False
            self._play_animation(dt, "idle")
            return

        # Facing is locked during a swing but can still be aimed during the
        # startup frames, which keeps the combo responsive.
        can_turn = (
            combat.state not in ATTACK_STATES
            and combat.state != DASH_ATTACK
            and not combat.dodging
            and combat.state != HURT
        )
        if combat.state in ATTACK_STATES and combat.attack_phase == "startup":
            can_turn = True
        if self.moving and can_turn:
            self._face(ix, iy)

        want_run = (
            (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT])
            and self.moving
            and combat.state not in ATTACK_STATES
            and combat.state != DASH_ATTACK
            and not combat.dodging
            and combat.state != HURT
        )
        self.running = want_run

        if combat.dodging:
            progress = 1.0 - max(0.0, combat.dodge_time) / DODGE_DURATION
            speed = DODGE_SPEED * (0.66 + 0.34 * progress)
            self.vx = combat.dodge_x * speed
            self.vy = combat.dodge_y * speed
            self._move(dt, collision)
            self._was_dodging = True
            self._was_dashing = False
        elif combat.dashing:
            progress = 1.0 - max(0.0, combat.dash_time) / DASH_DURATION
            speed = DASH_SPEED * (0.86 + 0.14 * progress)
            self.vx = combat.dash_x * speed
            self.vy = combat.dash_y * speed
            self._move(dt, collision)
            self._was_dashing = True
            self._was_dodging = False
        elif combat.state == HURT:
            self._apply_knockback(dt, collision)
            self._was_dodging = False
            self._was_dashing = False
        else:
            if self._was_dodging or self._was_dashing:
                self.vx = self.vy = 0.0
                self._was_dodging = False
                self._was_dashing = False
            scale = combat.movement_scale
            speed = (PLAYER_RUN_SPEED if want_run else PLAYER_WALK_SPEED) * scale
            target_vx = ix * speed
            target_vy = iy * speed
            if combat.state in ATTACK_STATES:
                # Fluid footwork: attacks keep most of the player's mobility.
                accel = PLAYER_ACCEL * 0.85 if self.moving else PLAYER_FRICTION
                self.vx = _approach(self.vx, target_vx, accel * dt)
                self.vy = _approach(self.vy, target_vy, accel * dt)
            elif self.moving:
                self.vx = _approach(self.vx, target_vx, PLAYER_ACCEL * dt)
                self.vy = _approach(self.vy, target_vy, PLAYER_ACCEL * dt)
            else:
                self.vx = _approach(self.vx, 0.0, PLAYER_FRICTION * dt)
                self.vy = _approach(self.vy, 0.0, PLAYER_FRICTION * dt)
            self._move(dt, collision)

        self.speed = math.hypot(self.vx, self.vy)
        self._play_animation(dt, "run" if want_run else "walk")

    # ------------------------------------------------------------------
    def _move(self, dt: float, collision: CollisionWorld) -> None:
        dx = self.vx * dt
        dy = self.vy * dt
        if not dx and not dy:
            return
        self.x, self.y, hit_x, hit_y = collision.move(
            self.x, self.y, dx, dy, HALF_W, HALF_H
        )
        if hit_x:
            self.vx = 0.0
        if hit_y:
            self.vy = 0.0

    def _apply_knockback(self, dt: float, collision: CollisionWorld) -> None:
        decay = PLAYER_HURT_DECAY * dt
        self.knockback_x = _approach(self.knockback_x, 0.0, decay)
        self.knockback_y = _approach(self.knockback_y, 0.0, decay)
        self.vx, self.vy = self.knockback_x, self.knockback_y
        self._move(dt, collision)

    def _face(self, ix: float, iy: float) -> None:
        # Diagonal movement keeps the current axis when it is close; this
        # avoids flickering between two animation rows while sliding.
        ax, ay = abs(ix), abs(iy)
        horizontal = self.facing in {"left", "right"}
        if abs(ax - ay) < 0.22:
            pass
        elif ax > ay:
            horizontal = True
        else:
            horizontal = False
        if horizontal:
            self.facing = "right" if ix > 0 else "left"
        else:
            self.facing = "down" if iy > 0 else "up"

    # ------------------------------------------------------------------
    def _play_animation(self, dt: float, movement_action: str) -> None:
        combat = self.combat
        if combat.dead:
            self.animator.play("death", "down")
        elif combat.state == HURT:
            self.animator.play("hurt", self.facing)
        elif combat.dodging:
            self.animator.play("dodge", self.facing)
        elif combat.state in ATTACK_STATES or combat.dashing:
            if combat.attack_id != self._anim_attack_id:
                self.animator.play("attack", self.facing, restart=True)
                self.animator.current.fps = combat.attack_fps
                self._anim_attack_id = combat.attack_id
        else:
            if self.moving:
                action = "run" if (self.running and self.speed > 95.0) else "walk"
            else:
                action = "idle"
            self.animator.play(action, self.facing)
        self.animator.update(dt)

        # Footsteps are timed to movement; atmosphere turns them into dust.
        if self.moving and self.speed > 26.0 and not combat.dead:
            self.footstep_timer -= dt
            if self.footstep_timer <= 0.0:
                self.step_side ^= 1
                self.footstep_timer = 0.30 if self.speed < 150 else 0.21
                self.footstep_pulse = True
            else:
                self.footstep_pulse = False
        else:
            self.footstep_timer = 0.0
            self.footstep_pulse = False

    # ------------------------------------------------------------------
    @property
    def attack_hitbox(self) -> AttackHitbox | None:
        combat = self.combat
        if combat.dashing:
            return AttackHitbox(
                self.x,
                self.y,
                self.facing,
                damage=DASH_DAMAGE,
                knockback=DASH_KNOCKBACK,
                heavy=True,
                attack_id=combat.attack_id,
                owner=self,
                reach=DASH_REACH,
                width=DASH_WIDTH,
                shape="arc",
                stage=0,
            )
        if not combat.attack_active:
            return None
        stage = max(1, combat.attack_stage)
        return AttackHitbox(
            self.x,
            self.y,
            self.facing,
            damage=ATTACK_DAMAGE[stage - 1],
            knockback=ATTACK_KNOCKBACK[stage - 1],
            heavy=ATTACK_HEAVY[stage - 1],
            attack_id=combat.attack_id,
            owner=self,
            reach=ATTACK_REACH[stage - 1],
            width=ATTACK_WIDTH[stage - 1],
            shape="spin" if ATTACK_SPIN[stage - 1] else "arc",
            stage=stage,
        )

    # ------------------------------------------------------------------
    def reset(self, x: float, y: float, facing: str) -> None:
        self.x, self.y = x, y
        self.vx = self.vy = 0.0
        self.knockback_x = self.knockback_y = 0.0
        self.facing = facing
        self.moving = False
        self.running = False
        self.speed = 0.0
        self.input_x = self.input_y = 0.0
        self.footstep_timer = 0.0
        self.footstep_pulse = False
        self._anim_attack_id = -1
        self._was_dodging = False
        self._was_dashing = False
        self.vitality.reset()
        self.combat.reset()
        self.animator.play("idle", facing, restart=True)

    # ------------------------------------------------------------------
    @property
    def state(self) -> str:
        """Single readable state: locomotion folds into IDLE-only frames."""
        combat_state = self.combat.state
        if combat_state != IDLE:
            return combat_state
        if self.moving:
            return RUN if (self.running and self.speed > 95.0) else WALK
        return IDLE

    @property
    def sort_y(self) -> float:
        return self.y

    @property
    def look(self) -> tuple[float, float]:
        vx, vy = FACING_VECTORS[self.facing]
        look_x = vx * 26.0 + max(-30.0, min(30.0, self.vx * 0.12))
        look_y = vy * 16.0 + max(-20.0, min(20.0, self.vy * 0.08))
        return look_x, look_y

    def draw(self, target: pygame.Surface, offset: tuple[int, int]) -> None:
        ox, oy = offset
        sx = int(round(self.x)) - ox
        sy = int(round(self.y)) - oy
        shadow = self.assets.soft_shadow(int(40 * self.scale),
                                         int(14 * self.scale))
        target.blit(shadow, (sx - shadow.get_width() // 2,
                             sy - shadow.get_height() // 2 - 1))
        image = self.animator.image
        combat = self.combat
        if combat.hurt_flash > 0.0 and not combat.dead:
            image = image.copy()
            image.fill((120, 42, 54, 0), special_flags=pygame.BLEND_RGBA_ADD)
        elif (combat.invuln > 0.0 and not combat.dodging
              and not combat.dead and int(combat.invuln * 26) % 2 == 0):
            image = image.copy()
            image.set_alpha(150)
        target.blit(image, (sx - self.frame_w // 2, sy - self.foot_line))

    def debug_draw(self, target: pygame.Surface, offset: tuple[int, int]) -> None:
        ox, oy = offset
        rect = pygame.Rect(
            int(round(self.x - HALF_W)) - ox,
            int(round(self.y - HALF_H)) - oy,
            int(HALF_W * 2),
            int(HALF_H * 2),
        )
        pygame.draw.rect(target, (84, 255, 156), rect, 1)
        pygame.draw.line(target, (84, 255, 156),
                         (rect.centerx, rect.centery - 18),
                         (rect.centerx, rect.centery + 24), 1)
        box = self.attack_hitbox
        if box is not None:
            pygame.draw.rect(target, (196, 106, 255), box.rect.move(-ox, -oy), 1)


def _approach(value: float, target: float, delta: float) -> float:
    if value < target:
        return min(target, value + delta)
    if value > target:
        return max(target, value - delta)
    return target
