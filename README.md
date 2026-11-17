# ASHEN VEIL — Ashen Village

A first-playable, top-down dark fantasy **hack & slash** built with
**Python + Pygame-CE**, packaged for the browser with **Pygbag**. This slice is
about atmosphere, exploration and fast multi-enemy swordplay: Fallen Knights,
Void Stalkers and Ashen Cultists roam the dying village while the player chains
a five-hit combo, dodge-rolls through swings and dash-attacks across the plaza.
On top of the swordplay sits **VOID ESSENCE**, a dark-magic system with a
regenerating energy pool and four skills.

**Phase 5** completes the first level. A title screen and atmospheric level
select lead into **Level 01 · ASHEN VILLAGE**, a four-stage descent from the
abandoned village, along the corrupted western path and through the forgotten
shrine, into a sealed arena where **THE HOLLOW GUARDIAN** waits. Beating the
guardian opens a victory screen and unlocks Level 02 in a small JSON profile.
Levels 02–04 are fully authored selection entries with previews, lore and lock
states, but their maps are deliberately not forged yet.

**Phase 7** adds character progression on top of the Phase 6 inventory,
equipment and loot layer: EXP and levels, four attributes, a three-branch Void
skill tree, add-on save fields and two full-screen character overlays. The
original combat, enemies, boss, stage flow and Q/E/R/F bindings stay intact.

The playable character uses the original ASHEN VEIL spritesheet (hooded figure,
black face, single white eye, large back sword, cape and sandals). The village
reuses artwork from the original environment concept atlas, sliced into named
sprites — the irregular atlas is never stretched or used as a flat backdrop.

## Features

- **Title screen and level select** — a dark-fantasy title over the living
  village, then four large atmospheric cards with baked preview dioramas, level
  number and name, description, boss lore, completion/lock status and a single
  Play action. Keyboard, number keys and mouse all work; locked cards can be
  inspected but never entered. Levels 02–04 advertise **MAP NOT YET FORGED**.
- **Four-stage Level 01** — the stage script drives the run without taking over
  combat:
  1. **ABANDONED VILLAGE** — cut down the opening trio.
  2. **CORRUPTED PATH** — break the 320 HP **Corrupted Warden** and its two
     escorts on the western road.
  3. **FORGOTTEN SHRINE** — walk into the pulsing veil gate; a short fade
     carries the player into the sealed arena.
  4. **BOSS ARENA** — defeat **THE HOLLOW GUARDIAN**. No retreat.
- **THE HOLLOW GUARDIAN** — a 1200 HP three-phase boss with purple chest
  cracks, a crimson core, an oversized greatsword and a 314×314 px silhouette
  (over three times a knight's frame). Every attack has a named wind-up,
  growing floor telegraph and committed recovery: **SWEEP**, **GROUND SLAM**,
  **TWIN SWEEP**, **VOID WAVE**, **VEIL MARK** and the **VEIL COLLAPSE**
  signature. See [The Hollow Guardian](#the-hollow-guardian).
- **Boss and stage HUDs** — a 620×64 top-centre guardian bar with the name
  above, phase readout, three phase diamonds, 70 %/35 % threshold notches and
  a crimson danger band; it exists only during the encounter and disappears the
  instant the guardian dies. A compact 300×42 stage panel sits under the
  vitality bars with stage number, objective, remaining foes / gate distance,
  four pips and a short stage banner. A 172×3 EXP strip at `20,63` shows the
  current level's progress without moving any earlier bar.
- **Persistent progression** — completion, boss kill and stages cleared are
  written to `save/progress.json` (and mirrored to browser `localStorage`). A
  completed Level 01 permanently unlocks Level 02 in the select screen; player
  level is preserved independently across runs. Missing, truncated or
  wrong-shaped saves fall back to a clean profile without crashing.
- **Loot, inventory and equipment** — enemies and bosses drop rolled gear into
  the world (`G` to pick up); `I` opens the seven-slot satchel with rarity
  borders, item details, consumables, gold and level-gated equipment. Equipped
  bonuses feed the real attack, defense, speed, critical and resource numbers.
- **Character progression** — one `ExpManager` owns level 1–30, EXP, four
  attributes, points and per-enemy kill markers. `P` opens **THE WANDERER**
  sheet (real sprite portrait, EXP bar, attribute allocation and derived
  stats); `T` opens the three-branch **VOID SKILL TREE**. Every reward, grant,
  attribute scaling, node effect and level-up value is configurable in
  `scripts/progression_config.py` and `scripts/skill_tree_config.py`.
- **Victory flow** — the guardian's death animation plays, every attack and
  hazard stops, and after a short beat the victory screen offers **CONTINUE**
  (preselects the newly unlocked Level 02) and **RETURN TO LEVEL SELECT**
  (preselects the completed Level 01). Nothing teleports automatically.
- **Arena framing** — the shrine sits against the world's north edge, so the
  camera lifts 300 px while the guardian is active; the whole boss clears the
  HUD instead of being clipped off-screen.
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
  48×4 enemy bars and a 438×32 control hint. Level 01 adds a 300×42 stage
  objective panel at `20,66` and the 620×64 guardian bar at `330,8`; the
  generic engaged plate is suppressed for the boss so the two never stack.
  Cached surfaces only; the fixed 1280×720 canvas is nearest-neighbour
  letterboxed on resize. A “YOU DIED” veil still offers restart.
- **Browser build** via Pygbag with an async-compatible game loop.

## Controls

| Input | Action |
| --- | --- |
| `↑` / `↓` or `W` / `S`, mouse | Move the title-menu highlight |
| `Enter` / `Space` / click | Confirm a menu item, start a level, or choose a victory action |
| `←` / `→` or `A` / `D` / `1`–`4` | Choose a level card |
| `Esc` | Back from level select, return from victory, or quit (desktop) |
| `WASD` / arrow keys | Move (8 directions) |
| `Left mouse button` | Attack — press again during a swing to chain the five-hit combo |
| `Right mouse button` / `C` | Dash attack (forward burst + wide strike) |
| `Space` | Dodge roll (invulnerability frames) |
| `Q` | VOID BURST — radial dark explosion |
| `E` | SHADOW STEP — Void dash with i-frames |
| `R` | VOID SLASH — travelling purple crescent |
| `F` | ECLIPSE — wind-up ultimate |
| `Shift` | Run (unrestricted) |
| `G` | Pick up a nearby world drop |
| `I` | Open / close the inventory and equipment screen |
| `P` | Open / close the character sheet and spend attribute points |
| `T` | Open / close the Void skill tree and unlock nodes |
| `Enter` / `Space` / click | Rise again after death |
| `H` | Toggle control hints |
| `F1` / `F3` | Toggle debug overlay |
| `F11` | Toggle fullscreen (desktop) |

The help bar hides itself after a short while; press `H` to bring it back. The
browser builds capture the mouse on the canvas, so click once to focus before
using keyboard controls. After death only `Enter`, `Space` or a click restarts
the run, so `R` is free for VOID SLASH. Skill keys are bound explicitly to
`Q`/`E`/`R`/`F`, and the dash key is guarded so it can never alias a skill:
one keypress casts at most one ability. The dash key is configurable via
`DASH_KEY_NAME` in `scripts/combat_config.py`; skill keys, costs and cooldowns
live in `scripts/skill_config.py`; enemy stats, spawn caps and projectile
tuning live in `scripts/enemy_config.py`.

On the title screen `BEGIN DESCENT` starts Level 01 and `LEVEL SELECT` opens
the four cards. Level select responds to arrows, `1`–`4`, mouse hover/click and
`Enter`; a sealed card explains what to clear. At the victory screen use
left/right (or Tab) to switch between `CONTINUE` and `RETURN TO LEVEL SELECT`
and `Enter` to confirm. Restarting after death always returns to Level 01
stage 1 at the village spawn; progression is never erased.

## Character progression

A new profile starts at **level 1** and caps at **level 30**. The EXP needed to
advance from level `L` to `L+1` is `round(60 * 1.13 ** (L - 1))` — 60 at level
1, 68 at level 2, 77 at level 3. Kill rewards are configurable: regular 20,
strong (Fallen Knight) 40, elite (Corrupted Warden / `ELITE` subtitle) 100 and
boss 500. Each defeated enemy is marked once as `<level>:<id>` (bosses use
`<level>:boss`), so reloading or re-entering a level cannot farm the same kill.
Future quests can call `ExpManager.award_quest_exp()`.

Every level grants **3 attribute points**; every two levels grant **1 skill
point**. Reaching level 30 therefore yields 87 attribute and 14 skill points.
Attributes are real simulation values: **STR** +2 attack, **VIT** +12 maximum
HP, **AGI** +2 speed and +1% critical chance, **INT** +4 maximum Void and +2%
Void skill power per rank (maximum rank 10). The sheet's *Reset Points* button
refunds allocations with a confirmation click.

The skill tree has twelve one-point nodes in three branches: **Void Offense**
(burst/slash damage, critical damage, elite damage), **Shadow Mobility**
(Shadow Step cooldown and distance, dodge recovery and post-dodge speed) and
**Eclipse Mastery** (Eclipse damage and radius, Void regeneration, reduced skill
cost). Nodes have level and prerequisite gates and only change values used by
the existing `Q`/`E`/`R`/`F` skills; no new active ability is created. Purchased
nodes, attributes, points, EXP and kill markers are added to the same JSON
profile with additive validation, so old saves and the browser `localStorage`
mirror (`ashen_veil_progress`) keep working.

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

## Level 01 and progression

| Stage | Objective | Flow |
| --- | --- | --- |
| 1 ABANDONED VILLAGE | CUT DOWN THE RISEN DEAD | the authored opening trio (knight, stalker, cultist) |
| 2 CORRUPTED PATH | BREAK THE CORRUPTED WARDEN | 320 HP elite + one stalker and one cultist escort on the west road |
| 3 FORGOTTEN SHRINE | STEP INTO THE VEIL GATE | walk into the pulsing 54 px gate marker |
| 4 BOSS ARENA | DEFEAT THE HOLLOW GUARDIAN | a 0.42 s veil fade into the sealed shrine; no retreat |

- The stage script disables the endless reinforcement trickle, so every stage
  group is authored and finite. Clearing a group records the stage, shows a
  stage banner and spawns the next group; stage 3 waits for the gate; stage 4
  starts the boss encounter.
- The Corrupted Warden is an elite variant of the Fallen Knight (same AI and
  art, 320 HP / 22 damage / 116 px/s), not a fourth archetype.
- Stage 1→2 and 2→3 transitions preserve the same player, skills and effects;
  only the enemy group changes. Entering the gate is the only way into the
  arena.
- The arena floor is a runtime-baked ruined-shrine overlay (cold flagstones,
  purple seal, blood) laid over the world's north-east corner. Village props
  inside the rectangle are filtered out and replaced with the authored shrine
  set; four continuous collision solids seal the shell. Player and boss are
  also clamped to their own arena bounds so knockback and dashes cannot escape.
- Levels are a strict chain: Level 01 is always open, completing it unlocks
  Level 02, and so on. Levels 02–04 have no maps yet; the select screen shows
  their preview, boss lore, **SEALED**/**UNLOCKED** status and **MAP NOT YET
  FORGED** instead of starting an unfinished level.
- A completed level can be replayed from the select screen. Replaying starts at
  stage 1 with the opening trio and never clears the saved completion.

### Save location and shape

- Desktop: `save/progress.json` next to the game. Override the path with the
  `ASHEN_VEIL_SAVE` environment variable (used by the test suite and preview
  tools so they never touch a real profile).
- Browser: the same JSON is also written to `window.localStorage` under
  `ashen_veil_progress`, so a refresh keeps the unlock even if the virtual
  filesystem resets.
- The profile is intentionally tiny and versioned:

```json
{
  "version": 1,
  "levels": {
    "01": {"completed": true, "boss_defeated": true, "stages_cleared": 4}
  },
  "player": {"level": 7}
}
```

- Loading canonicalises every field: a missing file, empty file, truncated
  JSON, wrong root type, junk level entry, negative stage count or out-of-range
  player level all fall back to safe values. Writes are atomic (temporary file
  then replace) and return a boolean; the victory screen reports a failed save
  instead of pretending it succeeded.

## The Hollow Guardian

The guardian duck-types the enemy contract (`take_damage`, `health`, `alive`,
`removed`, `draw`, `update`) and is appended to the normal combat list, so
`CombatManager` remains the single damage authority. Its art is procedural,
cached per `(action, frame, facing)` and drawn at 2.8× from a 112 px source
frame, giving a 314×314 px silhouette with a 269 px foot line.

| Stat | Value |
| --- | --- |
| Health | 1200 |
| Body half extents | 34 × 22 px (regular knight 13 × 9) |
| Speed | 62 / 78 / 92 px/s by phase (regular knight 96, always slower) |
| Melee reach | 178 px base, ×1.06 / ×1.12 in phases 2 / 3 |
| Arena bounds | `2356,252 – 2920,676`; player `2336,232 – 2940,692` |
| Phase thresholds | 70 % and 35 % of maximum health |

| Phase | Name | Behaviour |
| --- | --- | --- |
| 1 | AWAKENING | slow pursuit; only SWEEP and GROUND SLAM; long recovery pauses |
| 2 | CORRUPTION | faster pursuit; adds TWIN SWEEP, VOID WAVE and VEIL MARK; 0.90× wind-ups, 0.86× recovery |
| 3 | LAST RESOLVE | most aggressive; 0.78× wind-ups, 0.70× recovery, +30 % damage, +12 % reach; VEIL COLLAPSE whenever its 10 s timer is ready |

| Attack | Warning | Base wind-up | Active | Recovery | Base damage | Shape |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| SWEEP | SWEEP | 0.86 s | 0.16 s | 0.66 s | 20 | 178 px, 112° sector |
| GROUND SLAM | GROUND SLAM | 1.06 s | 0.20 s | 0.90 s | 26 | 186 px radius + shock ring |
| TWIN SWEEP | TWIN SWEEP | 0.62 s | 0.15 s | 0.58 s | 17 | two 186 px, 132° sweeps, re-aimed between links |
| VOID WAVE | VOID WAVE | 0.96 s | 0.26 s | 0.82 s | 16 | 330 px expanding ring |
| VEIL MARK | VEIL MARK | 1.16 s | 0.20 s | 0.84 s | 21 | 122 px ground blast at the locked mark |
| VEIL COLLAPSE | VEIL COLLAPSE | 1.78 s | 0.30 s | 1.05 s | 34 | 168 px signature blast, heavy shake, nova |

Every attack is a committed `WINDUP → ACTIVE → RECOVERY` sequence. The wind-up
paints a growing floor telegraph (sector, disc or ring) and names the attack
above the guardian; the attack only resolves once, at the end of the wind-up.
Fairness rules:

- All damage goes through `player.take_damage`, so dodge/dash i-frames and the
  death state remain authoritative for both direct hits and ground hazards.
- Melee, slams and hazards check `collision.segment_blocked` before applying
  damage, so nothing reaches through the sealed shrine walls.
- VEIL MARK and VEIL COLLAPSE lock their target at cast time; the warning circle
  never silently follows the player.
- The guardian is clamped to its arena bounds while chasing; attacks cannot
  leave the arena.
- The phase change is a 1.15 s roar with a banner (`PHASE 2 · CORRUPTION`), so
  the escalation is readable instead of a surprise.
- Death clears every pending hazard and swipe, stops the attack state machine
  and removes the corpse after its animation.

Victory is a short beat rather than an instant cut: the corpse plays its death
animation for 2.9 s, attacks stay stopped, then the victory screen opens. It
marks Level 01 complete, records the boss kill and all four stages, writes the
profile and unlocks Level 02. The player is never teleported; both buttons lead
back to the level select (Continue focuses Level 02, Return focuses Level 01).

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
- `save/` (a developer's local progression profile is never shipped)
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
save/progress.json          Desktop progression profile (created on first victory)

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
  village_layout.py         Canonical roads, patches, props, lights, spawn, arena
  world.py                  Prop instances, culling, Y-sorting, ground blit, arena floor
  atmosphere.py             Night overlay, glows, fog, ash, motes, dust, vignette
  hud.py                    Compact HP/Void/dash bars, help, intro and stage/boss HUD
  pixel_font.py             5×7 bitmap font and text renderer
  save_manager.py           Atomic versioned JSON profile + browser localStorage mirror
  level_config.py           Four level entries, boss lore and the four Level 01 stages
  progression_manager.py    Unlock chain, completion flags and stage records
  level_manager.py          Stage flow, Warden spawns, veil gate and arena hand-off
  boss_manager.py           Encounter lifecycle, arena clamps and the victory beat
  arena_art.py              Baked ruined-shrine floor overlay for the arena
  bosses/
    hollow_guardian.py      1200 HP three-phase boss AI, telegraphs and hazards
    guardian_art.py         Procedural cached 314 px guardian art and animator
  ui/
    main_menu.py            Title screen with Begin / Level Select / Quit
    level_select.py         Four atmospheric level cards, lock states and Play
    preview_art.py          Baked village/forest/dungeon/castle dioramas
    boss_hud.py             620×64 guardian bar, phase pips and phase banner
    stage_hud.py            Compact stage/objective panel, pips and stage banner
    victory_screen.py       Victory overlay with Continue and Return buttons
    ui_common.py            Shared panels, buttons, chips and text wrapping

tools/                      Development only (not shipped to the web build)
  slice_assets.py           Re-cuts the source atlas into assets/sliced/
  bake_ground.py            Rebakes assets/generated/ground.png
  preview.py                Headless landmark, combat, skill and Phase 5 screenshots
  bench.py                  Headless draw benchmark (exploration/combat/skills)
  test_combat.py            Headless Phase 1–4 baseline (211 assertions)
  test_phase5.py            Headless Phase 5 acceptance suite (252 assertions)
  generate_fallen_knight.py Regenerates the Fallen Knight sheet

screenshots/                Landmark, combat, skill and phase5_* preview renders
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
- The arena floor is baked once into a single surface and blitted only while
  the arena is on screen. Guardian frames are cached per action/frame/facing,
  so the boss costs one scaled blit plus a handful of cached telegraphs.
- `tools/bench.py` on the development machine reports roughly 5.7–6.5 ms mean
  for a full 1280×720 draw (p95 8.7–12.3 ms): exploration ≈ 5.7 ms,
  three-archetype combat ≈ 6.5 ms and a frame with all four skills firing
  ≈ 5.7 ms (world ≈ 1.5–1.8 ms, atmosphere ≈ 2.1–2.5 ms, skill effects
  ≈ 0.0–0.2 ms, combat effects ≈ 0.0–0.5 ms, HUD ≈ 1.2–1.3 ms) with the dummy
  video driver. Browser timing will differ.
- Enemy frames are shared caches: the knight spritesheet is loaded once and the
  stalker/cultist procedural surfaces are generated once per animation frame,
  then reused by every instance.

## Verification

### Phase 5 acceptance suite

`python tools/test_phase5.py` runs **252** headless assertions in nine sections:

1. **Save manager** — missing/empty/truncated/wrong-shaped profiles fall back
   safely, canonicalisation clamps junk, roundtrip preserves completion, atomic
   writes leave no `.tmp`, and `ASHEN_VEIL_SAVE` redirects the profile.
2. **Level configuration** — exactly four ordered entries, only Level 01
   playable, four named Level 01 stages with objectives, distinct previews and
   accents, and a terminating unlock chain.
3. **Progression** — Level 01 open, Level 02 locked, stage records never
   regress, completion unlocks exactly the next entry, reload persistence,
   reset, player-level preservation and corrupt-profile safety.
4. **Level 01 flow** — opening trio, reinforcements disabled, trio → Warden and
   two escorts → veil gate → fade → arena, Warden stats and position, four-wall
   seal, filtered arena props, arena floor, player clamp and camera framing.
5. **Hollow Guardian** — 1200 HP, scale, slower speeds, phase thresholds and
   names, attack pools, warning labels, telegraph pixels, shorter later-phase
   recovery, fair reach/arc/behind checks, i-frame immunity, no damage through
   the wall, locked area marks, boss clamp, and guaranteed death cleanup.
6. **HUD** — 620×64 boss bar centred at `330,8` below the play field, no overlap
   with the stage panel, bar appears during the fight and vanishes on defeat or
   empty health, stage panel geometry and renderable text.
7. **Victory** — death animation beat, all attacks stopped, Level 01 complete,
   boss recorded, Level 02 unlocked but still not playable, save written,
   no auto-teleport/auto-continue, Continue and Return both land on the correct
   select card, replay preserves completion, restart resets to stage 1.
8. **UI screens** — menu items/navigation, all four select cards fit and render
   full art without overlap, locked Play explains the seal, four distinct
   cached dioramas, victory panel and button switching, and letterboxed mouse
   mapping.
9. **Integration hygiene** — every Phase 5 string uses glyphs the bitmap font
   owns, every new module ships, the Pygbag async loop and four-screen routing
   remain intact, and no random spawn point sits inside the arena.

### Phase 4 baseline

`python tools/test_combat.py` runs **211** headless assertions. Its twelve
numbered sections map directly to the Phase 1–4 acceptance areas:

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
    `index.html`, and an archive containing `main.py`, `scripts/projectile.py`
    and the Phase 5 save/level/boss/UI modules, with `tools/` and `save/`
    excluded.

Also verified:

- Landmark, combat, skill and Phase 5 views render and are saved in
  `screenshots/` (`combat_impact.png`, `combat_finisher.png`,
  `combat_dash.png`, `combat_kill.png`, `combat_death.png`,
  `skill_void_burst.png`, `skill_shadow_step.png`, `skill_void_slash.png`,
  `skill_eclipse_windup.png`, `skill_eclipse_blast.png`, plus
  `phase5_menu.png`, `phase5_select_locked.png`,
  `phase5_select_unlocked.png`, `phase5_stage1.png`,
  `phase5_stage2_warden.png`, `phase5_shrine_gate.png`,
  `phase5_boss_intro.png`, `phase5_boss_phase1.png`,
  `phase5_boss_phase2.png`, `phase5_boss_phase3.png`,
  `phase5_boss_death.png` and `phase5_victory.png`).
- `python tools/bench.py` completes all three scenarios and reports the
  draw-phase timings above; the skill and combat effect lists stay within
  their caps.
- `python -m compileall -q scripts main.py settings.py tools` completes without
  errors.
- `python -m pygbag --build --title "ASHEN VEIL" .` produces a 147-file browser
  build in `build/web/` without `tools/`, `screenshots/`, the source atlas or
  any local save profile; serving that directory returns `index.html`,
  `game.tar.gz` and `game.apk` with HTTP 200 (archive ≈ 7.8 MB).
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
- **THE HOLLOW GUARDIAN has no source sheet.** All twelve actions (`idle`,
  `walk`, `windup`, `sweep`, `slam`, `combo`, `wave`, `charge`, `hurt`,
  `death`, `roar`, `victory`) are drawn procedurally into 112 px frames in
  `scripts/bosses/guardian_art.py`, cached per action/frame/facing and scaled
  2.8× at draw time. Facing mirrors the silhouette rather than redrawing every
  angle, and there are no distinct per-direction attack frames.
- The ruined-shrine arena floor is a procedural overlay (`scripts/arena_art.py`)
  baked once at load; the surrounding village still uses the existing baked
  ground texture. No new atlas art was added for the boss or arena.
- Levels 02–04 have atmospheric preview dioramas baked by
  `scripts/ui/preview_art.py`; they are selection art, not playable maps.
- The project currently has **no audio system or sound assets**. Enemy attacks,
  bolts, the guardian's slams and ground blasts, and the Void skills therefore
  have distinct visuals, timings, camera shake and hit stop, but no sound
  effects were added; adding audio would require a new mixer module and assets,
  which is outside this phase.

## Remaining issues

- In-browser behaviour (real input focus, audio, actual frame pacing) still
  needs a manual session in a real browser; the headless suite cannot prove it.
  The Phase 5 screens are rendered in `screenshots/` and can be reviewed, but
  boss feel and difficulty still want a human playthrough.
- The cultist's bolt is a simple circle with a glow, not a fully animated
  sprite, and all three archetypes share the same eight-direction facing model.
- Enemy art is intentionally limited to one procedural set per new archetype;
  there are no per-direction attack frames for the stalker or cultist. The
  guardian mirrors one silhouette instead of having per-direction boss art.
- Spawn points are hand-authored (14 validated locations); a runtime navigation
  mesh or dynamic spawn placement is out of scope for this phase.
- Levels 02–04 are deliberately selection entries only: their names, previews,
  lore, bosses and lock states exist, but no maps or encounters are generated.
- There is still no inventory, quest system or additional boss encounter.
- Browser saves are best-effort: the JSON file may live in an in-memory
  filesystem, so `localStorage` is the durable mirror. A browser with storage
  disabled can still play but will not remember unlocks after a refresh.

## Credits

Character spritesheet, environment concept atlas and ASHEN VEIL art direction
come from the project’s included original artwork. The Fallen Knight sheet,
runtime, layout, combat, baking tools and HUD were built for this prototype with
Pygame-CE and Pygbag.
