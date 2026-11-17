# ASHEN VEIL — Ashen Village Environment Pack

Environment art pack for the Python + Pygame-CE + Pygbag browser prototype.

## Included
- `assets/environment/ashen_village_atlas.png` — complete environment atlas.
- `ground_terrain.png` — broad crop containing terrain and ground tiles.
- `buildings_architecture.png` — broad crop containing houses, church and tower.
- `props_and_decorations.png` — broad crop containing trees, fences, graves, barrels,
  lanterns, rocks, statues and other props.
- `atlas_manifest.json` — source image dimensions and crop coordinates.
- `tools/crop_atlas.py` — helper to crop a selected rectangle from the atlas.

## Important
The source image is an irregularly arranged atlas, not a perfectly aligned tile sheet.
The category PNGs are broad crops only. Individual tiles/sprites still need to be sliced
and checked manually before being used as collision objects or tilemap cells.

## Use in Pygame
```python
import pygame

atlas = pygame.image.load(
    "assets/environment/ashen_village_atlas.png"
).convert_alpha()

# Example: crop a rectangle after checking its coordinates.
rect = pygame.Rect(x, y, width, height)
sprite = atlas.subsurface(rect).copy()
sprite = pygame.transform.scale_by(sprite, 3)
```

For crisp pixel art, use `pygame.transform.scale` / `scale_by` (nearest-neighbor)
and do not use smoothscale.
