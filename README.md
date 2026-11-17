# ASHEN VEIL — Ashen Village

A first-playable, top-down dark fantasy action-RPG village built with **Python
+ Pygame-CE**, packaged for the browser with **Pygbag**. This slice is about
atmosphere, exploration and a small, deliberate duel: Fallen Knights roam the
dying village and the player has a three-hit sword combo and a dodge roll.
There is no quest, inventory or boss system yet.

The playable character uses the original ASHEN VEIL spritesheet (hooded figure,
black face, single white eye, large back sword, cape and sandals). The village
reuses artwork from the original environment concept atlas, sliced into named
sprites — the irregular atlas is never stretched or used as a flat backdrop.

## Features

- **Explorable Ashen Village** — 3200×2400 hand-authored world with a cobbled
  plaza, well, timber houses, a church, a ruined stone gate, a graveyard, a
  purple tower and portal, ruined arches, fences, carts, barrels, crates, dead
  trees, rocks and debris.
- **Eight-direction movement** with idle, walk and run animations, acceleration,
  friction and sprint stamina.
- **Hybrid action combat** — left mouse starts a three-hit sword combo
  (25/30/45 damage) with directional attack animations, startup/active/recovery
  frames and a buffered combo window. Each swing resolves damage once per enemy
  and is stopped by walls.
- **Dodge roll** — `Space` rolls in the input direction (or facing), grants
  ~0.20 s of invulnerability, costs 20 stamina, moves at 370 px/s and has a
  0.45 s cooldown. Attacks commit through startup/active frames.
- **Fallen Knight enemies** — a purpose-built 64×64 pixel-art undead sentinel
  (idle, walk, attack, hurt, death) with delta-time IDLE/PATROL/CHASE/ATTACK/
  HURT/DEATH AI, 180 px detection, 42 px attack range, 15 damage, collision
  sliding, obstacle avoidance, leashing and single-application attacks.
- **Combat feedback** — pre-rendered slash arcs, impact sparks, floating damage
  numbers, enemy hit flash, player hurt vignette, knockback and restrained
  camera shake on the heavy finisher, all in the village's cold purple palette.
- **Pixel-aware collision** with sliding along walls, houses, gates, trees and
  props, plus solid world borders.
- **Smooth clamped camera** with subtle look-ahead, Y-sorted props and player,
  and nearest-neighbour scaling to the window.
- **Baked ground detail** — seamless grass/dirt/cobble samples, warped path and
  plaza masks, scattered detail, static prop shadows and baked lantern light
  pools, so the runtime only draws a small animated flame bloom.
- **Night atmosphere** — moon haze, drifting fog, ash, lantern motes, footstep
  dust, a cold player aura and a vignette.
- **Custom pixel HUD** — vitality and stamina bars, level badge, “ASHEN VEIL”
  title treatment, controls hint, an intro card and an engaged-enemy health bar
  with the knight's name. Cached surfaces; a “YOU DIED” veil with restart.
- **Browser build** via Pygbag with an async-compatible game loop.

## Controls

| Input | Action |
| --- | --- |
| `WASD` / arrow keys | Move (8 directions) |
| `Left mouse button` | Attack — press again during a swing to chain the 3-hit combo |
| `Space` | Dodge roll (invulnerability frames) |
| `Shift` | Run (drains stamina) |
| `R` / click | Rise again after death |
| `H` | Toggle control hints |
| `F1` / `F3` | Toggle debug overlay |
| `F11` | Toggle fullscreen (desktop) |
| `Esc` | Quit (desktop) |

The help bar hides itself after a short while; press `H` to bring it back. The
browser builds capture the mouse on the canvas, so click once to focus before
using keyboard controls.

## Requirements

- Python 3.12 or 3.13 recommended (Pygame-CE and Pygbag are pinned).
- A desktop environment for local play; a browser for the Pygbag version.

## Run locally

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
python main.py
```

The game opens at 1280×720. Resize the window and the frame is letterboxed with
nearest-neighbour scaling; the internal pixel grid stays crisp.

## Run in the browser (Pygbag)

From the project root:

```bash
python -m pygbag --title "ASHEN VEIL" .
```

Then open **http://localhost:8000** in a browser. The first run downloads the
Pygbag web runtime from its CDN and builds the game; later runs reuse the local
cache. Click the canvas if the browser asks for interaction first.

Build without starting the test server:

```bash
python -m pygbag --build --title "ASHEN VEIL" .
```

The result is written to `build/web/`. For an itch.io-style archive:

```bash
python -m pygbag --archive --title "ASHEN VEIL" .
```

### Web build contents

`pygbag.ini` excludes development-only files from the browser package:

- `tools/` (offline asset baking and previews)
- `screenshots/` (preview captures)
- `assets/environment/` (source atlas; runtime uses `assets/sliced/`)
- `README.md` and `requirements-dev.txt`

The original source art stays in the repository for provenance, but the web
package only ships the sliced sprites and the baked `assets/generated/ground.png`
(about 5 MB, palette-quantised for a faster first load). Allow a moment for that
texture on the first load.

## Project structure

```text
main.py                     Async game loop, input, update/draw/present
settings.py                 Resolution, world size, speeds, palette
pygbag.ini                  Browser build exclusions
requirements.txt            Runtime dependencies
requirements-dev.txt        Optional asset-tool dependencies

assets/
  characters/               Original player sheet + frame metadata
  enemies/                  Fallen Knight sheet + animation metadata (generated)
  environment/              Original concept atlas and manifest (source only)
  sliced/                   85 named sprites cut from the atlas + manifest.json
  generated/ground.png      Baked 3200×2400 ground texture

scripts/
  asset_loader.py           Manifest/image/ground/enemy/shadow loading and caching
  animation.py              Sheet animation and action/facing animator
  player.py                 Movement, stamina, footsteps, combat integration, 2x sprite
  player_combat.py          Attack/combo/dodge/hurt/death state machine and timers
  combat_config.py          All combat tuning (damage, timings, reach, knockback)
  health.py                 Clamped health pool shared by player and enemies
  stamina.py                Delta-time stamina pool with regen delay and exhaustion
  hitbox.py                 World-space attack volumes and facing helpers
  enemy.py                  Fallen Knight entity: animation, health, damage, drawing
  enemy_ai.py               Delta-time IDLE/PATROL/CHASE/ATTACK/HURT/DEATH AI
  combat_manager.py         Swing resolution, engagement, hit events and feedback
  effects.py                Slash arcs, particles, damage numbers, flashes, vignette
  combat_ui.py              Engaged-enemy bar and the death veil
  collision.py              Prop footprints, spatial hash, sliding movement
  camera.py                 Smooth clamped camera and world→screen conversion
  village_layout.py         Canonical roads, patches, props, lights, spawn
  world.py                  Prop instances, culling, Y-sorting, ground blit
  atmosphere.py             Night overlay, glows, fog, ash, motes, dust, vignette
  hud.py                    Cached HUD panels, bars, title, help, intro
  pixel_font.py             5×7 bitmap font and text renderer

tools/                      Development only (not shipped to the web build)
  slice_assets.py           Re-cuts the source atlas into assets/sliced/
  bake_ground.py            Rebakes assets/generated/ground.png
  preview.py                Headless landmark + combat screenshots → screenshots/
  bench.py                  Headless draw benchmark (exploration + combat frames)
  test_combat.py            Headless functional checks (83 assertions)
  generate_fallen_knight.py Regenerates the Fallen Knight sheet

screenshots/                Landmark preview renders from tools/preview.py
```

## Rebuilding art (optional)

The runtime never needs the source atlas or the baking tools. If you change the
layout or want to regenerate the world texture:

```bash
pip install -r requirements-dev.txt
python tools/slice_assets.py     # only needed after editing atlas rectangles
python tools/bake_ground.py      # regenerates assets/generated/ground.png
python tools/preview.py          # landmark screenshots
python tools/bench.py            # draw-phase timings
```

The ground baker reads the same `scripts/village_layout.py` data as the game, so
roads, plaza and static light pools stay aligned with props and collision.

## Performance notes

- The ground is one pre-baked texture; the runtime blits only the visible source
  rectangle instead of compositing hundreds of tiles.
- Props are culled against the camera view and sorted by ground contact before
  drawing.
- HUD panels, title, help and intro are pre-rendered once.
- Lantern bloom is capped at a small radius because the wide light pools are
  baked into the ground; fog was reduced to six blobs and footstep-dust scales
  are cached.
- Slash arcs are drawn once into cached surfaces (3 stages × 4 facings);
  particles and damage numbers use cached dots and glyph surfaces and are
  capped at 160 particles / 16 numbers.
- Enemy animation sheets are shared between all Fallen Knights; each knight
  only stores its own animator indices and timers.
- `tools/bench.py` on the development machine reports roughly 6–7 ms for a full
  1280×720 draw, both exploring and in a busy combat frame with three knights,
  a slash, sparks and the engaged bar (world ≈ 2 ms, atmosphere ≈ 3 ms,
  effects ≈ 0.7 ms, HUD ≈ 0.4 ms) with the dummy video driver. Browser timing
  will differ.

## Verification status

`python tools/test_combat.py` runs 83 headless assertions covering:

- walking, running, sprint stamina, the IDLE/WALK/RUN state surface and
  legacy collision/camera clamping;
- the three-hit combo (25/30/45), buffering, one hit per swing, the heavy-hit
  shake and the kill, plus hitbox checks in all four facings;
- dodge cost, distance, i-frames, cooldown and stamina gating;
- stamina regen delay, floor and ceiling, and refusal feedback;
- player damage, post-hit invulnerability, death, movement lock and restart;
- knight detection, chase, attack range, 15 damage, one application per
  swing and the forward attack arc missing a player who rolls behind;
- knight patrol radius, hurt/knockback recovery, death and removal;
- wall obstruction for both the sword (no cutting through stone) and knight
  movement (never inside a house footprint);
- synthetic mouse/keyboard events and six awaited frames of the async loop;
- full-resolution combat frames with HUD, effects, debug overlays and the
  death veil.

Also verified:

- Landmark and combat views render and are saved in `screenshots/`
  (`combat_impact.png`, `combat_kill.png`, `combat_death.png`).
- `python -m pygbag --build --title "ASHEN VEIL" .` produces a 7.7 MB
  `build/web/game.apk`; serving `build/web/` returns the page and APK with
  HTTP 200.
- A live interactive browser session (real input, audio, canvas display) still
  needs a manual check in your own browser; this environment cannot verify
  actual in-browser behaviour. The async loop, event handlers and rendering
  paths are exercised headlessly under the SDL dummy driver.

## Missing / reused animation assets

- The player sheet has no separate attack variants for the three combo links,
  so all three swings reuse the same six-frame directional `attack` row with
  different damage, reach, knockback and feedback. Directional `dodge`,
  `hurt` and a single `death` row already exist and are reused as-is.
- The Fallen Knight has `idle`, `walk`, `attack`, `hurt` (all four directions)
  and one `death_down` row. Non-down death directions fall back to
  `death_down`; `death` reads as the knight collapsing into ash.
- No new frames were invented for the player. The knight sheet is generated
  from code in `tools/generate_fallen_knight.py`, not reused player art.

## Credits

Character spritesheet, environment concept atlas and ASHEN VEIL art direction
come from the project’s included original artwork. The Fallen Knight sheet,
runtime, layout, combat, baking tools and HUD were built for this prototype with
Pygame-CE and Pygbag.
