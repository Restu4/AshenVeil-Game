"""THE HOLLOW GUARDIAN — a three-phase corrupted knight boss.

The guardian is built to be readable rather than random.  Every attack is a
committed sequence of WINDUP -> ACTIVE -> RECOVERY, the wind-up has a growing
floor telegraph and a named warning above the helm, and each phase changes the
numbers rather than the rules:

  PHASE 1  AWAKENING      slow sweep, telegraphed ground slam
  PHASE 2  CORRUPTION     faster pursuit, two-hit combo, void wave, targeted area
  PHASE 3  LAST RESOLVE   aggressive, shorter recovery, VEIL COLLAPSE signature

Damage to the player always goes through ``player.take_damage`` so dodge and
dash i-frames remain authoritative.  Damage to the guardian goes through the
same ``take_damage`` contract as every other enemy, which lets
``CombatManager`` stay the single damage authority.
"""
from __future__ import annotations

import math
import random
from types import SimpleNamespace

import pygame

from scripts.bosses.guardian_art import GuardianAnimator
from scripts.enemy_ai import facing_from_delta
from scripts.health import Health
from scripts.pixel_font import draw_text, text_width
from scripts.village_layout import ARENA_BOSS_BOUNDS

MAX_HEALTH = 1200.0
PHASE_THRESHOLDS = (0.70, 0.35)
PHASE_NAMES = {1: "AWAKENING", 2: "CORRUPTION", 3: "LAST RESOLVE"}
# Deliberately slower than the 96 px/s Fallen Knight, even in the last phase.
PHASE_SPEED = {1: 62.0, 2: 78.0, 3: 92.0}

INTRO = "INTRO"
IDLE = "IDLE"
CHASE = "CHASE"
WINDUP = "WINDUP"
ACTIVE = "ACTIVE"
RECOVERY = "RECOVERY"
PHASE_ROAR = "PHASE_ROAR"
DEATH = "DEATH"
VICTORY = "VICTORY"

ATTACK_STATES = frozenset((WINDUP, ACTIVE, RECOVERY))
WARNING_COLOR = (204, 146, 255)
DANGER_COLOR = (226, 84, 112)

# Every entry is phase-1 baseline; _spec() scales it per phase.
ATTACK_TABLE: dict[str, dict] = {
    "sweep": dict(label="SWEEP", windup=0.86, active=0.16, recovery=0.66,
                  damage=20.0, reach=178.0, arc=112.0, radius=0.0),
    "slam": dict(label="GROUND SLAM", windup=1.06, active=0.20, recovery=0.90,
                 damage=26.0, reach=0.0, arc=0.0, radius=186.0),
    "combo": dict(label="TWIN SWEEP", windup=0.62, active=0.15, recovery=0.58,
                  damage=17.0, reach=186.0, arc=132.0, radius=0.0),
    "wave": dict(label="VOID WAVE", windup=0.96, active=0.26, recovery=0.82,
                 damage=16.0, reach=0.0, arc=0.0, radius=330.0),
    "area": dict(label="VEIL MARK", windup=1.16, active=0.20, recovery=0.84,
                 damage=21.0, reach=0.0, arc=0.0, radius=122.0),
    "signature": dict(label="VEIL COLLAPSE", windup=1.78, active=0.30,
                      recovery=1.05, damage=34.0, reach=0.0, arc=0.0,
                      radius=168.0),
}

_RING_CACHE: dict[tuple, pygame.Surface] = {}
_DISC_CACHE: dict[tuple, pygame.Surface] = {}
_SECTOR_CACHE: dict[tuple, pygame.Surface] = {}


def _ring(radius: int, color, thickness: int = 3) -> pygame.Surface:
    key = ("ring", radius, color, thickness)
    surf = _RING_CACHE.get(key)
    if surf is None:
        surf = pygame.Surface((radius * 2 + 8, radius * 2 + 8), pygame.SRCALPHA)
        pygame.draw.circle(surf, color, (radius + 4, radius + 4), radius,
                           thickness)
        _RING_CACHE[key] = surf
    return surf


def _disc(radius: int, color) -> pygame.Surface:
    key = ("disc", radius, color)
    surf = _DISC_CACHE.get(key)
    if surf is None:
        surf = pygame.Surface((radius * 2 + 8, radius * 2 + 8), pygame.SRCALPHA)
        pygame.draw.circle(surf, color, (radius + 4, radius + 4), radius)
        _DISC_CACHE[key] = surf
    return surf


def _sector(radius: int, arc_deg: float, color) -> pygame.Surface:
    key = ("sector", radius, int(arc_deg), color)
    surf = _SECTOR_CACHE.get(key)
    if surf is None:
        size = radius * 2 + 8
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        center = (radius + 4, radius + 4)
        start = -math.radians(arc_deg / 2 + 90)
        end = math.radians(arc_deg / 2 - 90)
        steps = max(8, int(arc_deg / 6))
        points = [center]
        for i in range(steps + 1):
            angle = start + (end - start) * i / steps
            points.append((center[0] + math.cos(angle) * radius,
                           center[1] + math.sin(angle) * radius))
        pygame.draw.polygon(surf, color, points)
        _SECTOR_CACHE[key] = surf
    return surf


class HollowGuardian:
    """Duck-types the ``Enemy`` contract so CombatManager can own the hits."""

    def __init__(self, assets, x: float, y: float, facing: str = "down",
                 effects=None, camera=None) -> None:
        self.assets = assets
        self.effects = effects
        self.camera = camera
        self.is_boss = True
        self.id = 9001
        self.key = "hollow_guardian"
        self.name = "THE HOLLOW GUARDIAN"
        self.NAME = self.name
        self.subtitle = "WARDEN OF THE ASHEN SHRINE"
        self.ranged = False
        # CombatManager reads a swipe colour from the archetype.
        self.archetype = SimpleNamespace(swipe_color=(196, 126, 255))

        self.animator = GuardianAnimator(scale=2.8)
        self.x = float(x)
        self.y = float(y)
        self.home_x, self.home_y = self.x, self.y
        self.facing = facing
        self.half_w = 34.0
        self.half_h = 22.0
        self.health = Health(MAX_HEALTH)

        self.phase = 1
        self.phase_name = PHASE_NAMES[1]
        self.phase_banner = 0.0
        self.phase_banner_text = ""
        self.state = INTRO
        self.state_time = 0.0
        self.intro_timer = 1.75
        self.roar_timer = 0.0
        self.attack_timer = 1.4
        self.attack_kind = ""
        self.attack_time = 0.0
        self.attack_hit_done = False
        self.combo_hits = 0
        self.attack_target = (self.x, self.y)
        self.signature_timer = 12.0
        self.death_timer = 2.6

        # Enemy-contract fields read by CombatManager / CombatUI.
        self.attack_range = 210.0
        self.attack_cooldown = 0.0
        self.can_attack = True
        self.aggro_timer = 1.0
        self.hurt_timer = 0.0
        self.flash_timer = 0.0
        self.removed = False
        self.pending_swipe = None
        self.pending_projectile = None
        self.rng = random.Random(0xA5E_B055)

        # Ground warnings and waves.  Each entry is a plain dict so it stays
        # cheap to append/prune in the browser.
        self.hazards: list[dict] = []
        self._collision = None
        self._was_dying = False
        self.animator.play("roar", facing, restart=True)

    # ------------------------------------------------------------------
    # Enemy contract
    # ------------------------------------------------------------------
    @property
    def alive(self) -> bool:
        return not self.health.dead and not self.removed

    @property
    def dying(self) -> bool:
        return self.health.dead and not self.removed

    @property
    def sort_y(self) -> float:
        return self.y

    @property
    def hit_rect(self) -> pygame.Rect:
        return pygame.Rect(
            int(round(self.x - self.half_w)),
            int(round(self.y - self.half_h)),
            int(round(self.half_w * 2)),
            int(round(self.half_h * 2)),
        )

    @property
    def health_ratio(self) -> float:
        return self.health.ratio

    # ------------------------------------------------------------------
    def take_damage(self, amount: float, source_x: float, source_y: float,
                    knockback: float, heavy: bool = False,
                    knock_dir: tuple[float, float] | None = None):
        if self.health.dead:
            return 0.0, False
        lost = self.health.damage(amount)
        if lost <= 0.0:
            return 0.0, False
        self.flash_timer = 0.12 if not heavy else 0.17
        self.aggro_timer = 2.0
        if self.health.dead:
            self._die()
            return lost, True

        # A phase boundary roars, clears the floor and gives the player a beat
        # to reposition.  It is damageable during the roar (never a sponge
        # wall) but cannot attack.
        ratio = self.health.ratio
        new_phase = 3 if ratio <= PHASE_THRESHOLDS[1] else (
            2 if ratio <= PHASE_THRESHOLDS[0] else 1)
        if new_phase > self.phase:
            self.phase = new_phase
            self.phase_name = PHASE_NAMES[new_phase]
            self.state = PHASE_ROAR
            self.state_time = 0.0
            self.roar_timer = 1.15
            self.attack_timer = 0.55
            self.combo_hits = 0
            self.hazards.clear()
            self.signature_timer = 9.0
            self.animator.play("roar", self.facing, restart=True)
            self.phase_banner = 2.0
            # The bitmap font has no em dash; use the same middle dot the rest
            # of the UI uses so the banner never renders a "?" glyph.
            self.phase_banner_text = f"PHASE {new_phase} · {self.phase_name}"
            if self.camera is not None:
                self.camera.shake(6.0, 0.35)
            if self.effects is not None:
                self.effects.spawn_nova(self.x, self.y, 210.0)
                self.effects.spawn_flash((38, 16, 58), 0.22)
        return lost, False

    def _die(self) -> None:
        self.state = DEATH
        self.state_time = 0.0
        self.death_timer = 2.6
        self.hazards.clear()
        self.pending_swipe = None
        self.pending_projectile = None
        self.animator.play("death", self.facing, restart=True)
        if self.camera is not None:
            self.camera.shake(8.0, 0.55)
        if self.effects is not None:
            self.effects.spawn_nova(self.x, self.y, 250.0)
            self.effects.spawn_flash((44, 20, 64), 0.36)

    def begin_victory(self) -> None:
        if self.state == VICTORY:
            return
        self.state = VICTORY
        self.state_time = 0.0
        self.hazards.clear()
        self.animator.play("victory", "down", restart=True)

    # ------------------------------------------------------------------
    def update(self, dt: float, player, collision) -> None:
        dt = min(max(0.0, dt), 0.05)
        self._collision = collision
        self.flash_timer = max(0.0, self.flash_timer - dt)
        self.phase_banner = max(0.0, self.phase_banner - dt)
        self.signature_timer = max(0.0, self.signature_timer - dt)
        self.state_time += dt
        self._update_hazards(dt, player)
        self.animator.update(dt)

        # Safety net: health can only reach zero through take_damage, but a
        # loaded/serialised state or a debug poke must never leave a corpse
        # walking around.  Death always wins over any other state.
        if self.health.dead and self.state not in (DEATH, VICTORY):
            self._die()

        if self.state == DEATH:
            self.death_timer -= dt
            # Let the death animation and corpse fade finish, then leave the
            # combat list.  BossManager watches for this to open the victory
            # screen; removal never happens mid-animation.
            if self.death_timer <= -0.35:
                self.removed = True
            return
        if self.state == VICTORY:
            return

        if self.state == INTRO:
            self.intro_timer -= dt
            if self.intro_timer <= 0.0:
                self.state = CHASE
                self.state_time = 0.0
                self.attack_timer = 0.55
            return

        if self.state == PHASE_ROAR:
            self.roar_timer -= dt
            if self.roar_timer <= 0.0:
                self.state = CHASE
                self.state_time = 0.0
                self.attack_timer = 0.35
            return

        if self.state in ATTACK_STATES:
            self._update_attack(dt, player, collision)
            return

        if player.combat.dead:
            self.state = IDLE
            self.animator.play("idle", self.facing)
            return

        dx = player.x - self.x
        dy = player.y - self.y
        distance = math.hypot(dx, dy)

        if self.state in (IDLE, CHASE):
            self.state = CHASE
            self.attack_timer = max(0.0, self.attack_timer - dt)
            if abs(dx) > 3.0:
                self.facing = "right" if dx > 0 else "left"
            elif self.facing not in ("left", "right"):
                self.facing = "right"
            hold = 128.0
            if distance > hold:
                self._move(dt, dx / max(distance, 0.001),
                           dy / max(distance, 0.001), collision)
                self._animate("walk")
            else:
                self.vx = self.vy = 0.0
                self.animator.play("idle", self.facing)
            if (self.attack_timer <= 0.0 and distance <= self.attack_range
                    and not collision.segment_blocked(
                        self.x, self.y - 20.0, player.x, player.y - 20.0, 4.0)):
                self._start_attack(player, distance)

    # ------------------------------------------------------------------
    # Attacks
    # ------------------------------------------------------------------
    def _phase_scale(self) -> tuple[float, float, float, float]:
        """(windup, recovery, damage, radius) multipliers for the phase."""
        if self.phase <= 1:
            return 1.0, 1.0, 1.0, 1.0
        if self.phase == 2:
            return 0.90, 0.86, 1.08, 1.06
        return 0.78, 0.70, 1.30, 1.14

    def _spec(self, kind: str) -> dict:
        base = ATTACK_TABLE[kind]
        wind_mul, rec_mul, dmg_mul, rad_mul = self._phase_scale()
        reach_mul = 1.0 if self.phase <= 1 else (1.06 if self.phase == 2 else 1.12)
        return {
            **base,
            "windup": base["windup"] * wind_mul,
            "recovery": base["recovery"] * rec_mul,
            "active": base["active"],
            "damage": base["damage"] * dmg_mul,
            "radius": base["radius"] * rad_mul,
            "reach": base["reach"] * reach_mul,
            "arc": base["arc"] if self.phase <= 1 else base["arc"] + 8.0,
        }

    def _choose_attack(self, distance: float) -> str:
        if self.phase >= 3 and self.signature_timer <= 0.0:
            return "signature"
        if self.phase <= 1:
            pool = ["sweep", "slam", "sweep"]
        elif self.phase == 2:
            pool = ["sweep", "slam", "combo", "wave", "area", "combo"]
        else:
            pool = ["sweep", "combo", "slam", "wave", "area", "combo", "sweep"]
        if distance > 240.0:
            pool = ["wave", "area"] if self.phase >= 2 else ["slam"]
        elif distance < 110.0:
            pool = ["sweep", "combo", "slam"]
        return self.rng.choice(pool)

    def _start_attack(self, player, distance: float) -> None:
        kind = self._choose_attack(distance)
        spec = self._spec(kind)
        self.state = WINDUP
        self.state_time = 0.0
        self.attack_time = 0.0
        self.attack_kind = kind
        self.attack_hit_done = False
        self.combo_hits = 0
        self.attack_target = (player.x, player.y)
        if abs(player.x - self.x) > 3.0:
            self.facing = "right" if player.x > self.x else "left"
        action = {
            "sweep": "sweep", "slam": "slam", "combo": "combo",
            "wave": "wave", "area": "charge", "signature": "charge",
        }[kind]
        self.animator.play(action, self.facing, restart=True)
        self.attack_cooldown = spec["windup"] + spec["active"] + spec["recovery"]

    def _update_attack(self, dt: float, player, collision) -> None:
        spec = self._spec(self.attack_kind)
        self.attack_time += dt
        if self.state == WINDUP:
            self.vx = self.vy = 0.0
            if self.attack_kind in ("area", "signature"):
                # The mark is locked at cast time; the warning circle is the
                # contract.  Do not silently track the player.
                pass
            if self.attack_time >= spec["windup"]:
                self.state = ACTIVE
                self.state_time = 0.0
                if not self.attack_hit_done:
                    self._resolve_attack(player, collision, spec)
        elif self.state == ACTIVE:
            if self.attack_time >= spec["windup"] + spec["active"]:
                if self.attack_kind == "combo" and self.combo_hits == 0:
                    # Second link: re-aim so the new telegraph is truthful.
                    self.combo_hits = 1
                    self.attack_hit_done = False
                    self.attack_time = 0.0
                    self.state = WINDUP
                    if abs(player.x - self.x) > 3.0:
                        self.facing = "right" if player.x > self.x else "left"
                    self.animator.play("combo", self.facing, restart=True)
                else:
                    self.state = RECOVERY
                    self.state_time = 0.0
                    self.animator.play("idle", self.facing, restart=True)
        elif self.state == RECOVERY:
            if self.attack_time >= spec["windup"] + spec["active"] + spec["recovery"]:
                self.state = CHASE
                self.state_time = 0.0
                self.attack_timer = self._cooldown_after_attack()
                self.animator.play("idle", self.facing)

    def _cooldown_after_attack(self) -> float:
        if self.phase <= 1:
            return self.rng.uniform(1.35, 1.95)
        if self.phase == 2:
            return self.rng.uniform(0.95, 1.40)
        return self.rng.uniform(0.62, 1.00)

    def _resolve_attack(self, player, collision, spec: dict) -> None:
        self.attack_hit_done = True
        kind = self.attack_kind
        damage = spec["damage"]
        if kind in ("sweep", "combo"):
            self._resolve_sweep(player, collision, spec, damage)
        elif kind == "slam":
            self._resolve_slam(player, collision, spec, damage)
        elif kind == "wave":
            self._spawn_wave(damage)
            if self.effects is not None:
                self.effects.spawn_nova(self.x, self.y, 110.0)
        elif kind in ("area", "signature"):
            tx, ty = self.attack_target
            radius = spec["radius"]
            self.hazards.append({
                "kind": "blast", "x": tx, "y": ty, "radius": radius,
                "delay": 0.0, "life": 0.55, "max_life": 0.55,
                "damage": damage, "hit": False, "signature": kind == "signature",
            })
            if kind == "signature":
                if self.camera is not None:
                    self.camera.shake(9.0, 0.5)
                if self.effects is not None:
                    self.effects.spawn_flash((56, 18, 70), 0.38)
                    self.effects.spawn_nova(tx, ty, radius)
                self.signature_timer = 10.0
            else:
                if self.effects is not None:
                    self.effects.spawn_nova(tx, ty, radius * 0.7)

    def _resolve_sweep(self, player, collision, spec: dict, damage: float) -> None:
        fx, fy = (1.0, 0.0) if self.facing == "right" else (-1.0, 0.0)
        dx = player.x - self.x
        dy = player.y - self.y
        distance = math.hypot(dx, dy)
        hit = False
        if distance <= spec["reach"] + 14.0:
            dot = (dx * fx + dy * fy) / max(distance, 0.001)
            half_arc = spec["arc"] / 2.0
            if dot >= math.cos(math.radians(half_arc)):
                if not collision.segment_blocked(
                        self.x, self.y - 20.0, player.x, player.y - 20.0, 4.0):
                    hit = player.take_damage(damage, self.x, self.y)
        self.pending_swipe = (self.x, self.y, self.facing, bool(hit))
        if self.effects is not None:
            self.effects.spawn_nova(self.x + fx * 60.0,
                                    self.y + fy * 60.0, 58.0)

    def _resolve_slam(self, player, collision, spec: dict, damage: float) -> None:
        radius = spec["radius"]
        distance = math.hypot(player.x - self.x, player.y - self.y)
        hit = False
        if distance <= radius + 8.0:
            if not collision.segment_blocked(
                    self.x, self.y - 20.0, player.x, player.y - 20.0, 4.0):
                hit = player.take_damage(damage, self.x, self.y)
        if self.camera is not None:
            self.camera.shake(7.0, 0.28)
        if self.effects is not None:
            self.effects.spawn_nova(self.x, self.y, radius)
            self.effects.spawn_flash((34, 14, 50), 0.18)
        self.hazards.append({
            "kind": "shock", "x": self.x, "y": self.y, "radius": radius,
            "delay": 0.0, "life": 0.42, "max_life": 0.42, "damage": 0.0,
            "hit": True,
        })

    def _spawn_wave(self, damage: float) -> None:
        self.hazards.append({
            "kind": "wave", "x": self.x, "y": self.y,
            "radius": 74.0, "target_radius": 330.0, "speed": 300.0,
            "delay": 0.0, "life": 0.0, "max_life": 0.0,
            "damage": damage, "hit": False, "thickness": 46.0,
        })

    # ------------------------------------------------------------------
    # Hazards / telegraphs
    # ------------------------------------------------------------------
    def _update_hazards(self, dt: float, player) -> None:
        alive: list[dict] = []
        for hazard in self.hazards:
            kind = hazard["kind"]
            if kind == "wave":
                hazard["radius"] += hazard["speed"] * dt
                distance = math.hypot(player.x - hazard["x"],
                                      player.y - hazard["y"])
                if (not hazard["hit"]
                        and abs(distance - hazard["radius"])
                        <= hazard["thickness"] * 0.5 + 14.0
                        and not player.combat.dead
                        and self._can_reach(player)):
                    if not player.combat.invulnerable:
                        player.take_damage(hazard["damage"], hazard["x"],
                                           hazard["y"])
                        hazard["hit"] = True
                if hazard["radius"] > hazard["target_radius"]:
                    hazard["life"] += dt
                    if hazard["life"] > 0.24:
                        continue
                alive.append(hazard)
                continue

            if hazard["delay"] > 0.0:
                hazard["delay"] -= dt
                alive.append(hazard)
                continue

            if not hazard["hit"]:
                hazard["hit"] = True
                distance = math.hypot(player.x - hazard["x"],
                                      player.y - hazard["y"])
                if (distance <= hazard["radius"] + 10.0
                        and not player.combat.dead
                        and not player.combat.invulnerable
                        and self._can_reach(player)):
                    player.take_damage(hazard["damage"], hazard["x"],
                                       hazard["y"])
                if hazard["signature"] and self.effects is not None:
                    _ = 0  # effect already spawned at resolution
            hazard["life"] -= dt
            if hazard["life"] > 0.0:
                alive.append(hazard)
        self.hazards = alive

    def _can_reach(self, player) -> bool:
        """Ground attacks never resolve through a solid shrine wall."""
        if self._collision is None:
            return True
        return not self._collision.segment_blocked(
            self.x, self.y - 16.0, player.x, player.y - 16.0, 3.0)

    def _draw_telegraph(self, target: pygame.Surface, offset) -> None:
        ox, oy = offset
        # Active attack warnings first: sectors and circles under the bodies.
        if self.state == WINDUP:
            spec = self._spec(self.attack_kind)
            k = min(1.0, self.attack_time / max(0.001, spec["windup"]))
            if self.attack_kind in ("sweep", "combo"):
                radius = int(spec["reach"])
                surf = _sector(radius, spec["arc"], (170, 70, 120, 96))
                surf.set_alpha(int(90 + 130 * k))
                cx = int(self.x) - ox
                cy = int(self.y - 20.0) - oy
                target.blit(surf, (cx - radius - 4, cy - radius - 4))
                ring = _ring(radius, WARNING_COLOR, 2)
                ring.set_alpha(int(120 + 110 * k))
                target.blit(ring, (cx - radius - 4, cy - radius - 4))
            elif self.attack_kind == "slam":
                radius = int(spec["radius"])
                cx = int(self.x) - ox
                cy = int(self.y - 20.0) - oy
                disc = _disc(radius, (128, 34, 66, 54))
                disc.set_alpha(int(40 + 90 * k))
                target.blit(disc, (cx - radius - 4, cy - radius - 4))
                ring = _ring(radius, WARNING_COLOR, 2)
                ring.set_alpha(int(120 + 110 * k))
                target.blit(ring, (cx - radius - 4, cy - radius - 4))
            elif self.attack_kind == "wave":
                radius = 330
                cx = int(self.x) - ox
                cy = int(self.y - 20.0) - oy
                ring = _ring(radius, (136, 70, 190, 120), 3)
                ring.set_alpha(int(70 + 120 * k))
                target.blit(ring, (cx - radius - 4, cy - radius - 4))
            elif self.attack_kind in ("area", "signature"):
                tx, ty = self.attack_target
                radius = int(spec["radius"])
                cx = int(tx) - ox
                cy = int(ty) - oy
                disc = _disc(radius, (150, 38, 76, 58))
                disc.set_alpha(int(34 + 92 * k))
                target.blit(disc, (cx - radius - 4, cy - radius - 4))
                ring = _ring(radius, DANGER_COLOR if self.attack_kind == "signature"
                             else WARNING_COLOR, 3 if self.attack_kind == "signature" else 2)
                ring.set_alpha(int(130 + 120 * k))
                target.blit(ring, (cx - radius - 4, cy - radius - 4))
                if self.attack_kind == "signature":
                    for i in range(4):
                        pulse = _ring(max(14, radius - 30 - i * 26),
                                      (206, 118, 255, 90), 1)
                        pulse.set_alpha(int(60 + 80 * k))
                        target.blit(pulse, (cx - radius - 4, cy - radius - 4))

        for hazard in self.hazards:
            kind = hazard["kind"]
            cx = int(hazard["x"]) - ox
            cy = int(hazard["y"]) - oy
            if kind == "wave":
                radius = int(hazard["radius"])
                ring = _ring(radius, (196, 118, 255, 200), 5)
                ring.set_alpha(220)
                target.blit(ring, (cx - radius - 4, cy - radius - 4))
                inner = _ring(max(4, radius - int(hazard["thickness"])),
                              (96, 50, 148, 150), 2)
                inner.set_alpha(180)
                target.blit(inner, (cx - radius - 4, cy - radius - 4))
            elif kind == "blast":
                radius = int(hazard["radius"])
                k = min(1.0, max(0.0, 1.0 - hazard["life"] / hazard["max_life"]))
                disc = _disc(radius, (188, 74, 120, 90))
                disc.set_alpha(int(200 * (1.0 - k * 0.7)))
                target.blit(disc, (cx - radius - 4, cy - radius - 4))
                ring = _ring(radius, (255, 206, 236, 220), 3)
                ring.set_alpha(int(240 * (1.0 - k * 0.5)))
                target.blit(ring, (cx - radius - 4, cy - radius - 4))
            elif kind == "shock":
                radius = int(hazard["radius"] * (1.0 - hazard["life"] / hazard["max_life"]) + 20)
                ring = _ring(radius, (214, 150, 255, 200), 4)
                ring.set_alpha(200)
                target.blit(ring, (cx - radius - 4, cy - radius - 4))

    # ------------------------------------------------------------------
    # Movement / animation
    # ------------------------------------------------------------------
    def _move(self, dt: float, nx: float, ny: float, collision) -> None:
        speed = PHASE_SPEED[self.phase]
        self.vx = nx * speed
        self.vy = ny * speed
        self.x, self.y, hit_x, hit_y = collision.move(
            self.x, self.y, self.vx * dt, self.vy * dt,
            self.half_w, self.half_h,
        )
        if hit_x:
            self.x -= self.vx * dt * 0.5
        if hit_y:
            self.y -= self.vy * dt * 0.5
        x0, y0, x1, y1 = ARENA_BOSS_BOUNDS
        self.x = max(x0, min(x1, self.x))
        self.y = max(y0, min(y1, self.y))

    def _animate(self, action: str) -> None:
        self.animator.play(action, self.facing)

    # ------------------------------------------------------------------
    def draw(self, target: pygame.Surface, offset) -> None:
        self._draw_telegraph(target, offset)
        ox, oy = offset
        sx = int(round(self.x)) - ox
        sy = int(round(self.y)) - oy
        frame = self.animator.image
        fw = self.animator.frame_size
        foot = self.animator.foot_line

        # Huge soft shadow; the guardian should feel planted.
        shadow = self.assets.soft_shadow(int(120 * 1.5), int(40 * 1.5))
        target.blit(shadow, (sx - shadow.get_width() // 2,
                             sy - shadow.get_height() // 2 - 2))

        # A purple aura grows through the phases.
        if self.phase >= 2 and not self.health.dead:
            pulse = 118 + (16 if self.phase >= 3 else 0)
            aura = _disc(pulse, (104, 46, 154, 28))
            aura.set_alpha(38 if self.phase == 2 else 54)
            target.blit(aura, (sx - pulse - 4, sy - pulse // 2 - 4))

        image = frame
        if self.flash_timer > 0.0 and not self.health.dead:
            image = frame.copy()
            image.fill((116, 72, 168, 0), special_flags=pygame.BLEND_RGBA_ADD)
        elif self.state == DEATH:
            progress = 1.0 - max(0.0, self.death_timer) / 2.6
            if progress > 0.45:
                image = frame.copy()
                image.set_alpha(int(255 * max(0.0, 1.0 - (progress - 0.45) / 0.55)))
        target.blit(image, (sx - fw // 2, sy - foot))

        # Named warning above the helm makes the wind-up unambiguous.
        if self.state == WINDUP:
            spec = self._spec(self.attack_kind)
            label = spec["label"]
            color = DANGER_COLOR if self.attack_kind == "signature" else WARNING_COLOR
            k = min(1.0, self.attack_time / max(0.001, spec["windup"]))
            y = sy - foot - 12 - int(6 * k)
            draw_text(target, label, sx, y, 1, color, spacing=1,
                      shadow=(8, 3, 12), center=True)
            width = text_width(label, 1, 1)
            pygame.draw.rect(target, (24, 16, 34),
                             (sx - width // 2 - 4, y + 11, width + 8, 2))
            pygame.draw.rect(target, color,
                             (sx - width // 2 - 4, y + 11,
                              int((width + 8) * k), 2))

    def debug_draw(self, target: pygame.Surface, offset) -> None:
        ox, oy = offset
        pygame.draw.rect(target, (255, 92, 120),
                         self.hit_rect.move(-ox, -oy), 1)
        pygame.draw.circle(target, (255, 190, 92),
                           (int(self.x) - ox, int(self.y) - oy),
                           int(self.attack_range), 1)


__all__ = [
    "ATTACK_STATES",
    "ATTACK_TABLE",
    "HollowGuardian",
    "MAX_HEALTH",
    "PHASE_NAMES",
    "PHASE_SPEED",
    "PHASE_THRESHOLDS",
]
