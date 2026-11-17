"""Static level metadata for the ASHEN VEIL level select.

This module is pure data (no pygame, no saves) so the UI, the progression
manager and headless tests all read the same description of the world.

Only Level 01 is playable in this build.  Levels 02-04 are real selection
entries with names, atmosphere, boss lore and lock states, but no unfinished
maps are generated for them.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StageInfo:
    key: str
    number: int
    name: str
    objective: str
    summary: str
    x: float = 0.0
    y: float = 0.0


@dataclass(frozen=True)
class LevelInfo:
    level_id: str
    number: int
    name: str
    subtitle: str
    description: str
    boss_name: str
    boss_subtitle: str
    accent: tuple[int, int, int]
    preview: str
    playable: bool
    stages: tuple[StageInfo, ...] = ()
    coming_soon: str = ""


STAGE_01 = StageInfo(
    key="abandoned_village",
    number=1,
    name="ABANDONED VILLAGE",
    objective="CUT DOWN THE RISEN DEAD",
    summary="A cold square, a dead well, and three shapes that should not move.",
    x=1500.0,
    y=1080.0,
)

STAGE_02 = StageInfo(
    key="corrupted_path",
    number=2,
    name="CORRUPTED PATH",
    objective="BREAK THE CORRUPTED WARDEN",
    summary="Purple moss crawls over the west road. The Warden waits with an escort.",
    x=900.0,
    y=1120.0,
)

STAGE_03 = StageInfo(
    key="forgotten_shrine",
    number=3,
    name="FORGOTTEN SHRINE",
    objective="STEP INTO THE VEIL GATE",
    summary="Broken statues and a breathing portal. The air tastes of iron.",
    x=566.0,
    y=1138.0,
)

STAGE_04 = StageInfo(
    key="boss_arena",
    number=4,
    name="BOSS ARENA",
    objective="DEFEAT THE HOLLOW GUARDIAN",
    summary="A ruined shrine sealed by dead roots. There is no way back in the dark.",
    x=2638.0,
    y=690.0,
)

LEVELS: tuple[LevelInfo, ...] = (
    LevelInfo(
        level_id="01",
        number=1,
        name="ASHEN VILLAGE",
        subtitle="THE MOON IS DEAD",
        description=(
            "A dying village beneath a dead moon. Timber roofs lean into ash, "
            "the well has run black, and the risen dead keep their old patrols. "
            "Follow the corruption west to the forgotten shrine, then descend "
            "into the hollow where the village's guardian still kneels."
        ),
        boss_name="THE HOLLOW GUARDIAN",
        boss_subtitle="WARDEN OF THE ASHEN SHRINE",
        accent=(174, 122, 244),
        preview="village",
        playable=True,
        stages=(STAGE_01, STAGE_02, STAGE_03, STAGE_04),
    ),
    LevelInfo(
        level_id="02",
        number=2,
        name="HOLLOW FOREST",
        subtitle="WHERE ROOTS DRINK",
        description=(
            "Beyond the village the trees have grown inward. Black roots drink "
            "what the veil leaves behind, and something enormous moves between "
            "the trunks without ever touching the ground."
        ),
        boss_name="THE THORNMAW",
        boss_subtitle="ROOT-EATEN COLOSSUS",
        accent=(92, 158, 118),
        preview="forest",
        playable=False,
        coming_soon="MAP NOT YET FORGED",
    ),
    LevelInfo(
        level_id="03",
        number=3,
        name="FORGOTTEN DUNGEON",
        subtitle="STONE THAT REMEMBERS",
        description=(
            "A prison built under the shrine, older than the village above it. "
            "The cells are empty, but the chains still pull taut in the dark, "
            "and the jailer has not lost the habit of walking his hall."
        ),
        boss_name="THE CHAINED JAILER",
        boss_subtitle="KEEPER OF EMPTY CELLS",
        accent=(132, 138, 176),
        preview="dungeon",
        playable=False,
        coming_soon="MAP NOT YET FORGED",
    ),
    LevelInfo(
        level_id="04",
        number=4,
        name="BLACKTHORN CASTLE",
        subtitle="THE LAST THRONE",
        description=(
            "The road ends at a castle grown from one black thorn. Banners rot "
            "in the windows and a crown sits on a throne of roots. Whatever "
            "still wears it has been waiting for a sword like yours."
        ),
        boss_name="THE BLACKTHORN KING",
        boss_subtitle="THE CROWNED ROT",
        accent=(186, 74, 92),
        preview="castle",
        playable=False,
        coming_soon="MAP NOT YET FORGED",
    ),
)

LEVEL_BY_ID: dict[str, LevelInfo] = {level.level_id: level for level in LEVELS}


def get_level(level_id: str) -> LevelInfo:
    return LEVEL_BY_ID.get(level_id, LEVELS[0])


def next_level_id(level_id: str) -> str | None:
    index = next((i for i, level in enumerate(LEVELS)
                  if level.level_id == level_id), None)
    if index is None or index + 1 >= len(LEVELS):
        return None
    return LEVELS[index + 1].level_id


def level_index(level_id: str) -> int:
    return next((i for i, level in enumerate(LEVELS)
                 if level.level_id == level_id), 0)


__all__ = [
    "LEVELS",
    "LEVEL_BY_ID",
    "LevelInfo",
    "StageInfo",
    "get_level",
    "level_index",
    "next_level_id",
]
