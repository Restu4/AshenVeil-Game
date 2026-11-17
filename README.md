# ASHEN VEIL — Ashen Village

A first-playable, top-down dark fantasy **hack & slash** village built with
**Python + Pygame-CE**, packaged for the browser with **Pygbag**. This slice is
about atmosphere, exploration and fast multi-enemy swordplay: Fallen Knights,
Void Stalkers and Ashen Cultists roam the dying village while the player chains
a five-hit combo, dodge-rolls through swings and dash-attacks across the plaza.
On top of the swordplay sits **VOID ESSENCE**, a dark-magic system with a
regenerating energy pool and four skills. There is no quest, inventory or boss
system yet.

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
- **Dash attack** — `C` or right mouse bursts forward with a wide, bright
  sword strike (26 damage, 0.85 s cooldown). Movement uses the normal collision
  solver, so the dash slides to a stop at walls instead of teleporting.
- **Dodge roll** — `Space` rolls in the input direction (or facing), grants
  i-frames, moves at 470 px/s and has a 0.30 s cooldown. No stamina cost.
- **VOID ESSENCE dark magic** — a separate 100-point energy pool that starts
  full, regenerates 8/s and gains +8 on every enemy kill (sword or magic).
  Four skills share the existing combat pipeline:
  - `Q` **VOID BURST** — instant purple detonation, 35 damage in a 110 px
    radius, radial knockback, 20 energy, 3 s cooldown.
  - `E` **SHADOW STEP** — 0.25 s Void dash with purple afterimages, i-frames
    and normal collision, 15 energy, 2 s cooldown.
  - `R` **VOID SLASH** — a travelling crescent that hits each enemy once,
    45 damage, 320 px range, 25 energy, 5 s cooldown.
  - `F` **ECLIPSE** — a 0.55 s wind-up that darkens the screen, then a
    220 px expanding detonation for 100 damage with heavy knockback and camera
    shake, 60 energy, 18 s cooldown.
- **Void Essence UI** — the four skills are compact 42 px icons in the
  bottom-right strip, with key labels, costs, shrinking cooldown overlays, a
  dimmed unaffordable state and a charging ring for Eclipse.
- **Multi-enemy combat** — one swing damages every enemy inside its hitbox
  exactly once, with independent reactions. Heavy links use a radial hitbox.
  Knockback follows the sword's travel direction, and a light separation pass
  keeps the pack from stacking into one silhouette.
- **Critical hits** — 18% chance for ×1.7 damage and ×1.25 knockback, with
  gold sparks, a bigger damage number and a `CRITICAL` HUD flash.
- **Three enemy archetypes** — one entity and one AI state machine, with every
  gameplay number in `scripts/enemy_config.py`:
  - **FALLEN KNIGHT** — 100 HP, 12 damage, 1.35 s cooldown and a deliberately
    long 0.40 s wind-up. Reuses the original generated 64×64 undead sentinel
    spritesheet.
  - **VOID STALKER** — 65 HP, the fastest archetype (152 px/s) with quick
    0.22 s telegraphed claws for 7 damage and a 0.82 s cooldown.
  - **ASHEN CULTIST** — 75 HP, holds a ~205 px preferred band, retreats when
    the player closes inside 140 px and fires a visible purple bolt
    (10 damage, 250 px/s, 470 px range).
  - Stalker and cultist art are procedural 64×64 pixel-art frames cached and
    shared between instances (`scripts/enemy_art.py`); enemies are never drawn
    as plain rectangles.
- **State-based enemy AI** — `IDLE`/`PATROL` → `CHASE` → `ATTACK_WINDUP` →
  `ATTACK` → `RECOVERY`, plus `RETREAT` (ranged), `HURT` and `DEATH`.
  Detection, leash, short-term memory, light separation, collision sliding,
  Y-sorting, a single attack token and line-of-sight checks keep fights fair:
  no melee swing or bolt passes through a wall and a committed wind-up can be
  dodged or rolled behind.
- **Controlled spawning** — a small opening group of one knight, one stalker
  and one cultist; validated spawn points that never overlap solids, the player
  or another body; a configurable active cap of 6 and a finite total cap of 9,
  so the village eventually runs dry instead of spawning forever.
- **Combat feedback** — six pre-rendered purple slash styles, radial novas on
  the spin and finisher, impact sparks, enemy swipe arcs, purple projectile
  pops, floating 2×/3× damage numbers, clear enemy hit flash, attack-direction
  knockback, 35–105 ms hit stop, light camera shake and a stronger finisher
  flash. Heavier links produce stronger shake and hit stop than quick links.
- **Pixel-aware collision** with sliding along walls, houses, gates, trees and
  props, plus solid world borders.
- **Smooth clamped camera** with subtle look-ahead, Y-sorted props and player,
  and nearest-neighbour scaling to the window.
- **Baked ground detail** — seamless grass/dirt/cobble samples, warped path and
  plaza masks, scattered detail, static prop shadows and baked lantern light
  pools, so the runtime only draws a small animated flame bloom.
- **Night atmosphere** — moon haze, drifting fog, ash, lantern motes, footstep
  dust, a cold player aura and a vignette.
- **Compact dark-fantasy HUD** — unobtrusive top-left vitality bar
  (`20,20` · 204×13 px) in muted crimson, a dark-violet Void bar directly
  below (`20,44` · 172×9 px), a 120×3 dash gauge at `20,57`, four 42 px skill
  icons in a 186 px bottom-right strip (`1074,658`), a small 120×52 combo
  readout at `1140,16`, a 300×46 engaged-target plate top-centre, floating
  48×4 enemy bars and a 438×32 control hint. Cached surfaces only; the fixed
  1280×720 canvas is nearest-neighbour letterboxed on resize. A “YOU DIED”
  veil still offers restart.
- **Browser build** via Pygbag with an async-compatible game loop.

## Controls

| Input | Action |
| --- | --- |
| `WASD` / arrow keys | Move (8 directions) |
| `Left mouse button` | Attack — press again during a swing to chain the five-hit combo |
| `Right mouse button` / `C` | Dash attack (forward burst + wide strike) |
| `Space` | Dodge roll (invulnerability frames) |
| `Q` | VOID BURST — radial dark explosion |
| `E` | SHADOW STEP — Void dash with i-frames |
| `R` | VOID SLASH — travelling purple crescent |
| `F` | ECLIPSE — wind-up ultimate |
| `Shift` | Run (unrestricted) |
| `Enter` / `Space` / click | Rise again after death |
| `H` | Toggle control hints |
| `F1` / `F3` | Toggle debug overlay |
| `F11` | Toggle fullscreen (desktop) |
| `Esc` | Quit (desktop) |

The help bar hides itself after a short while; press `H` to bring it back. The
browser builds capture the mouse on the canvas, so click once to focus before
using keyboard controls. After death only `Enter`, `Space` or a click restarts
the run, so `R` is free for VOID SLASH. Skill keys are bound explicitly to
`Q`/`E`/`R`/`F`, and the dash key is guarded so it can never alias a skill:
one keypress casts at most one ability. The dash key is configurable via
`DASH_KEY_NAME` in `scripts/combat_config.py`; skill keys, costs and cooldowns
live in `scripts/skill_config.py`; enemy stats, spawn caps and projectile
tuning live in `scripts/enemy_config.py`.

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
### Enemy archetypes

Every value lives in `scripts/enemy_config.py`; the AI reads them from the
enemy instance and hard-codes no archetype.

| Enemy | HP | Damage | Cooldown | Wind-up | Active | Recovery | Chase | Detection |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| FALLEN KNIGHT | 100 | 12 melee | 1.35 s | 0.40 s | 0.12 s | 0.28 s | 96 px/s | 230 px |
| VOID STALKER | 65 | 7 melee | 0.82 s | 0.22 s | 0.08 s | 0.16 s | 152 px/s | 320 px |
| ASHEN CULTIST | 75 | 10 bolt | 2.15 s | 0.55 s | 0.10 s | 0.30 s | 78 px/s | 400 px |

- Cultist: preferred distance 205 px, retreats inside 140 px at 132 px/s for
  0.85 s, bolt speed 250 px/s, damage 10, radius 7 px, range 470 px. At most
  12 enemy projectiles exist at once; each lives 3 s and dies on a wall.
- Spawning: opening group 3, active cap 6, total cap 9 (including the opening
  group), reinforcement interval 9 s, minimum distance to the player 250 px
  for the opening group / 420 px for reinforcements, 86 px between enemies and
  ±22 px jitter around the 14 validated spawn points.
- Detection, memory (3.6 s knight / 4.0 s stalker / 4.6 s cultist), leash
  (700 / 900 / 820 px) and separation (30 px) are per-archetype configurable.
- One enemy holds the attack token at a time (range ×1.7), so damage is never
  an unavoidable simultaneous burst.
- Player: 100 HP, 0.75 s post-hit invulnerability.

## Void Essence tuning

All values live in `scripts/skill_config.py`.

| Resource | Value |
| --- | --- |
| Maximum energy | 100 |
| Starting energy | 100 |
| Regeneration | 8 / second (delta time) |
| Kill reward | +8 (sword or magic kills) |

| Skill | Key | Cost | Cooldown | Damage | Radius / range | Knockback |
| --- | --- | ---: | ---: | ---: | --- | ---: |
| VOID BURST | `Q` | 20 | 3.0 s | 35 | 110 px radius | 165 |
| SHADOW STEP | `E` | 15 | 2.0 s | — | 0.25 s dash / 690 px/s | — |
| VOID SLASH | `R` | 25 | 5.0 s | 45 | 320 px, 560 px/s wave | 215 |
| ECLIPSE | `F` | 60 | 18.0 s | 100 | 220 px radius, 0.55 s wind-up | 360 |

- Energy regeneration, spending and cooldowns are all delta-time based and
  clamped to `0..100`; a skill can never be cast below its cost.
- Magic damage uses the same `CombatManager.damage_enemy` / `damage_area`
  pipeline as sword hits, so damage numbers, hit stop, knockback, enemy health
  bars, death dissolves and kill rewards are identical.
- Each cast carries its own hit set: an enemy is damaged at most once per
  burst, wave or Eclipse, even while overlapping for several frames.
- Magic cannot damage the player. Shadow Step grants 0.22 s of i-frames, moves
  through the normal collision solver and stops at walls.
- Eclipse is a committed cast: it cannot begin again while a previous wind-up
  is still gathering, and it applies its cooldown immediately.
- Presentation limits live at the bottom of the config: 240 skill particles,
  10 rings, 24 afterimages and 4 travelling waves.

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
  player_combat.py          Five-hit combo/dash/dodge/shadow-step/cast state machine
  combat_config.py          All combat tuning (damage, timings, reach, knockback)
  skill_config.py           All Void Essence tuning (energy, costs, damage, cooldowns)
  void_energy.py            Clamped delta-time energy pool with kill rewards
  skill_manager.py          Skill orchestration, energy, waves, Eclipse, kill hook
  skills/                   Per-skill casts (base, burst, shadow step, slash, eclipse)
  skill_effects.py          Capped purple particles, rings, afterimages, dark overlay
  skill_hud.py              Bottom-right four-slot skill strip and cooldowns
  health.py                 Clamped health pool shared by player and enemies
  hitbox.py                 Arc and radial attack volumes with knock direction
  enemy_config.py           Archetype stats, spawn caps and projectile tuning
  enemy.py                  Generic archetype-driven enemy: flash, knockback, death
  enemy_ai.py               IDLE/CHASE/WINDUP/ATTACK/RECOVERY/RETREAT/HURT/DEATH AI
  enemy_art.py              Procedural cached pixel art for stalker and cultist
  projectile.py             Capped wall-aware enemy bolts with impact effects
  spawner.py                Validated finite spawning with active/total caps
  combat_manager.py         Hits, crits, hit stop, attack token, separation, spawns
  effects.py                Slashes, novas, particles, swipe arcs, damage numbers
  combat_ui.py              Combo counter, crit flash, enemy bars and the death veil
  collision.py              Prop footprints, spatial hash, sliding movement
  camera.py                 Smooth clamped camera and world→screen conversion
  village_layout.py         Canonical roads, patches, props, lights, spawn
  world.py                  Prop instances, culling, Y-sorting, ground blit
  atmosphere.py             Night overlay, glows, fog, ash, motes, dust, vignette
  hud.py                    Compact HP/Void/dash bars, help and intro
  pixel_font.py             5×7 bitmap font and text renderer

tools/                      Development only (not shipped to the web build)
  slice_assets.py           Re-cuts the source atlas into assets/sliced/
  bake_ground.py            Rebakes assets/generated/ground.png
  preview.py                Headless landmark + combat + skill screenshots
  bench.py                  Headless draw benchmark (exploration/combat/skills)
  test_combat.py            Headless functional checks (211 assertions)
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
- HUD panels, help and intro are pre-rendered once.
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
- Enemy art is shared: the knight spritesheet is loaded once, and the
  stalker/cultist procedural frames live in one module-level cache reused by
  every instance; each enemy only stores its own animator indices and timers.
- Skill visuals reuse one cached full-screen dark surface, cached dot sprites
  and plain capped lists; the wave and Eclipse sigil are cheap arc/circle
  draws rather than new per-frame surfaces.
- `tools/bench.py` on the development machine reports roughly 6–8 ms for a full
  1280×720 draw: exploration ≈ 6.2 ms, three-archetype combat ≈ 7.7 ms and a
  frame with all four skills firing ≈ 7.2 ms (world ≈ 1.8–2.1 ms, atmosphere
  ≈ 2.6–2.8 ms, skill effects ≈ 0.3 ms, combat effects ≈ 0.3–0.8 ms, HUD
  ≈ 1.2–1.6 ms) with the dummy video driver. Browser timing will differ.
- Enemy frames are shared caches: the knight spritesheet is loaded once and the
  stalker/cultist procedural surfaces are generated once per animation frame,
  then reused by every instance.

## Phase 4 verification

`python tools/test_combat.py` runs **211** headless assertions. Its twelve
numbered sections map directly to the acceptance areas:

1. **Movement, run, collision and camera** — walking, unrestricted running,
   the IDLE/WALK/RUN surface, house blocking and camera clamping.
2. **Five-hit combo, dodge and dash** — 20/22/25/30/45 damage, one-link-at-a-
   time buffering, rapid-input safety, auto-reset, guaranteed crits,
   multi-enemy single hits, knockback direction, dash i-frames, cooldown and
   wall stops.
3. **Enemy archetypes and configurable stats** — all three keys and HP values
   (100/65/75), speed ordering, wind-up ordering, ranged flags, cultist
   projectile damage, start-group composition, and procedural art that is
   non-empty, 64 px sourced and cache-shared.
4. **AI states** — every state constant, the explicit committed wind-up →
   attack → recovery sequence, exactly one 12-damage knight hit, a swing that
   misses a player who rolls behind it, and idle/patrol near home with no
   player nearby.
5. **HURT and DEATH** — flash timer, knockback travel, recovery, lethal hit,
   death state and removal after the fade.
6. **Ranged cultist** — retreat when crowded (the gap grows), visible wind-up,
   exactly one bolt, purple colour, 10 damage applied once, impact particles
   and the live-projectile cap.
7. **Walls** — melee through a fence refuses damage, a blocked cast creates no
   bolt (only a harmless impact), while clear plaza and stone-wall lines behave
   correctly.
8. **Feedback** — 2×/3× damage-number sizes, impact/swipe/projectile effects,
   particle caps, and heavier shake plus longer hit stop on the spin.
9. **Compact HUD and scaling** — HP 204×13, Void 172×9, dash 120×3, 42 px
   icons at `1074,658`, the 300×46 engaged plate, the 120×52 combo block, the
   438×32 hint, muted crimson/dark-violet pixels, empty-pool drain, cached
   panels, and letterboxing a 1000×1000 window to 1000×562 while keeping the
   1280×720 internal canvas.
10. **Spawner** — small start group, spawn log, 14 points > 6 active cap, no
    solid/player/enemy overlap, active cap blocks update spawning, total cap 9
    is finite, and exhausted spawning never restarts.
11. **One cast per keypress** — explicit Q/E/R/F map, dash key never aliases a
    skill, Q spends only burst (80 left), starts only the burst cooldown and
    never dashes; repeated Q during cooldown spends nothing; E/R/F each cast
    only their own ability.
12. **Pygbag** — async entry point, per-frame `await asyncio.sleep(0)`,
    emscripten detection, desktop `asyncio.run`, `pygbag.ini`, the built
    `index.html`, and an archive containing `main.py` and
    `scripts/projectile.py` with `tools/` excluded.

Also verified:

- Landmark, combat and skill views render and are saved in `screenshots/`
  (`combat_impact.png`, `combat_finisher.png`, `combat_dash.png`,
  `combat_kill.png`, `combat_death.png`, `skill_void_burst.png`,
  `skill_shadow_step.png`, `skill_void_slash.png`,
  `skill_eclipse_windup.png`, `skill_eclipse_blast.png`).
- `python tools/bench.py` completes all three scenarios and reports the
  draw-phase timings above; the skill and combat effect lists stay within
  their caps.
- `python -m compileall -q scripts main.py settings.py tools` completes without
  errors.
- `python -m pygbag --build --title "ASHEN VEIL" .` produces a browser build in
  `build/web/`; serving that directory returns `index.html`, `game.tar.gz` and
  `game.apk` with HTTP 200 (archive ≈ 7.7 MB).
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
- The Void Stalker and Ashen Cultist have no source sheets. Their idle, walk,
  attack, hurt and death frames are drawn procedurally into 64×64 surfaces by
  `scripts/enemy_art.py`, using the same chunky pixel style, and cached. They
  have one art set per archetype rather than per-direction attack variants.
- No new frames were invented for the player. The knight sheet is generated
  from code in `tools/generate_fallen_knight.py`, not reused player art.
- The project currently has **no audio system or sound assets**. Enemy attacks,
  projectiles and the Void skills therefore have distinct visuals, timings,
  camera shake and hit stop, but no sound effects were added; adding audio
  would require a new mixer module and assets, which is outside this phase.

## Remaining issues

- In-browser behaviour (real input focus, audio, actual frame pacing) still
  needs a manual session in a real browser; the headless suite cannot prove it.
- The cultist's bolt is a simple circle with a glow, not a fully animated
  sprite, and all three archetypes share the same eight-direction facing model.
- Enemy art is intentionally limited to one procedural set per new archetype;
  there are no per-direction attack frames for the stalker or cultist.
- Spawn points are hand-authored (14 validated locations); a runtime navigation
  mesh or dynamic spawn placement is out of scope for this phase.
- There is still no inventory, quest, new map or boss encounter, by design.

## Credits

Character spritesheet, environment concept atlas and ASHEN VEIL art direction
come from the project’s included original artwork. The Fallen Knight sheet,
runtime, layout, combat, baking tools and HUD were built for this prototype with
Pygame-CE and Pygbag.
