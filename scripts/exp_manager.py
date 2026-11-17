"""Character EXP, level, attribute points and anti-farming guards.

One ExpManager owns all progression state in memory.  It is the single
authority for level-ups and attribute allocation; the save layer only mirrors
its validated snapshot.  Level-up callbacks let the game pause briefly, refresh
stats and show feedback without this module importing pygame or any manager.
"""
from __future__ import annotations

from scripts.progression_config import (
    ATTRIBUTE_KEYS,
    ATTRIBUTE_POINTS_PER_LEVEL,
    MAX_ATTRIBUTE_RANK,
    MAX_DEFEATED_KEYS,
    MAX_LEVEL,
    QUEST_EXP_DEFAULT,
    SKILL_POINT_INTERVAL,
    START_LEVEL,
    attribute_points_for_level,
    clamp_int,
    defeated_key,
    exp_for_enemy,
    exp_for_level,
    skill_points_for_level,
)


class ExpManager:
    """A fully validated, recomputable snapshot of character progression."""

    def __init__(self, profile: dict | None = None, on_change=None,
                 on_level_up=None) -> None:
        self.on_change = on_change
        self.on_level_up = on_level_up
        self.reset()
        if isinstance(profile, dict):
            self.load(profile)

    # ------------------------------------------------------------------
    def reset(self) -> None:
        self.level = START_LEVEL
        self.exp = 0
        self.total_exp = 0
        self.attributes: dict[str, int] = {key: 0 for key in ATTRIBUTE_KEYS}
        self.attribute_points = 0
        self.skill_points = 0
        self.purchased_nodes: set[str] = set()
        self.defeated: set[str] = set()

    def load(self, profile: dict) -> None:
        """Rebuild state from a canonical save profile; never trust raw data."""
        self.reset()
        player = profile.get("player")
        player = player if isinstance(player, dict) else {}

        level = clamp_int(player.get("level", START_LEVEL),
                          START_LEVEL, MAX_LEVEL, START_LEVEL)
        self.level = level

        need = exp_for_level(level)
        self.exp = clamp_int(player.get("exp", 0), 0, max(0, need - 1), 0)

        total = clamp_int(player.get("total_exp", self.exp), 0, 10 ** 9,
                          self.exp)
        self.total_exp = max(self.exp, total)

        raw_attrs = player.get("attributes")
        raw_attrs = raw_attrs if isinstance(raw_attrs, dict) else {}
        for key in ATTRIBUTE_KEYS:
            self.attributes[key] = clamp_int(
                raw_attrs.get(key, 0), 0, MAX_ATTRIBUTE_RANK, 0
            )

        # Old Phase 5/6 profiles have no point counters.  Grant what their
        # stored level already earned, minus attributes they actually hold.
        if "attribute_points" in player:
            self.attribute_points = clamp_int(
                player.get("attribute_points"), 0, 10 ** 6, 0
            )
        else:
            spent = sum(self.attributes.values())
            self.attribute_points = max(
                0, attribute_points_for_level(level) - spent
            )

        if "skill_points" in player:
            self.skill_points = clamp_int(
                player.get("skill_points"), 0, 10 ** 6, 0
            )
        else:
            self.skill_points = skill_points_for_level(level)

        raw_nodes = player.get("skill_nodes")
        if isinstance(raw_nodes, (list, tuple, set)):
            for node_id in raw_nodes:
                if isinstance(node_id, str) and node_id:
                    self.purchased_nodes.add(node_id[:32])

        raw_defeated = profile.get("defeated_enemies")
        if isinstance(raw_defeated, (list, tuple, set)):
            for key in raw_defeated:
                if isinstance(key, str) and key:
                    self.defeated.add(key[:80])
        self._trim_defeated()

    # ------------------------------------------------------------------
    @property
    def is_max(self) -> bool:
        return self.level >= MAX_LEVEL

    @property
    def exp_required(self) -> int:
        return 0 if self.is_max else exp_for_level(self.level)

    @property
    def exp_ratio(self) -> float:
        required = self.exp_required
        if required <= 0:
            return 1.0
        return max(0.0, min(1.0, self.exp / float(required)))

    # ------------------------------------------------------------------
    def notify_change(self) -> None:
        if callable(self.on_change):
            self.on_change()

    def _emit_level_ups(self, events: list[dict]) -> None:
        if not events:
            return
        if callable(self.on_level_up):
            for event in events:
                self.on_level_up(event)

    # ------------------------------------------------------------------
    def award_exp(self, amount, reason: str = "QUEST") -> list[dict]:
        """Add EXP and resolve every level gained by this single reward."""
        try:
            gain = max(0, int(amount))
        except (TypeError, ValueError, OverflowError):
            gain = 0
        if gain <= 0:
            return []

        self.total_exp += gain
        self.exp += gain
        events: list[dict] = []

        while not self.is_max and self.exp >= self.exp_required:
            self.exp -= self.exp_required
            self.level += 1
            points = ATTRIBUTE_POINTS_PER_LEVEL
            self.attribute_points += points
            skill_gain = (
                1 if SKILL_POINT_INTERVAL > 0
                and (self.level - START_LEVEL) % SKILL_POINT_INTERVAL == 0
                else 0
            )
            self.skill_points += skill_gain
            events.append({
                "level": self.level,
                "attribute_points": points,
                "skill_points": skill_gain,
                "reason": str(reason).upper(),
            })

        if self.is_max:
            self.exp = 0

        self._emit_level_ups(events)
        self.notify_change()
        return events

    def award_quest_exp(self, amount) -> list[dict]:
        """Public API for future quest rewards (no enemy marker required)."""
        return self.award_exp(amount, "QUEST")

    def award_enemy_kill(self, enemy, level_id: str = "") -> list[dict]:
        """Award once per defeated enemy, even across reloads and restarts."""
        if enemy is None:
            return []
        # CombatManager calls this from its death hook; a live enemy must never
        # be rewarded, and neither may a stale second call for the same corpse.
        if bool(getattr(enemy, "alive", False)):
            return []

        key = defeated_key(enemy, level_id)
        if key in self.defeated:
            return []
        self.defeated.add(key)
        self._trim_defeated()

        reward = exp_for_enemy(enemy)
        if reward <= 0:
            self.notify_change()
            return []
        return self.award_exp(reward, "KILL")

    def _trim_defeated(self) -> None:
        if len(self.defeated) <= MAX_DEFEATED_KEYS:
            return
        extras = len(self.defeated) - MAX_DEFEATED_KEYS
        for key in list(self.defeated)[:extras]:
            self.defeated.discard(key)

    # ------------------------------------------------------------------
    def allocate_attribute(self, name: str) -> bool:
        key = str(name).lower()
        if key not in ATTRIBUTE_KEYS:
            return False
        if self.attribute_points <= 0:
            return False
        if self.attributes[key] >= MAX_ATTRIBUTE_RANK:
            return False
        self.attributes[key] += 1
        self.attribute_points -= 1
        self.notify_change()
        return True

    def reset_attributes(self) -> bool:
        """Refund every allocated point (the character-screen reset action)."""
        refunded = sum(self.attributes.values())
        if refunded <= 0:
            return False
        for key in ATTRIBUTE_KEYS:
            self.attributes[key] = 0
        self.attribute_points += refunded
        self.notify_change()
        return True

    def spend_skill_point(self) -> bool:
        if self.skill_points <= 0:
            return False
        self.skill_points -= 1
        return True

    def refund_skill_point(self) -> None:
        self.skill_points += 1

    # ------------------------------------------------------------------
    def to_profile(self) -> dict:
        """Return the additive save fragment owned by this manager."""
        return {
            "player": {
                "level": self.level,
                "exp": self.exp,
                "total_exp": self.total_exp,
                "attributes": dict(self.attributes),
                "attribute_points": self.attribute_points,
                "skill_points": self.skill_points,
                "skill_nodes": sorted(self.purchased_nodes),
            },
            "defeated_enemies": sorted(self.defeated),
        }


__all__ = ["ExpManager"]
