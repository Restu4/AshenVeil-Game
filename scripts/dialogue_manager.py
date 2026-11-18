"""Data-driven dialogue with choices, progression and persistent story flags."""
from __future__ import annotations

from scripts.village_data import MAX_SAVE_ENTRIES, dialogue_definition

REVEAL_TIME = 0.14


class DialogueManager:
    """Owns one open conversation at a time; no pygame imports."""

    def __init__(self, on_flag=None, on_change=None) -> None:
        self.on_flag = on_flag
        self.on_change = on_change
        self.active = False
        self.dialogue_id = ""
        self.npc_id = ""
        self.pages: list[dict] = []
        self.page_index = 0
        self.reveal = 0.0
        self.seen: list[str] = []
        self.flags: dict[str, bool] = {}

    # ------------------------------------------------------------------
    def _changed(self) -> None:
        if callable(self.on_change):
            self.on_change()

    def open(self, dialogue_id: str, npc_id: str = "") -> bool:
        definition = dialogue_definition(str(dialogue_id).lower())
        if definition is None:
            return False
        pages = definition.get("pages")
        if not isinstance(pages, list) or not pages:
            return False
        self.dialogue_id = str(dialogue_id)
        self.npc_id = str(npc_id)
        self.pages = [page for page in pages if isinstance(page, dict)]
        if not self.pages:
            return False
        self.page_index = 0
        self.reveal = 0.0
        self.active = True
        # A page's action fires when the page is first read, not when the
        # player leaves it.  This keeps story flags in sync with the text.
        self._apply_action(self.page.get("action", ""))
        if self.dialogue_id not in self.seen:
            self.seen.append(self.dialogue_id[:48])
            self._changed()
        return True

    def close(self) -> None:
        was_active = self.active
        self.active = False
        self.pages = []
        self.page_index = 0
        if was_active:
            self._changed()

    def update(self, dt: float) -> None:
        self.reveal = min(1.0, self.reveal + max(0.0, dt) / REVEAL_TIME)

    # ------------------------------------------------------------------
    @property
    def page(self) -> dict:
        if not self.active or not self.pages:
            return {}
        return self.pages[min(self.page_index, len(self.pages) - 1)]

    @property
    def text(self) -> str:
        return str(self.page.get("text", ""))

    @property
    def choices(self) -> list[dict]:
        raw = self.page.get("choices")
        if not isinstance(raw, list):
            return []
        return [choice for choice in raw if isinstance(choice, dict)][:4]

    @property
    def has_choices(self) -> bool:
        return bool(self.choices)

    # ------------------------------------------------------------------
    def set_flag(self, key, value=True) -> bool:
        name = str(key).strip().lower()
        if not name or len(name) > 48:
            return False
        if name not in self.flags and len(self.flags) >= MAX_SAVE_ENTRIES:
            return False
        flag = bool(value)
        if self.flags.get(name) == flag:
            return False
        self.flags[name] = flag
        if callable(self.on_flag):
            self.on_flag(name, flag)
        self._changed()
        return True

    def _apply_action(self, action, base: str = "") -> str:
        """Apply one action and return a state change for Game to route."""
        if isinstance(action, str):
            return action.strip().lower()
        if not isinstance(action, dict):
            return base
        kind = str(action.get("kind", action.get("action", ""))).strip().lower()
        if kind == "set_flag":
            self.set_flag(action.get("flag"), action.get("value", True))
        elif kind in ("open_shop", "open_blacksmith", "close"):
            return kind
        return base

    def _follow(self, target) -> str:
        """Move to the linked page and apply *that* page's entry action."""
        if target is not None:
            try:
                self.page_index = max(0, min(len(self.pages) - 1, int(target)))
            except (TypeError, ValueError):
                self.page_index = min(self.page_index + 1, len(self.pages) - 1)
        elif not self.has_choices:
            if self.page_index + 1 >= len(self.pages):
                self.close()
                return "close"
            self.page_index += 1
        else:
            # A chooser page without a link stays put; no action to replay.
            return ""
        return self._apply_action(self.page.get("action", ""))

    def advance(self) -> str:
        """Continue a page without choices; safe to call on a chooser page."""
        if not self.active:
            return ""
        if self.has_choices:
            return ""
        return self._follow(self.page.get("next"))

    def choose(self, index: int) -> str:
        if not self.active:
            return ""
        choices = self.choices
        if not 0 <= index < len(choices):
            return ""
        choice = choices[index]
        result = self._apply_action(choice.get("action", ""))
        target = choice.get("next")
        if target is None and result in ("open_shop", "open_blacksmith", "close"):
            self.close()
            return result
        follow = self._follow(target)
        return result or follow

    # ------------------------------------------------------------------
    def load_state(self, raw) -> None:
        if not isinstance(raw, dict):
            return
        seen = raw.get("seen")
        if isinstance(seen, (list, tuple, set)):
            for dialogue_id in seen:
                if (isinstance(dialogue_id, str) and dialogue_id in
                        ("merchant", "blacksmith", "veil_keeper")
                        and dialogue_id not in self.seen):
                    self.seen.append(dialogue_id)
        flags = raw.get("flags")
        if isinstance(flags, dict):
            for key, value in flags.items():
                if len(self.flags) >= MAX_SAVE_ENTRIES:
                    break
                name = str(key).strip().lower()
                if name:
                    self.flags[name[:48]] = bool(value)

    def to_state(self) -> dict:
        return {
            "seen": list(self.seen[:MAX_SAVE_ENTRIES]),
            "flags": dict(self.flags),
        }


__all__ = ["DialogueManager", "REVEAL_TIME"]
