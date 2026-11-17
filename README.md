# ASHEN VEIL — Ashen Village

A first-playable, top-down dark fantasy **hack & slash** village built with
**Python + Pygame-CE**, packaged for the browser with **Pygbag**. This slice is
about atmosphere, exploration and fast multi-enemy swordplay: Fallen Knights
roam the dying village and the player chains a five-hit combo, dodge-rolls
through swings and dash-attacks across the plaza. There is no quest, inventory
or boss system yet.

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
  friction and unrestricted sprinting. Running is never stamina-limited.
- **Five-hit sword combo** — `LMB` chains horizontal → reverse → diagonal →
  heavy spin → finisher for 20 / 22 / 25 / 30 / 45 damage. Inputs are buffered
  from the first frames of a swing, each link has its own timing, reach,
  knockback and slash arc, and the chain auto-resets after 2.2 s idle.
- **Dash attack** — `E` or right mouse bursts forward with a wide, bright
  sword strike (26 damage, 0.85 s cooldown). Movement uses the normal collision
  solver, so the dash slides to a stop at walls instead of teleporting.
- **Dodge roll** — `Space` rolls in the input direction (or facing), grants
  i-frames, moves at 470 px/s and has a 0.30 s cooldown. No stamina cost.
- **Multi-enemy combat** — one swing damages every knight inside its hitbox
  exactly once, with independent reactions. Heavy links use a radial hitbox.
  Knockback follows the sword's travel direction, and a light separation pass
  keeps the pack from stacking into one silhouette.
- **Critical hits** — 18% chance for ×1.7 damage and ×1.25 knockback, with
  gold sparks, a bigger damage number and a `CRITICAL` HUD flash.
- **Fallen Knight enemies** — a purpose-built 64×64 pixel-art undead sentinel
  (idle, walk, attack, hurt, death) with delta-time IDLE/PATROL/CHASE/ATTACK/
  HURT/DEATH AI, 230 px detection, 44 px attack range, 12 damage, a readable
  wind-up ring, collision sliding, obstacle avoidance and leashing. Seven
  knights spawn in the village. A single attack token means only one knight
  winds up at a time, so damage is never an unavoidable simultaneous burst.
- **Combat feedback** — six pre-rendered purple slash styles, radial novas on
  the spin and finisher, impact sparks, floating damage numbers, enemy hit
  flash, attack-direction knockback, 35–105 ms hit stop, light camera shake and
  a stronger finisher flash.
- **Pixel-aware collision** with sliding along walls, houses, gates, trees and
  props, plus solid world borders.
- **Smooth clamped camera** with subtle look-ahead, Y-sorted props and player,
  and nearest-neighbour scaling to the window.
- **Baked ground detail** — seamless grass/dirt/cobble samples, warped path and
  plaza masks, scattered detail, static prop shadows and baked lantern light
  pools, so the runtime only draws a small animated flame bloom.
- **Night atmosphere** — moon haze, drifting fog, ash, lantern motes, footstep
  dust, a cold player aura and a vignette.
- **Custom pixel HUD** — vitality bar, a DASH cooldown gauge, level badge,
  “ASHEN VEIL” title treatment, controls hint, an intro card, a combo counter
  with five chain pips, a critical-hit flash, floating enemy health bars and
  the engaged-knight bar. Cached surfaces; a “YOU DIED” veil with restart.
- **Browser build** via Pygbag with an async-compatible game loop.

## Controls

| Input | Action |
| --- | --- |
| `WASD` / arrow keys | Move (8 directions) |
| `Left mouse button` | Attack — press again during a swing to chain the five-hit combo |
| `Right mouse button` / `E` | Dash attack (forward burst + wide strike) |
| `Space` | Dodge roll (invulnerability frames) |
| `Shift` | Run (unrestricted) |
| `R` / click | Rise again after death |
| `H` | Toggle control hints |
| `F1` / `F3` | Toggle debug overlay |
| `F11` | Toggle fullscreen (desktop) |
| `Esc` | Quit (desktop) |

The help bar hides itself after a short while; press `H` to bring it back. The
browser builds capture the mouse on the canvas, so click once to focus before
using keyboard controls. The dash key is configurable via
`DASH_KEY_NAME` in `scripts/combat_config.py`.

## Combat tuning

All values live in `scripts/combat_config.py`.

| Combo link | Damage | Knockback | Reach / width | Startup | Active | Recovery |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| 1 horizontal | 20 | 70 | 58 / 54 | 0.055 s | 0.095 s | 0.070 s |
| 2 reverse | 22 | 80 | 60 / 56 | 0.055 s | 0.095 s | 0.070 s |
| 3 diagonal | 25 | 95 | 64 / 60 | 0.065 s | 0.105 s | 0.085 s |
| 4 spin (radial) | 30 | 180 | 84 radius | 0.085 s | 0.135 s | 0.110 s |
| 5 finisher (radial) | 45 | 280 | 94 radius | 0.115 s | 0.165 s | 0.170 s |

- Combo window 0.50 s after a swing; buffering opens at 0.045 s; counter
  resets after 2.2 s without a hit.
- Dodge: 470 px/s, 0.22 s, 0.16 s i-frames, 0.30 s cooldown, no stamina.
- Dash attack: 640 px/s burst, 0.20 s, 26 damage, 0.85 s cooldown, 0.08 s
  i-frames.
- Criticals: 18% chance, ×1.7 damage, ×1.25 knockback.
- Hit stop: 35 ms normal, 70 ms heavy, 105 ms finisher.
- Fallen Knight: 100 HP, 12 damage, 1.35 s attack cooldown, 0.40 s wind-up,
  0.80 s total swing. One knight holds the attack token at a time.
- Player: 100 HP, 0.75 s post-hit invulnerability.

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
  player.py                 Movement, footsteps, combat integration, 2x sprite
  player_combat.py          Five-hit combo/dash/dodge/hurt/death state machine
  combat_config.py          All combat tuning (damage, timings, reach, knockback)
  health.py                 Clamped health pool shared by player and enemies
  hitbox.py                 Arc and radial attack volumes with knock direction
  enemy.py                  Fallen Knight entity: animation, health, damage, drawing
  enemy_ai.py               Delta-time IDLE/PATROL/CHASE/ATTACK/HURT/DEATH AI
  combat_manager.py         Hits, crits, hit stop, attack token, separation, feedback
  effects.py                Slash arcs, novas, particles, damage numbers, flashes
  combat_ui.py              Combo counter, crit flash, enemy bars and the death veil
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
  test_combat.py            Headless functional checks (110 assertions)
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
- Slash arcs are drawn once into cached surfaces (6 styles × 4 facings);
  particles and damage numbers use cached dots and glyph surfaces and are
  capped at 200 particles / 16 numbers / 8 slashes / 3 novas.
- Scene effects are plain lists pruned every frame; no full-screen surface is
  allocated during combat. Radial novas are two cheap circle outlines.
- Hit stop freezes simulation only (`CombatManager.consume_hit_stop`), while
  the HUD, input and intro timing keep real delta time, so responsiveness is
  preserved.
- Enemy animation sheets are shared between all Fallen Knights; each knight
  only stores its own animator indices and timers.
- `tools/bench.py` on the development machine reports roughly 5–6 ms for a full
  1280×720 draw, both exploring and in a busy combat frame with five knights,
  a chained combo, sparks, damage numbers and combo/enemy bars (world ≈ 2 ms,
  atmosphere ≈ 2–3 ms, effects ≈ 0.75 ms, HUD ≈ 0.7 ms) with the dummy video
  driver. Browser timing will differ.

## Verification status

`python tools/test_combat.py` runs 110 headless assertions covering:

- walking, running without stamina, the IDLE/WALK/RUN state surface and
  legacy collision/camera clamping;
- the full five-hit combo (20/22/25/30/45), one-link-at-a-time buffering,
  rapid-input safety, combo auto-reset, heavy camera shake, novas and hit stop;
- multi-enemy hits: one swing damages three knights exactly once each, the
  radial spin/finisher hit the whole ring, and knockback follows the attack
  direction rather than radiating from the player;
- guaranteed critical hits (34 damage on the first link), crit HUD flash and
  crit damage numbers;
- dodge distance, i-frames, cooldown and the removal of stamina gating;
- dash burst, front damage, cooldown and wall stops that never leave the player
  inside geometry;
- player damage, post-hit invulnerability, death, movement lock and restart
  with all seven knights;
- knight detection, chase, 12 damage, forward attack arc missing a player who
  moves behind, patrol radius, hurt/knockback recovery, death and removal;
- one attack token across a three-knight pack (no simultaneous wind-ups) and
  the separation pass;
- wall obstruction for both the sword (no cutting through stone) and knight
  movement (never inside a house footprint);
- synthetic mouse/keyboard events (LMB, RMB, E, Space), six awaited frames of
  the async loop and full-resolution frames with HUD, combo readout, enemy
  bars, debug overlays and the death veil.

Also verified:

- Landmark and combat views render and are saved in `screenshots/`
  (`combat_impact.png`, `combat_finisher.png`, `combat_dash.png`,
  `combat_kill.png`, `combat_death.png`).
- `python -m pygbag --build --title "ASHEN VEIL" .` produces a browser build in
  `build/web/`; serving `build/web/` returns the page and APK with HTTP 200.
- A live interactive browser session (real input, audio, canvas display) still
  needs a manual check in your own browser; this environment cannot verify
  actual in-browser behaviour. The async loop, event handlers and rendering
  paths are exercised headlessly under the SDL dummy driver.

## Missing / reused animation assets

- The player sheet has no separate attack variants for the five combo links or
  the dash, so every swing reuses the same six-frame directional `attack` row
  with different timings, damage, reach, knockback and feedback. Directional
  `dodge`, `hurt` and a single `death` row already exist and are reused as-is.
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
