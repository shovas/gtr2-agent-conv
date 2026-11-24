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

### `.aud` (text or JCA-encrypted)
- **Intent**: sound event mapping (engine, shifts, backfires, etc.).
- **Observed**: key=value lines like `VS_INSIDE_COAST_ENGINE_1=Cars\914_idle.wav`. A 247-file survey found 86 plain-text files (CRLF, `//` comments), 153 JCA-wrapped files (magic `0f b1 ff ff`, decryptable by `jca_crypt.py`), and 8 others — so `.aud` is not always text.
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
- **Conversion notes**: mostly copy; watch DDS compression/flags, dimensions, mipmaps, and case-sensitive references. rfactortools has `img.py` for resizing/conversion helpers. `media_tool.py` reads DXT1/3/4/5, BC4/BC5, all BC6H UF16/SF16 and BC7 modes, preserves mip chains and six-face cube maps byte-for-byte, and decrypts JCA-wrapped DDS (88 encrypted cube maps found in Race07 corpora). Write-back is lossless for DXT1/3/5/cube maps but unsupported for BC4–BC7.

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

**Implemented offline (2026-11-23)**: step 1 is implemented in `gtl_to_gtr2.py` (`.trk` MASFile `.gtl`→`.gtr`, `teammaps.gtl`→`teammaps2.gtr`, `Misc.gtr` insertion; `.gtl` archives repacked as type-0 `.gtr`; subtree conversion). `validate_gtr2_tree()` covers steps 1 and 4: 34/34 GTR2 `.trk`, 85/85 `.gdb`, 145/145 `.car` pass, with MASFile references resolving 187/187 (GTR2) and 106/106 (GTL). `.gdb` session-key presence is validated (15 universal GTR2 keys) and can be adapted from a same-name GTR2 template (6 corpus pairs); `.car` key presence is validated (4 universal GTR2-only keys) and the same template-adaptation pattern copies those keys from a GTR2 template (1 same-name corpus pair plus 10 generic cases). `.aiw` keys `scrpos`/`scrori` are universal in GTR2 (34/34) and absent in GTL (0/25), copied from same-name templates (6 pairs); `.tyr` `WetWeather=1` is universal in GTR2 (15/15) and added to all 26 GTL tire files; `.hdc` wheel/gear keys are universal in GTR2 (44/44) with template adaptation for 34 flagged GTL files; `.aud` mixing/sound keys are universal in GTR2 (25/25), with 15/31 GTL files flagged; `.rcd` cold-brain keys are universal in GTR2 (223/223) and absent in GTL (0/98), with two constant values and two template-supplied. Key **values** for `.gdb`/`.car` are track/car-specific and are deliberately not invented;  `.aud` sound paths are rewritten from `Cars\` to `GTR\` (1,488 occurrences in 31/31 GTL files). `.hdc` `clutchengagerate` is rewritten 0.6→0.8 where present. `.aud` road-noise sample `gtc_road_roll_int.wav`→`road_roll_int.wav` is rewritten where present. Ten `.dmg` damage constants have universal GTL→GTR2 values and are rewritten (290 replacements in 29 files).geometry/physics/config semantics and in-game validation remain open.

**Surveyed but no confirmed rule**: `.cam` and `.eng` have identical universal key sets in both corpora (no adaptation needed); `.grd` GTL-only keys (`camera`, `iterations`, `probability`) are present in 33/34 real GTR2 files, so removal is not justified; `.cas` (`projector`) and `.dmg` (part3 keys) each flag only 1/57 and 1/29 GTL files, too weak for a corpus-wide rule.  `.ani` motion-block presence is validated (34/34 GTR2, 24/26 GTL) with template adaptation for the 6 same-name pairs.No validators were added for these.

**Archive-level survey (31 same-name GTL/GTR2 archives)**: member sets differ per track (content was genuinely changed between games), with 36 same-basename `.tga`→`.dds` texture pairs in 5 archives but 13 GTL TGAs without counterparts and 76 loose `.tga` files still shipped in GTR2 — so neither a blanket extension rewrite nor a "no TGA" rule is justified. No archive-member rule was added.

`.hat` files are gzip-compressed binary (no text keys after decompression); `.set` files are CUBEASF text whose only same-name GTL/GTR2 differences are track-specific view/lighting values, so neither yielded a corpus-wide rule.

**JCA-encrypted media**: 33,351 DDS + 4,415 TGA + 4,112 WAV files across the corpora (Race07Complete/Vanilla + VolvoTheGame) carry the `0fb1ffff` JCA header; the default key decrypts 20/20 sampled textures and Race07 audio samples to valid DDS/TGA/RIFF payloads (`media_tool.py jca-decrypt`).

**Extension survey**: the only remaining common extensions are binary media (`.bmp`, `.dds`, `.jpg`, `.mp3`, `.tga`, `.wav`), executables/libraries, `.vcr` replays (handled by `simbin_events_tool.py`), and `.set`/`.hat` with 2 GTL files — no further text config format to survey.

**`.trk` key survey**: all 16 universal keys are identical in GTL and GTR2 (no new rules beyond the MASFile rewrites).

**Pairwise value-invariant survey** (`.gdb`/`.car`/`.hdc`): no new clean GTR2-only invariants beyond the session-block `racetime == racetimescaled` rule; apparent `.hdc` hits are both-keys-absent-in-GTL artifacts, not real relationships.

**Rule scoping re-verified on decrypted JCA configs (2026-11-24)**: the HDC `clutchengagerate` rewrite (0.6→0.8) is genuinely GTL-specific — plain GTL uses 0.6 (41/42), GTR2 0.8 (43/44), while Race07 uses 0.9/1.2 and decrypted JCA Race07/Volvo files use 0.9/1.2 (only 3 JCA files have 0.6), so the rule must not be applied to Race07 sources. The TYR `WetWeather=1` key is universal (GTR2 45/15, decrypted JCA Race07 68/60, Volvo 8/8, plain Race07 25/25, GTL 3/26), so it is a presence rule rather than a GTR2-only marker. DMG constants follow the same GTL-specific pattern: `aerodiv=1.25e-5`, `aeromin=1100.0` and `wallskidthresh=2500.0` already hold in all 71 Race07 files (22 plain + 45 decrypted JCA + 4 Volvo JCA), while GTL uses the old values in 29/29; `wheeldetach` varies in Race07 (18000/35000/9000/6000), so its GTL→GTR2 rewrite must not be applied there either. A follow-up audit of `.hed`/`.grb`/`.eng`/`.trk` found identical key-set sizes between plain and decrypted JCA files (11/2/~30/13-24 keys respectively), so key-presence rules generalise; value rules remain GTL-specific (`.eng` `enginebrakingmapsetting`: GTL 3/4 in 31/36, GTR2 2 in 28/30, decrypted JCA Race07 2 in 87/92).

**Value-scale candidates examined but NOT promoted**: median GTL→GTR2 numeric shifts exist for `.hdc` `bumpstopspring` (250000→125000), `bumpstopdamper` (2000→1050), `forwardgears` (4/5→6), `brakepressuresetting` (10→20), `diffcoastsetting` (2→8), `.eng` `enginebrakingmapsetting` (4→2) and `.tyr` `optimumpressurebase` (60/100→90). None is universal in both corpora (e.g. 3 GTR2 `.hdc` files retain GTL `bumpstopspring`/`bumpstopdamper`, 3 retain GTL `upshiftdelay`/`downshiftdelay`, 2 retain GTL `brakepressuresetting`), so applying them would be speculative; only `clutchengagerate` (0.6→0.8, universal where present) and the `.aud` path prefixes were promoted. A strict universal constant-difference sweep over 16 text formats found no further rules.

## Confidence / gaps

- **High confidence**: MAS container identification; `.car/.gdb/.trk/.aud/.hdc/.eng/.dmg/.hed/.cam/.grd/.rcd` general purpose from samples.
- **Medium confidence**: exact required key sets for GTR2 compatibility across all mod variants.
- **Needs deeper spec work**: `.gmt` version differences, `.svm/.lma/.ani` exact binary semantics, GTR2 class/category mapping rules, and physics compatibility when crossing GTL->GTR2. Use `GTR2Steam` as target oracle and small controlled test conversions.