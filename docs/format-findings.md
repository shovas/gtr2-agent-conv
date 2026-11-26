# Consolidated format & reverse-engineering findings

**Start here** when working on ISIMotor/SimBin formats, EXEs, or telemetry. This
is a topic-organized index of *verified* findings; `docs/open-issues-research.md`
keeps the chronological experiment log (including superseded claims). Nothing
here is a speculation: each entry has either an independent decoder with
regression tests or an explicitly documented negative.

## 1. GMT layouts and ISI encryption

- Three generations: **old layout** (magic `c8cfd2d8…bf90` at `0x1D4`, byte 13
  `a8` in GSC/rF1, `a7` in GTR2/GTL), **new layout** (magic at offset `0x08`,
  108-byte mesh records at `0x16C`), and **GTR1 third magic** (handled by
  `gmt_semantic.read_gtr1_geometry()`).
- A fourth variant, **`RaceGMT\0`**, occurs in 643 Race07Complete meshes. It is
  not a standard GMT: `race_gmt.parse_header()` verifies an 8-byte magic,
  u32 printable-name length, the name, a constant flag word `0x04000020`, four
  finite f32 triples (the third repeated as the fourth in **643/643** files),
  then a payload of mixed f32/u16 records. All 643 files parse cleanly; the payload
  geometry is **not** decoded and `parse_gmt()` returns zero meshes for them.
  Payload probing found f32 triples and u16 index triples at 36-/72-byte
  strides in several models (e.g. `PEOPLE_STAND_01`, `SEATS29_LODA`), but the
  stride is not universal across the 643 files, so no record layout is claimed.
  Full-tier test: `test_racegmt_container_parser`. Payload probing found a
  bounded structure in several models: after the header and a prefix, a run of
  36-byte records begins with u16 index triples `(0,1,2), (3,4,5), ...` for at
  least the first eight records (verified in `PEOPLE_STAND_01/02`, `STAND_25`,
  `SEATS29_LODA`). The index sequence later resets with a model-dependent
  period, so only the opening run is asserted. Full-tier test:
  Their five f32 fields are finite and bounded (<1000) in that opening run
  but contain NaNs later, so the alignment is not global. Full-tier test:
  `test_racegmt_payload_has_indexed_36_byte_records`.
- `gmt_layout.is_old()/is_new()` detect layouts; `old_to_new_semantic()` rebuilds
  a new-layout mesh from decoded old-layout geometry. The semantic reader now
  recognizes all eight observed mesh-record magic low words (`0x4001/11/13/15/35`
  and `0x6011/15/35`); previously `0x60xx` files (BRIDGE1, cameras, etc.) had
  zero recognized submeshes.
- A **template-free container** can be synthesized: `gmt_format.build_synthetic_gmt()`
  builds a valid new-layout GMT from mesh objects alone (zeroed 0x18..0x16C
  header, empty material tail). It parses, round-trips and passes
  `validate_materials.check_gmt()`, but carries no materials/textures, so it is
  a test/fallback container rather than a render-ready conversion.
- GTL archives are already new-layout: 2,529 sampled GMTs from `.gtl` archives
  all carried the new magic, so GTL→GTR2 needs no mesh relayout (only TRK/GDB/
  archive-convention fixes). Full-tier regression test.
- **Critical:** ISI-encrypted GSC-family GMT members must be decrypted with
  `isi_crypt.decrypt_bytes(raw, skip=4)`. `skip=1` leaves a spurious per-file XOR
  layer that *looks* like a "region mask schedule" but corrupts bulk vertices.
  With `skip=4`, 150/150 sampled members have submeshes, plausible positions and
  faces. `gmt_semantic.decode_gsc_member()` implements the validated path;
  `decode_gsc_xor_gmt()` is retained only as a historical artifact path.
- **rF1 structural vs semantic bridge:** `rf1_to_gtr2.convert_bytes()` defaults
  to `gmt_layout.old_to_new()`, which fills only the first mesh record of a
  multi-object GMT; on a 150-member sample that path passes
  `validate_conversion.validate()` **0/150** times (82 sources have >1
  submesh). Passing `relayout=True` uses `old_to_new_semantic()` and passes
  **150/150** with all positions/UVs/faces/f0 preserved. Prefer the semantic
  path for rF1 conversions. Full-tier test:
  `test_rf1_semantic_conversion_validates`.
- `gmt_semantic.find_submeshes()` scans both layouts; `read_gsc_geometry()`
  applies a quality gate (`finite_positions`, `plausible_positions`, `face_count`)
  before any geometry is trusted.

## 2. GSC → GTR2 mesh conversion

- `gmt_layout.gsc_member_to_gtr2(raw_member)` and
  `python3 gmt_layout.py INPUT OUTPUT --gsc` produce GTR2-layout GMTs.
- Verified on 150/150 members: output parses with `gmt_format.parse_gmt()`;
  vertex/face counts, original `f0` markers, normals and `f7` colours are
  preserved (raw 32-byte vertex records are copied, not rebuilt). Index
  integrity verified on 40 converted meshes / 56,273 triangles: no out-of-range
  indices and no degenerate faces. UVs are preserved exactly on 150/150
  sampled members (source vs converted pairs compared byte-for-byte).
- **Winding:** GSC, rF1 old-layout and GTR2 target meshes all show *inverted*
  face winding relative to stored normals (cross-product agreement ~0 forward,
  ~1 reversed). Do **not** flip indices during conversion.
- GTR1 48-byte vertices carry UV pairs in fields 9/10 (fields 8/11 are always
  zero in 20,017 sampled vertices). `gtr1_to_gmt.uvs_from_gtr1()` extracts
  them and `gtr1_to_gmt()` writes them into the GTR2 UV block; 30/30 sampled
  conversions reproduce source UVs exactly. UVs are available only for
  descriptor-based GTR1 meshes (213/213 sampled); descriptor-less fallback
  meshes have no UV source (187/187 correctly yield none).
- VRL UVs are per corner, so `vrl_to_gmt.prepare_geometry_with_uvs()` expands
  shared vertices into one vertex per corner and rebases triangle indices.
  25/25 sampled conversions round-trip UVs exactly; shuffled UVs fail >90%.
- `batch_convert.py` includes a `gsc` family; all written meshes are re-parsed
  and pass `validate_materials.check_gmt()`. Round-tripping 40 converted
  meshes through `gmt_format.relayout_gmt()` preserves vertex and stream bytes
  exactly.
- **Converted UV range caveat:** shipped GTR2 UVs are mostly small (median
  |u| 0.39, 98.6% within [-1,1]); converted GSC/VRL UVs are much wider
  (median |u| ~0.99, ~55% within [-1,1]). Source→target UVs are exact, so this
  reflects source content, not a conversion bug — but in-game texture tiling
  correctness remains unverified. A finiteness/bounds guard test is included.
 meshes whose record has
  `rec[6] < rec[7] < rec[8]` carry two extra 32-byte-per-vertex streams. In
  46.7% of 1,605 sampled meshes every 8-float stream record follows
  `[U, S, V, S, V, S, V, S]` — only three distinct values per vertex. A flat
  road mesh shows column 2 as a planar world-x projection (r=1.0) with columns
  4/6 as ×10/×15 copies, but this is not general (only 39/447 meshes), so UV
  *semantics* remain unassigned. `gmt_format.decode_stream_records()` exposes
  the verified triples; no UV correctness claim is made.
  A broader invariant: `gmt_format.stream_column_signature()` shows column 7
  equals column 1 in 2,594/2,601 (99.73%) stream meshes; the seven exceptions
  are all TRACKnn meshes with a distinct scheme.
- **Cross-corpus confirmation:** JCA-decrypted Volvo and Race07 GMTs expose
  the same UV blocks and signatures: 300/300 parsed meshes per game had a
  `vc*32` block, with 257/300 (Volvo) and 264/300 (Race07) matching the two
  dominant GTR2 signatures. A per-record shuffle control scores 0%.
- `gmt_format.read_mesh_uvs()` is a unified reader: it returns per-vertex
  (u, v) from the 32-byte record's +4/+8 offsets for both single-block and
  two-stream meshes, and agrees with `gmt_semantic.read_gmt()` on 800/800
  sampled meshes spanning both layouts.
- **Integer tiling ratios:** in the `(1,2,3,4,5,6,1)` UV signature, columns 4
  and 6 are often constant integer multiples of column 2 (e.g. ×5/×8, ×20/×24)
  while columns 1/3/5/7 are binary flags — 915/1,980 meshes; shuffling column 2
  drops the match to 0/500. The rule also decodes in JCA-decrypted Race07
  meshes, so it is not GTR2-only. The ratios are material-associated: among 487
  multi-mesh material groups, 91.6% have identical ratios vs 4.8% for a
  distribution-preserving shuffle. A mesh's own ratio also appears as an f32
  in its material record more often than a ratio drawn from the same
  distribution (0.314 vs 0.160), supporting material-level metadata, but no
  fixed material offset was found. `gmt_format.uv_tiling_factors()` exposes it.
- **Two-stream meshes duplicate one UV pair:** in 1,731 two-stream meshes,
  stream3's columns 3..7 are zero in 100%, and columns 1/2 agree with stream2
  per vertex in 96% of meshes (median agreement 1.0 vs 0.023 for shuffled
  stream3 rows). `gmt_format.stream_cross_agreement()` exposes the check. The
  distinct stream3 column 0 is not world-position derived (median |r| 0.135)
  and, like f0, is nonzero only at vertex 0 — any per-vertex correlation
  between the two is a sparsity artefact.
- **Two UV block layouts, both now parsed:** GTR2 uses either explicit stream
  end markers (`rec[6] < rec[7] < rec[8]`, ~18%) or a single `vc*32` block at
  `rec[6]` running up to the index array (~86%). `parse_gmt()` now exposes
  both as `stream2_data`, and repacking preserves vertex and UV bytes on
  563/563 sampled single-block meshes. The single-block fallback is exposed
  **only** when `index_offset - rec[6] == vertex_count*32`; an earlier broader
  fallback exposed misaligned blocks and broke an existing stream-stride test.
  Which layout is used is **exactly**
  predicted by mesh flag bit `0x20` (`rec[1] & 0x20`): 40,327/40,327 sampled
  meshes agree. All converted outputs use the single-block form with the bit
  clear, so their flags are consistent. In the single-block layout the UV pair sits at
  `rec[6]+4/+8` (dominant signature `(1,2,0,0,0,0,0)`).
- **Converter UV layout corrected:** `old_to_new_semantic()` previously wrote
  a 4-byte count lead before the UV block and placed UVs at `+8/+12`, so
  converted files did not match real GTR2. It now writes a lead-free `vc*32`
  block with UVs at `+4/+8`, and the gtr2 schema's `uv_sub_off` is 0 in both
  `gmt_semantic.py` and `validate_conversion.py`. Converted blocks now have
  exactly the dominant real signature; source/converted UV equality is
  restored in offline validation.

## 3. EXE / embedded-resource code

- `gsc_exe_tool.py` reads the `AXS.GS.0` container in GSC-family EXEs: `.keyMan`
  GUID keys, SHA-1 + Blowfish-CBC (big-endian, derived IV, unaligned-tail fix),
  `lzma86head` and LZ4 in pure Python. Verified vs QuickBMS: Marcas 34/35 and
  AMS 626/627 files byte-identical. SCE type-1 resources use the key at
  `key_list()[i+11]` (204/204 valid headers, 207/218 resources extracted).
- `GameStockCar/GSC.exe` embeds five plain GMT images (file offsets
  `0x3a3980`…`0x3a5cb0`) with valid geometry — evidence that `a8` is a genuine
  GSC magic.
- **Static-analysis blockers:** `Marcas.exe`, SCE `GSC.exe`, `AMS.exe` are packer
  stubs; `GameStockCar/GSC.exe` is YMY-packed with loader strings but no code
  xrefs. No static derivation of the ISI skip is possible without unpacking.
- `GTR2Dedicated.exe` also carries the GTTF string and the same pointer-table
  structure (validator `0x526dc0`, fixup `0x52a300`) but no 63-byte frame read
  site either — no serializer recovered from that build.
- `GTR2.exe` (unpacked PE32) code map: GTTF validator `0x527000`, reader
  `0x52be30`, writer `0x52a540`, GMT loader `0x5d68d0`, mesh/shader fixup
  `0x5e9ab0`, shader helpers `0x5e54e0`/`0x5e55e0`, material-library lookup
  `0x5e85c0`. No 63-byte file serializer was found; those 63-byte objects are
  runtime replay state.
- All 29 shipped GTL/GTR2 EXEs/DLLs contain **no** `PHS`/`PHYSICS` strings.
- Debug-artifact sweep: no `.pdb`/linker `.map`/COFF symbol tables in any game
  install. `GTR2.exe` embeds an RSDS reference
  (`D:\work\gtr2\workspace\Projects\copperhead\…\GTR2.pdb`, GUID
  `a2746770…`, age 16), but the PDB itself is absent. Exports are only five
  UI/Game entrypoints and RTTI names are UI classes — no format semantics.

## 4. GTTF / IRSR (time trial / replay payloads)

- Container: gzip with `//[[gMb…]]` wrapper; magic `GTTF`/`IRSR`, f32 version,
  u32-length TRK and AIW filenames. `simbin_events_tool.py` is the reader.
  `gzip_simbin_tool.compress_simbin()` writes byte-identical containers by
  patching the XFL/OS header bytes to `00 0b` (verified on 29 GTT + 9 VCR
  files), so a payload-level ghost writer is feasible. GTL replays use the
  same container at version **1.01** (vs GTR2's 1.05): its summary is
  `-1e32` followed by zero-prefixed u24 frame/sub-record counts and an f32
  duration. All four GTL `.Vcr` files parse to exact EOF and rewrap
  byte-identically; all 13 local replays across both games are decoded.
  `simbin_events_tool.set_session_seconds()` already edits that field in place
  (at most four bytes change) and the result rewraps byte-identically apart
  from the edited value.
- Header fields after filenames: `u8, u8, f32, u8, u32`; the f32 is one of
  **36000/43200/46800** (10/12/13 h in seconds — strong inference) across 42
  files. Exposed as `EventFile.session_seconds` etc.
- Header flags distinguish the two containers: all 29 GTTF ghosts have
  `(a,b,c,u) = (0,0,1,0)`, while the nine IRSR replays use several combinations
  (e.g. `b=6` in two "HOT LAP" files, `c=8` in Magny-Cours). Exact flag
  semantics remain unclaimed.
- **Camera coordinates are inverted** relative to AIW waypoints: across 30
  GTR2 tracks with matched `.cam`/`.AIW` pairs, track-mean camera x has the
  opposite sign to track-mean waypoint x in 90% of tracks (vs 53.5% shuffled;
  Pearson r −0.84); y and z show the same tendency (r −0.99 / −0.75). This
  confirms the guitarmaen CAM/AIW note empirically. At point level, negating
  each camera's `ActivationLocation` moves it 4.4× closer to the track's AIW
  waypoints (median 25.2 vs 110.2 world units; 80% of 422 cameras), so the
  inversion applies to individual coordinates, not just track means. The same
  convention holds in rF1 (594/684 cameras, median 15.3 vs 304.6) and GTL
  (246/274, 10.1 vs 113.9), so it is a gMotor-wide storage convention, **not**
  a GTR2-specific conversion step; the rF1→GTR2 pipeline leaves CAM files
  byte-identical (50/50 sampled). Separately, the `//[[gMa1.` header itself is
  generation-specific: 34/34 sampled rF1 and 25/25 GTL CAMs carry it, while
  34/34 sampled GTR2 and 40/40 Race07 CAMs start directly at `StaticCam=`.
  GTR2 AIWs, unlike CAMs, still carry the header (31/31), so header stripping
  must not be generalised from AIW to CAM without runtime evidence; our tree
  converters preserve the source bytes. Full-tier test:
  `test_cam_header_convention_by_game_generation`.
- All nine shipped `.Vcr` replay files parse with the same reader: gzip +
  gMb wrapper + `IRSR` v1.05, with driver/car/team names and session values
  from the same 36000/43200/46800 set. The GTTF-specific frame-grid detector
  does **not** find their frames (no `01 00 00 34 00 20 00` marker), so their
  frame layout remains a separate, undecoded format. The payload does have a
  an **86-byte period confined to the header region** (first ~0x2000 bytes;
  byte-match 0.78 at lag 86 vs chance, harmonics at 172/258/344). The bulk
  frame data has no 86-byte structure (0.04–0.06 match), so this is a header
  table rather than the frame grid. Static analysis located the ghost writer
  at `GTR2.exe` RVA `0x52a540` (GTTF/IRSR magic branch, 105 sixteen-byte object
  slots at `0x52a6ca`, per-object linked-list serialization) — evidence for
  variable-length object records. Earlier 4-byte-aligned stride scans also
  missed 86 because it is not a multiple of 4. Frame semantics remain
  unknown. The EXE-derived object layout yields a working parser
  (`simbin_events_tool.parse_object_records()`): across all nine GTR2 replays
  it finds chains of 2–6 records whose names are the participants (driver
  entries plus `Safety Marshal`); shuffled payloads yield ~1 chance record.
  Fixed blocks hold `.CAR`/skin names; the trailing f32 pair is an activity
  window `[start, end]` with `-1e32` (`0xF49DC5AE`) meaning unbounded.
  Bulk data shows a separate **20-byte lag excess** over neighbouring

- **Replay frame stream decoded:** `parse_vcr_frames()` consumes the payload
  exactly in **all 9** GTR2 replays: `count_a` frames (declared), each u32
  absolute time + u16 sub-record count, each sub-record u32 header + packed
  size; total sub-record count equals `count_b`, and `last − first` frame time
  equals the summary duration. The first frame time equals the participant
  window start. Bulk data also shows a 20-byte lag excess in 7/9 replays.
  Variants: `Anderstorp.Vcr` has a second continuous 82-frame segment (203
  total, exact EOF), and `Dubai International.Vcr` uses Latin-1 accented
  participant names. `shift_replay_times()` shifts all frame times and
  participant windows consistently while leaving spans and sub-records
  untouched. `simbin_events_tool.py FILE --shift S --out OUT` exposes this as
  a CLI. Driving-school `.dsi` files use the same IRSR/replay frame
  stream: their instructor ghost line equals the decoded driver-state
  positions exactly, one point per frame. All 142 shipped `.dsi` files parse
  to exact EOF (68,916 frames total). Sub-record low-byte tags follow participants: `0..N-2`
  are driver state records, `0x68` accompanies the `Safety Marshal`, and
  `0xff` marks event records whose bodies can contain texture names such as
  `DYTEX000`/`SRTEX000`/`SSTEX000`. A 53-byte driver-state body decodes via
  `vcr_driver_state()`: four u16s at +8 and six f32s starting at byte **29**;
  the first three are smooth world positions (median frame-to-frame step <5 m
  vs ~100× larger for shuffled samples), the fifth (byte 45, `angle_like`) is
  angle-like and correlates with position-derived heading (|r| >0.4 vs a
  shuffled baseline). The fourth float (`small_a`, byte 41) tracks **vertical
  motion**: r=0.13–0.96 (mean 0.641) against position y-delta in 8/8 replays
  (slightly better than per-second vertical velocity); the elevation-to-value
  slope varies ~91x across replays, so the channel has no universal scale
  (seeded permutation p<0.001); the sixth (`small_b`) remains unexplained:
  across the eight long replays its correlations with elevation delta, speed,
  heading rate, lateral acceleration and longitudinal acceleration change
  sign between files and average |r| < 0.25; lags in [-10, +10] likewise give
  no consistent peak (full-tier test
  `test_driver_small_b_unexplained_by_kinematics`).
  Full-tier test: `test_driver_small_a_tracks_elevation_change`. Calibration
  against AIW-derived road gradient is track-dependent (Brno HOT LAP r=0.98,
  Imola r=0.00), so no universal scale conversion is claimed; guarded by
  `test_driver_small_a_aiw_slope_calibration_is_track_dependent`. The four u16s form
  wheel-like pairs: the rear-left/rear-right gap is <1% of the value scale in
  Monza.Vcr, versus a much larger gap after shuffling. Wrapped frame-to-frame
  **Verified signal:** the *difference* `shorts[0] - shorts[1]` correlates
  with position-derived heading rate (next minus current angle) in **8/8**
  replays with >=300 driver states (r = -0.087 to -0.365, mean -0.171; seeded
  corpus permutation p = 0.004), far more consistent than any individual slot
  or speed relationship. Lateral acceleration (speed x heading rate) is only
  a weaker companion (7/8 negative, mean -0.108, p=0.028), so heading rate is
  the primary association. A fixed bicycle-model calibration (wheelbase 2.5 m)
  gives median raw/radian ratios spanning 10^3..10^5 with inconsistent signs,
  so no universal scale conversion is claimed. Per-car calibration is also
  unavailable: replay `car` labels are 5-digit menu IDs absent from all shipped
  `.hdc` configs (0 matches). Full-tier guard:
  `test_replay_car_labels_do_not_resolve_to_hdc`. Cross-correlation over lags
  -5..+5 frames has no sharp peak (best lag -1, mean r -0.180 versus -0.171 at
  lag 0), so no timing offset is implied. This is a steering-like channel, but
  no unit mapping is claimed. Full-tier test:
  `test_driver_short_pair_difference_tracks_heading_rate`.
  Raw deltas appeared to correlate with derived speed in 4 of 28 replay/slot pairs
  (|r| > 0.15), but the signs were inconsistent and linear detrending collapsed
  all four to |r| <= 0.109 — a shared slow trend, not a wheel-speed decoder.
  A search over wrap moduli 1024..65536 also found no consistent speed channel
  (best per-replay |r| never exceeds 0.5 in any modulus; full-tier test
  `test_driver_u16_wrap_moduli_not_wheel_speed`). Cumulating four wrapped u16
  totals gives r = 0.90–1.00 with cumulative distance, but that is a shared
  monotonic-trend artifact: the per-frame four-wheel sum has mean |r| < 0.1
  against step distance, at permutation chance. Full-tier test:
  `test_driver_u16_deltas_not_wheel_speed`.
- Every ghost ends with a **20-byte tail** (5 f32s). Its first two floats are
  a per-track fixed point (median distance 0.6 between ghosts of the same
  track vs 178 for random pairs) near that track's final frame position —
  consistent with a start/finish-line coordinate. The remaining three mirror
  the final frame's state: float 3 ≈ final heading (median error 0.0004 rad),
  float 4 ≈ final frame +16 (~0.0003), and float 2 tracks final `slot48_low`
  (|r| 0.993 vs 0.24 shuffled). Full-tier test included.
- **24-byte pre-frame records** immediately precede the frame grid: six f32
  fields `(y, z, heading, f3, f4, x)`. They form the reference racing line.
  `find_preframe_records()` / `reconstruct_frame_x()` expose x; frames get
  `x`, `world_position`, `path_f3`, `path_f4`.
- Frame stride 63 bytes; `read_frames()` also exposes `engine_speed` (+32),
  `slot48_low/high` (packed i16 channels at +48), and CLI `--frames` prints all
  recovered fields.
- Verified mappings / invariants (all permutation-controlled, see tests):
  - frame `+0` = path y, `+4` = path z (r≈1.0);
  - frame `+12` = path heading = `atan2(dx,dz)` (coherence 0.992 vs 0.024);
  - frame `+20` is absolute session time with an arbitrary start offset; its
    **span** (last − first) reproduces the lap time encoded in every ghost
    filename to a median 0.0023 s (max 0.034 s, 29/29 within 0.05 s; 23.59 s
    for shuffled pairings). x is longitudinal progress;
  - path-heading field follows its own x/z tangent (0.973 vs 0.086);
  - frame/path-record count ratio median 2.44, range 1.93–3.49;
  - `+32/speed` clusters near `.grb`-derived gear bands (p≈0.01); `+32/1024`
    is RPM-shaped (1177–5807 across 44,631 frames, 100% in 800–9000, lag-1
    0.992 vs ~0 shuffled), matching the live shared-memory RPM units;
  - `+16` (and ~99.9% of `+8`) lies in [-1,1], consistent with the normalized
    control ranges of the live shared-memory telemetry;
  - `path_f4` decreases with gear index (r −0.200 vs −0.005) — throttle-like;
  - `path_f3` rises mildly with racing-line curvature (median |r| 0.060 vs
    0.019 permuted) and with AIW-derived waypoint curvature (0.142 vs 0.068;
    14/27 files >2× baseline), consistent with a brake-like channel. Its
    associations with raw AIW attributes are all chance-level (|r| ≤ 0.046);
  - `path_f3`/`path_f4` are complementary normalized channels **at the frame
    level**: median correlation **−0.59** (vs −0.001 permuted), median
    `f3+f4 = 1.0`, and `f3 == 0` in 77% of frames — consistent with
    brake/throttle shares but not proven as pedals. At the *source path-record*
    level the relation is much weaker (median sum 0.85, r −0.136 vs 0.009
    permuted), so the frame values are not a verbatim record copy;
  - `path_f4` also tracks curvature (median |r| 0.072 vs 0.020, positive in
    23/29 ghosts) and AIW `galpha` (median |r| 0.276 vs 0.085 shuffled across
    27 ghosts) — associations, not simple pedal semantics;
  - `+48` low i16 tracks steering/path f3; high i16 tracks engine +32;
  - `+36` is an exact quantized float lattice (`±34·4^k`) whose exponent
    **tracks path f4** (median r 0.274 vs 0.016 permuted, positive in all 29
    ghosts) — a magnitude/demand relationship, not yet a decoded unit;
  - bytes `+24..+30` are a fixed marker `01 00 00 34 00 20 00` in all 44,631
    sampled frames; only byte `+31` varies. It tracks engine speed (median
    |r| 0.263 vs 0.021 permuted; 0.198 after removing ±2% clamps, 22/29 files
    above 3× baseline) and path y (0.164) — not merely a random exponent;
  - frame `+16` has a weak, non-clamp-driven engine coupling (|r| 0.152).
- **Corrected artefacts — never repeat these interpretations:**
  - `+8` ↔ `+16` correlation (0.675) collapses to 0.146 when `+16`'s ±1.0
    clamps are removed; it was a saturation artefact.
  - `+36` is not curvature, AIW galpha/width/index, or steering.
  - `+48` raw u32 is misleading; decode as two signed 16-bit halves.
  - `+40/+52/+56/+60` are at chance against kinematics.

### `.hat` header (gMb-wrapped track data) — verified 2026-12-01

The `.hat` body after `generated\x00` begins with a **16-byte header whose
bytes 4:16 are a per-track constant**. Across all 34 GTR2 `.hat` files:
- grouping by track name (15 groups), `body[4:16]` is identical in **24 of 28**
  within-track pairs; a seeded label permutation (1000 shuffles, seed 2026)
  gives mean 1.2 and max 6 matches — `p < 0.001`;
- the 4 mismatches are genuinely different physical layouts (Monza GP vs Jn,
  Hockenheim GP vs national/short), not contradictions;
- `body[0:4]` varies per file even within a track (10/28 matches), so the
  stable identifier is specifically the trailing 12 bytes.

Under `isi_crypt.crypt_info()` this block reads as a 16-byte signature/key
pair, but the derived signature is not in `GAMES` and no cipher is claimed.
The high 32 bits of the "key" (`body[12:16]`) and the f32 at `+8` are both
track-stable; earlier attempts to interpret them as CRC32/adler32/MD5 of the
track name failed.

The body after byte 4 is **deterministic per physical layout**, not salted
ciphertext: grouping all 34 GTR2 files by `body[4:]` yields 28 exact classes,
five of them multi-member (3 Donington, 2 ANDERSTORP, 2 Brno, 2 Magny,
2 Monza — 11 files). Within each class the entire remaining body (1.4–4.7 MB)
is byte-identical, e.g. `3Brno`/`4Brno` agree over 3,782,765 bytes and
`3Monza`/`4Monza` over 2,649,256 bytes. The earlier "high entropy" result
measured byte diversity, not per-file randomness. `body[16:36]` is a distinct
20-byte layout signature (17 values): it groups Dubai ×4, Donington ×3,
Magny ×3 (incl `NTMagny`), Oschersleben ×3, Valencia ×3 and pairs of
ANDERSTORP/Barcelona/Brno/Monza/Spa/NT+SH Hockenheim; its within-track
match rate is the same 24/28 (permutation mean 1.24, max 6).
Semantics of the blob remain undecoded; gMb keys and inner zlib streams are
still ruled out. Full-tier tests: `test_hat_header_bytes_4_to_16_are_track_stable`,
`test_hat_body_is_deterministic_per_layout`.
- **Negative — not a track-asset hash:** neither `body[4:8]` nor `body[12:16]`
  matches CRC32/adler32/MD5(lo/hi) of any of 1,669 candidate strings derived
  from the track name, `.hat` filename or actual asset filenames, nor of the
  contents of 408 files in that track's `Locations` folder. Raw u32 bytes in
  media files looked significant (9/15 tracks) but a distribution-preserving
  control (matching the zero-byte mask) gave 24.9/15 — the hits are coincidences
  in `.tga`/`.bik`/`.jpg` data. Full-tier test:
  `test_hat_track_id_not_a_track_asset_hash`.
- **Cross-game (GTL vs GTR2):** the 32-byte `body[4:36]` layout signature is
  identical for the same physical layout in both games — GTL `NANDERSTORP` and
  GTR2 `3ANDERSTORP`/`SANDERSTORP` all agree; GTL `MBNuerburgring` matches no
  GTR2 file. Seeded name-to-signature permutation: 2 observed co-occurrences
  vs mean 0.127 (1000 shuffles, seed 2026), `p = 0.003`. The bodies still
  diverge quickly (byte agreement from offset 36 falls from 27% in the first
  10 KB to ~1% later), so **no cross-game .hat body conversion rule** is
  claimed. Full-tier test: `test_hat_signature_is_cross_game_stable`.
- The same `body[4:36]` signature also exists in Race07's bare `Ver 0.08`
  variant: Race07 Anderstorp matches GTR2 Anderstorp, 41 Vanilla files form
  18 distinct signatures, and Race07Complete's 93 files form 43. Bodies are
  mostly deterministic per signature too (61/123 same-signature pairs fully
  byte-identical after byte 4). Full-tier test:
  `test_hat_signature_across_three_games`.
- **Decoded:** the 32-byte `body[4:36]` "signature" is four little-endian f64
  **spatial-grid parameters** ``(origin_x, inv_cell_x, origin_z, inv_cell_z)``,
  exposed as `media_tool.hat_grid_params()`. GTR2.exe's height-tree query at
  RVA `0x45de40` computes `ix = int((x-origin_x)*inv_cell_x)`,
  `iz = int((z-origin_z)*inv_cell_z)` and `bucket = ((ix<<5)+iz) & 0x3ff`
  (a 32x32 = 1024-bucket hash) before evaluating a quadratic height surface.
  For GTR2/GTL/Race07 all table records map into `ix,iz ∈ 0..31`; rF1/SCE
  layouts use 64x64 grids with correspondingly larger inverse cell sizes.
  Verified on all 178 local HAT files; 97.9% of sampled records fall inside
  the nominal grid extent (the rest are boundary samples). Grid extent is
  **not** a track-pairing discriminator: AIW waypoints fall inside a matching
  HAT's extent 11/11 times but also inside a mismatched one ~10.9/11 times, so
  no `validate_hat_track_pair()` rule is promoted. Full-tier test:
  `test_hat_signature_decodes_to_spatial_grid_params`.
- The body begins at offset 48 with a **fixed-stride 16-byte record table**:
  each record is `[f32 x, u32 unknown, f32 height, f32 z]` (B is a local
  elevation value — see below), with B roughly constant
  per layout (|B| 0.75–2.9) and A/C varying. Record counts span 7–61,412 and
  are identical across byte-identical bodies (5 multi-member classes, 11
  files); shuffling counts among files breaks that agreement (observed 5 vs
  permutation mean 0.125 / max 3, seed 2026). An 8-byte zero pair follows the
  table before a second stream. Field semantics remain undecoded. Full-tier
  test: `test_hat_body_starts_with_16_byte_record_table`.
  **Producer evidence:** `GTR2.exe` contains `..\Source\htree.cpp`, `Mb@`,
  `Ver 0.08 This file is automatically generated`, `.hat` and `HAT\` at
  adjacent RVAs around 0x670118, with the path builder at RVA 0x45e6d0
  (appends `HAT\`, track stem, `.hat`) and a spatial query using `QWORD`
  (double) transforms and a 3-element loop at RVA ~0x45b700 in `htree.cpp`.
  The name "height tree" and the query code support a spatial/terrain-index
  interpretation, but no full decoder is claimed. The dedicated server EXE
  retains the producer diagnostics ``Gaussian elimination for HAT poly failed
  once/twice`` and ``Build HAT database everytime tracks are loaded (for
  development purposes)``; its HAT writer at RVA ~0x45e430 emits the 46-byte
  version string, the u32 at object +0x1028, the four grid doubles, then the
  header counts (first from an external structure, second from function
  0x45b1d0), allocating 0x60- and 0x10-byte element arrays; the record count
  is computed by `0x459480`. The record loop (0x45e680) writes each 16-byte
  record from an array of pointers as `[4 bytes at ptr+0][8 bytes at ptr+0x18]
  [4 bytes at ptr+0x10]` — so the opaque u32 and the height float are adjacent
  fields of the runtime object, and records follow runtime list order rather
  than spatial order (consistent with the weak record-index/waypoint-index
  correlation). After the record table, `0x459610` builds 32-byte structures
  (96 = 3 x 32 bytes allocated per polygon) and `0x45c3d0` writes 8-byte
  prefixes of those structures plus variable linked-list metadata (chains of
  up to three nodes), so the trailing stream is variable-length — consistent
  with the lack of a fixed stride. The apparent 32-byte alignment of tail u32s
  (16.3% vs 3.2% for random bytes) disappears under a byte-shuffled control
  (16.6%), so it is a zero-byte-histogram artifact, not pointer evidence.
  Full-tier tests: `test_hat_producer_strings_in_dedicated_exe`,
  `test_hat_trailing_stream_is_not_plain_float_records`. Although 18 signatures are shared
  across games, the matching bodies are **not reusable**: GTR2 Brno has 40,189
  records vs Race07's 41,530 (3/40,189 records identical at the same index),
  and GTR2 Anderstorp 27,357 vs GTL's 27,185 (24/27,185). Full-tier test:
  `test_hat_record_tables_not_cross_game_reusable`.
  The body header declares **three u32 counts at offsets 36/40/44**
  (`media_tool.hat_declared_counts()`); the third is the authoritative record
  count, verified on **178/178** `.hat` files in 9 corpora (all three header
  variants). The first is the input polygon count `n`; the second is exactly
  `T(n)` from GTR2.exe's recursive bisection function `0x45b1d0`
  (`T(0)=0, T(1)=T(2)=1, T(n)=1+T(n//2)+T(n-n//2)` for `n>=3`), exposed as
  `media_tool.hat_bisection_count()` and verified on **178/178** files — no
  clamping is involved (values like 32767/65535 are genuine `T(n)` plateaus).
  The record count is computed by the quadtree node counter `0x459480`.
  The polygon count is not a waypoint-count proxy (r=0.35, p=0.098), but it
  does scale with the grid's covered area across 34 GTR2 layouts (r=0.553,
  seeded permutation p=0.001), consistent with area-driven tessellation.
  Full-tier test: `test_hat_polygon_count_tracks_grid_area`. `hat_record_count()` now uses the declared
  count: the old bounded scan stopped at valid records with `B = 0.0` and
  `U = 0`, undercounting 6/34 files (e.g. Enna 7,558 vs 15,417). Full-tier
  test: `test_hat_record_count_uses_declared_header_count`.
  The f32 triples are **not** AIW waypoint or CAM camera positions: Brno has
  40,189 records vs 1,304 waypoints, and zero records fall within 0.5 units of
  any AIW waypoint or CAM point (same for a shuffled control). Full-tier test:
  `test_hat_records_are_not_aiw_or_cam_positions`.
- The `(A, C)` pair is nevertheless **track-space coordinates**: median
  distance from a sampled record point to the nearest AIW waypoint *segment*
  is 18.2 m (Brno) and 6.2 m (Monza), versus 84.7 m / 96.5 m under a
  distribution-preserving shuffle of the C column (ratio 0.21 / 0.06). They
  are track-surface/boundary samples, not exact waypoints. Full-tier test:
  `test_hat_records_lie_near_track_polyline`.
  The remaining u32 is opaque: correlation with record ordinal is <0.012 in
  Brno/Monza/Dubai, and repeated `(x, z)` points carry different u32 values
  (0/93 duplicate pairs in Brno agree). Full-tier test:
  `test_hat_record_u32_is_not_a_counter_or_position_hash`. Reinterpreting it
  as a float in LE/BE, byte-swapped or sign-flipped form gives plausibility
  rates within 0.03 of random bytes. Information-theoretic check on 20,095
  Brno records: MI(u32, grid bucket) = 7.765 bits vs 7.740 for a shuffled
  control (spatially independent), while MI(height B, bucket) = 4.86 bits —
  a clean separation between an external identifier and a spatial field.
  Full-tier test: `test_hat_record_u32_is_spatially_independent`.
  Its value divided by 2^32 lies in [0,1]
  and its most frequent values match simple fractions (0.2/0.8 at Brno,
  0.75/0.25/0.5/0.125 at Monza), but there is no universal fixed-point step
  (<=5.4% land on 1/1024) and no correlation with normalized arc length or
  elevation; no decoder is claimed. Full-tier tests:
  `test_hat_record_u32_not_a_track_parameter`.
  B is also not AIW `wp_width` or groove width (r=0.11 / 0.24 across 14
  layouts, both below seeded permutation maxima). Full-tier test:
  `test_hat_field_b_not_a_track_width`.
- After the table's 8-byte zero terminator, the trailing stream is also
  non-random but harder to parse: byte-lag 8 agreement is 7.5–10.7% versus
  1.3–1.7% for a seeded shuffle, uniformly across 64 KB blocks, and the most
  frequent matching bytes are float exponent values (0x40/0xC0/0x3C…0x39).
  However no 8-byte phase yields a convincing run of plausible f32 pairs
  (~48% at every phase, same as random), so the stream is not plain packed
  floats. Full-tier test: `test_hat_trailing_stream_has_eight_byte_periodicity`.
  Stronger periodicity exists at **34- and 77-byte strides**: byte agreement
  11.2–16.3% (34) and 11.6–16.1% (77) across Brno/Monza/Enna/Dubai/Anderstorp
  versus ~1.4% for a seeded byte shuffle, with agreement spread fairly evenly
  across all phases of the period (not a single constant field). 43 and 87
  bytes are weaker companions (77 = 34 + 43). No fixed record layout has been
  derived from this yet: the per-phase consensus bytes are 0xC0/0x32 (float
  exponent bytes) and no exact 34- or 77-byte record template occurs, so the
  periodicity reflects repeated exponent values rather than a fixed record.
  Full-tier tests: `test_hat_trailing_stream_has_34_and_77_byte_periodicity`.
  The ~49% of 8-byte windows that decode as two plausible IEEE floats is fully
  explained by the tail's byte histogram (byte-shuffled control 48.5%), so no
  float-record layout is present.
- The table field B has only a **weak track-scale trend**, not a decoder:
  using all 32 GTR2 layout files (including duplicate byte-identical bodies)
  gives r=0.66 against AIW waypoint count, but deduplicating to 14 independent
  layouts gives r=0.495 (seeded permutation p~0.07), and 43 independent
  Race07 layouts give r=0.326 (p~0.04). Duplicates must be collapsed before
  significance testing. B's sign does not encode track direction (18/32
  agreement with AIW signed area, chance 0.56). Full-tier test:
  `test_hat_record_b_weak_track_scale_association`.
  **B is a local elevation value, however:** at a record's own `(x, z)` it
  correlates strongly with the nearest AIW waypoint's y — r = 0.65–0.93 on
  Brno/Monza/Magny/Dubai/Estoril/Imol, versus |r| < 0.1 after shuffling y
  among records. A circular-shift control (preserving spatial autocorrelation)
  has mean r ≈ 0. On flat Dubai the relationship is almost exactly affine
  (robust slope 0.0156, intercept 2.499, MAD 0.0003); on hilly layouts
  outliers arise where an adjacent road section lies directly above/below the
  sample. The scale is track-specific (slopes vary by >10x across layouts,
  with no z-score/min-max law), so no unit mapping is claimed. Full-tier test:
  `test_hat_field_b_tracks_local_elevation`.

## 5. HAT placement in converted trees

GTR2 ships every HAT asset under `GameData/Locations/HAT_Dedicated`; GTL uses
`UserData/LOG/HAT` and Race07 keeps them per-track. Since cross-game HAT bodies
are not byte-compatible, `validate_gtr2_tree()` flags any `.hat` outside
HAT_Dedicated as misplaced. Full-tier test: `test_hat_placement_validator`.

## 6. GDB class filters are not cross-era mappable

rF1-era GDBs carry `Filter Properties =` tokens describing **track/season
properties** (`srgrandprix`, `roadcourse`, `2005`, `lienz`, `nscrs`, ...);
across 39 sampled lines only 12 distinct tokens occur and none are `.veh`/`.hdv`
class tags. SimBin GDBs instead use `SpecialClasses` / filter blocks whose keys
resolve to local `.car` class tags (112/117 in an earlier 252-file sweep). The
two token sets overlap by <10%, and no GTR2/GTL GDB field carries the rF1 track
properties (only coincidental `2006` substrings in names/paths). Therefore
**no rF1→SimBin GDB class-mapping rule is derivable** and none is implemented;
a superficial string mapping would be wrong. Full-tier test:
`test_rf1_gdb_filter_properties_not_simbin_car_classes`.

## 7. Vertex `f0` (per-mesh marker on vertex 0)

- **GSC conversion normals** are derived and essentially always unit vectors:
  2 of 130,855 sampled vertices (0.0015%) are zero-length, both in
  `CRU_EXT_PARTS_A.GMT` at symmetric positions (likely degenerate source
  triangles). Full-tier test: `test_gsc_conversion_normals_are_unit`.
- f0 is **preserved from the GMT**, not assigned by GTR2.exe; the shader
  helpers use a small 1/2/3/99 stage-type enum, and there are only 94 shipped
  `.psh`/`.vsh` names — too few for f0's >1,000 values.
- Verified structure (all with distribution-preserving permutation baselines):
  - halves are near-equal: `|high-low| <= 1` in 49.2% vs 1.4% permuted;
  - each half is separately family-stable (16.3% / 17.3% vs 0.2% / 0.5%);
  - half-sign is family-stable (53.4% vs 18.4%) and skewed negative for
    material/mesh slot 0;
  - half-delta and half-sum inversely track mesh ordinal (r −0.21 / −0.26);
  - **methodology trap:** `split_f0()` returns the ABSOLUTE halfword delta;
    a "high half is never below low half" invariant was an artifact of using
    that helper. Raw signed high-minus-low is mixed (~42% positive, ~55%
    negative). Full-tier guard: `test_f0_split_delta_is_absolute_not_signed`.
  - **mesh 0 is structurally distinct**: median halves 542/678, delta 314 vs
    later meshes 63/63, delta 1; its half-sum also tracks GMT mesh count
    (r≈0.13) and member size (r≈0.16) vs ~0.009 permuted.
  - **Cross-game preservation:** across 2,589 same-length GTR2/GTL meshes with
    identical names, 2,261 (87.3%) have identical f0 values for **all
    submeshes at index >= 1** (permutation mean ~5 matches); in 1,311 of those
    only mesh 0 differs. No simple constant transform explains the mesh-0
    change (287 distinct XOR values in 462 pairs). So the marker is
    authoring-state preserved across games for later meshes, with mesh 0
    game-specific. Full-tier test:
    `test_f0_preserved_cross_game_except_first_submesh`.
- **Terminology correction:** `material_index` equals the mesh ordinal in
  99.97% of meshes; all "material index" findings are really mesh position.
- f0 is strongly associated with material identity (raw-material-equal groups
  show P(f0 equal) 0.347 vs 0.036) but no tested name/record hash reproduces it.
  **Working hypothesis only (not established):** an external authoring
  identifier. Decoding it is not required for conversion as long as the word is
  preserved byte-for-byte.
- **Byte-level structure:** in 69.6% of 30,000 sampled markers both u16 halves
  are byte-sized (bytes 1 and 3 are zero), so the real payload is byte 0 and
  byte 2. Those two bytes are usually **consecutive integers**: for an even
  low byte, `high == low + 1` in 60.3% of markers vs 0.8% under a
  distribution-preserving shuffle (odd low bytes most often pair with
  `low - 3`). f0 is therefore a pair of small structured IDs, not a hash.
- **Tested and rejected** (all with distribution-preserving controls where
  applicable): material index (a mesh-0 artefact), material stage indices,
  geometry CRC, material-name/record hashes, shader registry indices, shader
  type enums, material name/stage/string lengths, object-list-offset and file
  bytes, MOS 8-bit element counts, CRC32/sum of the GMT member filename,
  exact f0 u32 reuse in material records (matches were trivial sentinel/ASCII
  values), printable-ASCII reinterpretation of the u32 (1.2% of markers), and
  8-bit slices of hashes of material names / stage strings (`sum`, CRC32, MD5 —
  all at the distribution-preserving expectation, e.g. 47 vs 46.7 expected).
  The reverse association is weak but real: across 16,547 GTR2 markers,
  equal-f0 pairs share an exact material name only 6.7% of the time (vs 0.29%
  shuffled) but share a 3-character material-name prefix 18.8% (vs 3.5%) — a
  family-level association, not a material ID. Full-tier test:
  `test_f0_predicts_material_family_weakly`. CRC16-CCITT and CRC16-IBM of
  material names and stage strings hit f0 bytes at ~0.6% (chance 0.78%), so
  those hash families are also ruled out, as is indexing the material's stage
  strings (hit rate 0.77%, at chance). The cross-family scope is also
  constrained: f0 byte semantics differ in JCA-encrypted Volvo/Race07 GMTs.
  See `docs/open-issues-research.md` for each experiment.
- Tooling: `gmt_format.split_f0()`, `gmt_format.f0_byte_pair()`, `gmt_tool.py info --meshes` and
  `gmt_tool.py f0 FILE` (with invariant warnings). `validate_conversion.validate()` now guards
  byte-exact f0 preservation too (30/30 sampled old→new conversions; metamorphic test flips one
  marker and the report fails).

## 8. `PHYSICS.PHS`

- Five PHS members in GTL `.gtl` archives: four PAR2 `Main`/`RecvSlic` chains,
  one opaque blob. Slice size 384,000; only **3** recovery slices (exponents
  53/58/59) vs ~160 needed for the 61 MB GTL 1.1 updater — reconstruction is
  mathematically insufficient.
- No shipped GTL/GTR2 binary references PHS; GT Legends 0.9.01 updater was not
  found in local mirrors or accessible web sources. Explicitly blocked.

## 9. Methodology rules learned the hard way

1. Prefer the producer/consumer code over more byte statistics; but packed EXEs
   can make this impossible — record the blocker, don't fake it.
2. **Permutation baselines must preserve the observed distribution.** A uniform
   shuffle created a false f0/material-index signal.
3. Remove saturation/clamp frames before claiming a control-field correlation;
   several "steering" results were clamp artefacts.
4. Structural validity ≠ geometric correctness: always apply
   `read_gsc_geometry()` quality gates.
5. Correct superseded claims in place and keep the old log for provenance;
   never silently rewrite history.

## 10. Verification

- Converted GSC→GTR2 GMTs were validated against the independent
  `gtr2-agent-tools` GMT reader (runtime reference only, no code copied):
  20/20 real and converted samples agree on mesh/vertex counts and exact
  triangle lists (17,588 converted faces); GTR1 conversions validated likewise.
  `batch_convert.py` additionally compares GSC source and output UVs byte-for-byte
  (60/60 sampled members) before writing a converted GMT. A full-tier test uses that parser when the
  reference tree is present.
- `validate_conversion.independent_read()` uses only the published field-offset
  schema; with its early `break` removed it finds exactly the same submeshes as
  `gmt_semantic` on 100/100 sampled conversions. `validate()` now cross-checks
  **all** submeshes' positions, UVs and exact triangle lists against that
  independent read, and a metamorphic test verifies that flipping a triangle
  index in the second submesh fails the cross-check. Full-tier tests.
- Tests: `python3 run_tests.py --mode quick|normal|full`; quick tier is kept
  under its budget (20 modules / ~30 s). Normal tier 270 s / 266 tests /
  0 failures, below its 300 s budget; two corpus-wide tests were moved from
  quick-tier modules to full tier to restore the budget.
- Safety: `python3 pre_push_check.py` before any push; no push without explicit
  authorization.
- Full suite evidence is recorded in `CHANGES.md` with its starting commit
  caveat; targeted experiments have their own full-tier regression tests.
