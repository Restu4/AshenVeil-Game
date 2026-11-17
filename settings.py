"""ASHEN VEIL — global configuration and palette."""
from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ASSETS = BASE_DIR / "assets"

# Internal render resolution.  The browser canvas uses the same aspect ratio
# (16:9); the final frame is nearest-neighbour scaled to the window.
SCREEN_W = 1280
SCREEN_H = 720
FPS = 60
TITLE = "ASHEN VEIL"
SUBTITLE = "ASHEN VILLAGE"

WORLD_W = 3200
WORLD_H = 2400
TILE = 96

PLAYER_SCALE = 2.0  # crisp integer upscale so the character reads on screen
ENEMY_SCALE = 2.0

PLAYER_WALK_SPEED = 118.0
PLAYER_RUN_SPEED = 218.0
PLAYER_ACCEL = 1400.0
PLAYER_FRICTION = 1700.0

CAMERA_SMOOTH = 7.5

STAMINA_MAX = 100.0
STAMINA_DRAIN = 19.0
STAMINA_REGEN = 25.0
STAMINA_REGEN_DELAY = 0.8

# --------------------------------------------------------------------------
# Palette — sampled from the character sheet + environment atlas.
# --------------------------------------------------------------------------
INK = (9, 8, 12)
VOID = (14, 12, 19)
CHARCOAL = (24, 21, 31)
CHARCOAL_2 = (35, 31, 44)
STONE_DARK = (48, 44, 54)
STONE = (83, 78, 92)
BONE = (178, 169, 160)
BONE_DIM = (129, 121, 116)
PURPLE_DEEP = (36, 27, 48)
PURPLE = (91, 72, 122)
PURPLE_LIGHT = (158, 138, 192)
PURPLE_GLOW = (151, 112, 226)
LAVENDER = (206, 192, 226)
MOSS_DARK = (33, 43, 33)
MOSS = (63, 82, 58)
MOSS_LIGHT = (92, 112, 76)
BROWN_DARK = (42, 32, 27)
BROWN = (82, 63, 48)
BROWN_LIGHT = (126, 99, 73)
BLOOD_DARK = (66, 22, 28)
BLOOD = (116, 38, 46)
BLOOD_LIGHT = (158, 62, 61)
STEEL = (128, 130, 146)
STEEL_LIGHT = (188, 190, 206)
