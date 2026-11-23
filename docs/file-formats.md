# GTL -> GTR2 File Format Reference (first pass)

Purpose: working reference for converting GT Legends (GTL) content to GTR2. This is an early first-pass map based on local installs (`../GTLSteam`, `../GTR2Steam`), `../rfactortools`, `quickbms_scripts/mas.bms`, and small samples in `hand_selected/`. It is not a complete spec; verify against game behavior before treating any field as canonical.

**Note:** the current, broader format inventory across all reviewed game corpora is in `docs/binary-formats.md`; GMT internals are detailed in `docs/gmt-format.md`. For agent-oriented usage, start with `README.md` and `FEATURES.md`.

## Observed extension inventory

### GTL GameData (top)
`wav 548, gtl 493, tga 247, svm 188, rcd 98, car 96, bik 95, lma 62, cas 57, gdb 53, hdc 42, eng 36, grb 35, sp 34, aud 31, dds 30, dmg 29, grd 27, tyr 26, gmt 26, ani 26, trk 25, jpg 25, cam 25, bmp 25, aiw 25, ...`

### GTR2 GameData (top)
`wav 687, txt 687, gtr 620, rcd 223, bmp 180, car 145, dsi 142, ds 142, fxm 135, gdb 85, tga 76, svm 70, jpg 68, cas 57, lma 54, hdc 44, cam 35, trk 34, hat 34, grd 34, ani 34, aiw 34, gmt 30, eng 30, sp 26, dmg 26, dds 26, grb 25, aud 25, dst 20, ...`

Notably absent in GTL GameData: rFactor-style `.veh/.scn/.gen/.hdv/.tbc/.sfx` (0 observed). GTL->GTR2 is SimBin/ISI lineage conversion, closer to GTR2 than rFactor.

## 1. Archives / containers

### `.gtl`, `.gtr` (binary MAS archive)
- **Intent**: package multiple game assets (textures, GMTs, maps, etc.) into one archive.
- **Observed**: both GTL `.gtl` and GTR2 `.gtr` start with `GMOTORMAS10\0\0\0\0\0` (MAS type 0). Confirmed by header inspection and round-trip via `mas_tool.py`.
- **Structure (type 0)**:
  - `u8 sig[16]` = `GMOTORMAS10\0\0\0\0\0`
  - `u32 file_count`, `u32 data_size`
  - `file_count * 256-byte entries`: `<pad4 u32 offset u32 size u32 zsize char name[240]>`
  - `offset` relative to base `24 + 256*file_count`
  - payload: zlib-compressed if `zsize != size`, else raw
- **Conversion**: rename/repack as `.gtr` for GTR2 target where appropriate; update references in `.trk`/other files. Validate extracted names and case.
- **Tools/refs**: `mas_tool.py`, `rfactortools/mas.py`, `quickbms_scripts/mas.bms`, `../MAS2Extract` is for rF2 MAS2 (different format).

## 2. Vehicle definition / physics chain

### `.car` / `.CAR` (text)
- **Intent**: per-skin/entry vehicle instance. Links graphics, physics, sounds, driver/team metadata, and class/category info.
- **Observed fields** (GTR2 `04142_G2_BMW_M3GTR.car`, GTL `859_SIM_GTC_Cobra.CAR`): `HDVehicle`, `Graphics`, `GenString`, `Sounds`, `HeadPhysics`, `Eyepoint`, `CameraTarget`, seat/pedal positions, `Number`, `Team`, `PitGroup`, `Driver/Driver1/Driver2`, `Description`, `Engine`, `Manufacturer`, `classes`/`Classes`, `Category` (seen in GTR2 samples elsewhere), `ComparativeTime`.
- **Conversion notes**:
  - Normalize extension/case (`.CAR` -> `.car` as needed) and audit all references.
  - Remap `classes`/categories to GTR2-appropriate class structure; preserve semantics carefully.
  - Verify referenced files exist: `.hdc`, `.cas`, `.aud`, `.hed`, `.eng` (sometimes referenced indirectly), tires/physics chain.
  - GTL and GTR2 field sets overlap heavily but are not identical; compare against `GTR2Steam` cars before writing.

### `.hdc` (text)
- **Intent**: high-detail car/physics configuration. Pointed to by `.car` `HDVehicle=`.
- **Observed sections/keys**: `[GENERAL]` with `Mass`, `Inertia`, `FuelTankPos`, `DamageFile`, `TireBrand`, fuel/wing/suspension/brake/aero params; many numeric ranges/settings. Large, vehicle-specific.
- **Conversion notes**: usually copy with validation; ensure `DamageFile`, tire brands, engine/sound/graphical dependencies are compatible. Do not blindly rewrite numeric physics unless intentionally converting physics model.

### `.eng` (text)
- **Intent**: engine torque curve and engine parameters.
- **Observed**: `RPMTorque=(rpm, engine_braking, torque)` lines (GTR2 M3GTR.eng).
- **Conversion notes**: copy/validate; check units/ranges and references from vehicle chain.

### `.tyr` (text)
- **Intent**: tire compound/behavior data. Referenced by brand/compound settings in `.hdc`.
- **Observed**: present in Teams (e.g. `Dunlop_GT.tyr`).
- **Conversion notes**: compatibility-sensitive; copy/validate carefully. GTR2 tire model expectations may differ from GTL mods.

### `.dmg` (text)
- **Intent**: damage model parameters.
- **Observed**: `damage.dmg`, vehicle-specific dmg files; `[PHYSICAL]` with detach thresholds, mass/inertia, collision params.
- **Conversion notes**: copy/validate; ensure instance names/parts match car graphics.

### `.sp` (text)
- **Intent**: suspension geometry/physics support file.
- **Observed**: starts with `[BODY]`, `[JOINT]`, `[HINGE]`, `[BAR]` style definitions (M3GTR.sp).
- **Conversion notes**: copy/validate; tightly coupled to physics/graphics model.

### `.grb` (text)
- **Intent**: gearbox/ratios.
- **Observed**: `[GEAR_RATIOS]`, `[FINAL_DRIVE]` with `ratio=(n,m)` entries.
- **Conversion notes**: copy/validate.

### `.hed` (text)
- **Intent**: head/camera physics.
- **Observed**: `headphysics.hed` with `HeadMass`, `HeadInertia`, min/max pos/ori, spring defs.
- **Conversion notes**: usually shared/copy; referenced by `.car` `HeadPhysics`.

### `.cas` (text-like graphics config)
- **Intent**: car/spinner graphics configuration, material/instance setup.
- **Observed**: present for cars (e.g. `BMW_M3GTR.cas`).
- **Conversion notes**: copy/validate referenced GMTs/textures/material names. Path/case sensitivity matters.

### `.aud` (text)
- **Intent**: sound event mapping (engine, shifts, backfires, etc.).
- **Observed**: key=value lines like `VS_INSIDE_COAST_ENGINE_1=Cars\914_idle.wav`.
- **Conversion notes**: copy/validate WAV paths; path separators/case may need normalization. rfactortools has `sfx` parsing patterns for related ISI sound files; `.aud` is simpler mapping-style.

## 3. Track / location files

### `.gdb` (text)
- **Intent**: track/event/game database. Defines track metadata, filters, classes/categories, scoring/sessions, AI settings, scene order, lighting/fog, etc.
- **Observed**: GTR2 `24H_Hock.gdb` has `Game Name`, `Game Filter`, `SpecialClasses`, `Category`, `DefaultScoring`, `SeasonScoringInfo`. GTL `Anderstorp.gdb` has track metadata (`TrackName`, `VenueName`, `Length`, `SettingsFolder`, laptimes, lighting).
- **Conversion notes**: GTR2 expects specific structure/keys; GTL track GDBs may differ. Map filters/classes/categories to GTR2 conventions. rfactortools has `gdb.py` for parsing/modifying GDBs.

### `.trk` (text scene/track file)
- **Intent**: scene description: search paths, MAS files, view/camera setup, instances/mesh refs.
- **Observed**: starts with `CUBEASF`; has `SearchPath=...`, `MASFile=...gtr`, `View=...`, `Instance=... { MeshFile=...gmt ... }`.
- **Conversion notes**: must rewrite MAS refs from `.gtl` to `.gtr` where converted; normalize paths/case; validate mesh/MAS existence. Related to rfactortools SCN/TRK handling concepts, but TRK is SimBin track scene form.

### `.aiw` (binary)
- **Intent**: AI waypoints, pit/grid/telemetry paths, track AI data.
- **Observed**: binary file present per track variant (`3Anderstorp.AIW`, `SANDERSTORP.AIW`). rfactortools has `aiw.py`.
- **Conversion notes**: usually copy unchanged unless format/version incompatibility found; verify in-game. Legacy had extensive AIW sampling scripts.

### `.cam` (text)
- **Intent**: track camera definitions.
- **Observed**: `StaticCam=...`, `TrackingCam=...` blocks with Position/Orientation/FOV/ClipPlanes/Activation fields.
- **Conversion notes**: usually copy/validate; check coordinate conventions and activation locations.

### `.grd` (text)
- **Intent**: grid/presentation script/data.
- **Observed**: `PreRacePresentation { CinematicEvent { ... } }`.
- **Conversion notes**: copy/validate.

### `.ani` (text/binary-ish by game usage; observed as track asset)
- **Intent**: animation data (track/scene animations).
- **Conversion notes**: copy/validate; inspect if target complains.

## 4. Models, textures, visuals

### `.gmt` (binary model)
- **Intent**: 3D mesh/model used by game/scene/cars.
- **Observed**: present as loose files and inside MAS archives. rfactortools has `gmt.py`; legacy referenced `gmtconvert`.
- **Conversion notes**: high-risk area. GMT versions/layouts differ across ISIMotor generations/games. Validate magic/version; convert only when necessary and with tests.

### `.dds`, `.tga`, `.bmp`, `.jpg` (binary textures/images)
- **Intent**: textures, skins, UI images, maps.
- **Conversion notes**: mostly copy; watch DDS compression/flags, dimensions, mipmaps, and case-sensitive references. rfactortools has `img.py` for resizing/conversion helpers.

### `.svm` (binary/text-ish in some contexts; observed as team/skin/support asset)
- **Intent**: SimBin vehicle/material/skin-related asset (observed frequently in Teams).
- **Conversion notes**: copy/validate; confirm exact role per file before transformation.

### `.lma` (binary)
- **Intent**: animation/model asset (commonly used by SimBin titles).
- **Conversion notes**: copy/validate.

## 5. Audio / media

### `.wav` (binary audio)
- **Intent**: sound samples referenced by `.aud`.
- **Conversion notes**: copy; preserve paths/names expected by AUD mappings.

### `.bik` (binary video)
- **Intent**: Bink video assets.
- **Conversion notes**: copy as-is; `media_tool.py bink-decode` / `bink-encode` can decode to PNG frames and encode new BIKi videos via external tools (see `CAPABILITIES.md`).

### `.mp3` (binary audio)
- **Intent**: occasional music/commentary/audio assets.
- **Conversion notes**: verify target location/support; usually copy.

## 6. Talent / sim support / misc

### `.rcd` (text)
- **Intent**: AI driver talent/profile.
- **Observed**: blocks with driver name, nationality, stats (`QualifyingAbility`, `RaceAbility`, aggression/composure, etc.).
- **Conversion notes**: copy/validate; class/team associations may need adjustment.

### `.set` (text/config)
- **Intent**: setup/config data.
- **Conversion notes**: inspect case-by-case.

### GTR2-observed support formats (less/no GTL presence)
- `.txt` - metadata/docs/config text; inspect.
- `.dst` - driving school/training data.
- `.dsi/.ds` - support/config/data files.
- `.fxm` - material/effect data.
- `.hat` - AI/track auxiliary data.
- May be GTR2-specific; do not invent during GTL conversion unless required.

## Conversion priority (GTL -> GTR2 MVP)

1. **Container/path normalization**: `.gtl` -> `.gtr` where needed, `.trk` MAS refs, case/path fixes.
2. **Vehicle chain**: `.car/.CAR`, `.hdc`, `.eng`, `.tyr`, `.aud`, `.cas`, `.dmg`, `.sp`, `.grb`, `.hed`, textures/models inside archives.
3. **Track chain**: `.gdb`, `.trk`, `.aiw`, `.cam`, `.grd`, `.ani`, textures/models.
4. **Validation**: parseability, missing refs, stale source extensions, GTR2 layout sanity (`GameData/...`), and in-game smoke test later.

**Implemented offline (2026-11-23)**: step 1 is implemented in `gtl_to_gtr2.py` (`.trk` MASFile `.gtl`→`.gtr`, `teammaps.gtl`→`teammaps2.gtr`, `Misc.gtr` insertion; `.gtl` archives repacked as type-0 `.gtr`; subtree conversion). `validate_gtr2_tree()` covers steps 1 and 4: 34/34 GTR2 `.trk`, 85/85 `.gdb`, 145/145 `.car` pass, with MASFile references resolving 187/187 (GTR2) and 106/106 (GTL). `.gdb` session-key presence is validated (15 universal GTR2 keys) and can be adapted from a same-name GTR2 template (6 corpus pairs); `.car` key presence is validated (4 universal GTR2-only keys) and the same template-adaptation pattern copies those keys from a GTR2 template (1 same-name corpus pair plus 10 generic cases). `.aiw` keys `scrpos`/`scrori` are universal in GTR2 (34/34) and absent in GTL (0/25), copied from same-name templates (6 pairs); `.tyr` `WetWeather=1` is universal in GTR2 (15/15) and added to all 26 GTL tire files. Key **values** for `.gdb`/`.car` are track/car-specific and are deliberately not invented; geometry/physics/config semantics and in-game validation remain open.

## Confidence / gaps

- **High confidence**: MAS container identification; `.car/.gdb/.trk/.aud/.hdc/.eng/.dmg/.hed/.cam/.grd/.rcd` general purpose from samples.
- **Medium confidence**: exact required key sets for GTR2 compatibility across all mod variants.
- **Needs deeper spec work**: `.gmt` version differences, `.svm/.lma/.ani` exact binary semantics, GTR2 class/category mapping rules, and physics compatibility when crossing GTL->GTR2. Use `GTR2Steam` as target oracle and small controlled test conversions.