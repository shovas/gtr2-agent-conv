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
- `gmt_layout.is_old()/is_new()` detect layouts; `old_to_new_semantic()` rebuilds
  a new-layout mesh from decoded old-layout geometry.
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
  distribution-preserving shuffle. `gmt_format.uv_tiling_factors()` exposes it.
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
  same container at version **1.01** (vs GTR2's 1.05); all four local GTL
  `.Vcr` files parse and rewrap byte-identically.
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
  byte-identical (50/50 sampled).
- All nine shipped `.Vcr` replay files parse with the same reader: gzip +
  gMb wrapper + `IRSR` v1.05, with driver/car/team names and session values
  from the same 36000/43200/46800 set. The GTTF-specific frame-grid detector
  does **not** find their frames (no `01 00 00 34 00 20 00` marker), so their
  frame layout remains a separate, undecoded format. The payload does have a
  an **86-byte period confined to the header region** (first ~0x2000 bytes;
  byte-match 0.78 at lag 86 vs chance, harmonics at 172/258/344). The bulk
  frame data has no 86-byte structure (0.04–0.06 match), so this is a header
  table rather than the frame grid. Earlier 4-byte-aligned stride scans also
  missed 86 because it is not a multiple of 4. Frame semantics remain
  unknown. Bulk data shows a separate **20-byte lag excess** over neighbouring
  lags in 7/9 replays (median +0.16 matching bytes), consistent with a small
  repeating record, but no monotonic time field was found at that stride.
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
  - `+32/speed` clusters near `.grb`-derived gear bands (p≈0.01);
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

## 5. Vertex `f0` (per-mesh marker on vertex 0)

- f0 is **preserved from the GMT**, not assigned by GTR2.exe; the shader
  helpers use a small 1/2/3/99 stage-type enum, and there are only 94 shipped
  `.psh`/`.vsh` names — too few for f0's >1,000 values.
- Verified structure (all with distribution-preserving permutation baselines):
  - halves are near-equal: `|high-low| <= 1` in 49.2% vs 1.4% permuted;
  - each half is separately family-stable (16.3% / 17.3% vs 0.2% / 0.5%);
  - half-sign is family-stable (53.4% vs 18.4%) and skewed negative for
    material/mesh slot 0;
  - half-delta and half-sum inversely track mesh ordinal (r −0.21 / −0.26);
  - **mesh 0 is structurally distinct**: median halves 542/678, delta 314 vs
    later meshes 63/63, delta 1; its half-sum also tracks GMT mesh count
    (r≈0.13) and member size (r≈0.16) vs ~0.009 permuted.
- **Terminology correction:** `material_index` equals the mesh ordinal in
  99.97% of meshes; all "material index" findings are really mesh position.
- f0 is strongly associated with material identity (raw-material-equal groups
  show P(f0 equal) 0.347 vs 0.036) but no tested name/record hash reproduces it.
  Treat it as an **external authoring identifier**; do not invent semantics.
- **Byte-level structure:** in 69.6% of 30,000 sampled markers both u16 halves
  are byte-sized (bytes 1 and 3 are zero), so the real payload is byte 0 and
  byte 2. Those two bytes are usually **consecutive integers**: for an even
  low byte, `high == low + 1` in 60.3% of markers vs 0.8% under a
  distribution-preserving shuffle (odd low bytes most often pair with
  `low - 3`). f0 is therefore a pair of small structured IDs, not a hash.
- Tooling: `gmt_format.split_f0()`, `gmt_format.f0_byte_pair()`, `gmt_tool.py info --meshes` and
  `gmt_tool.py f0 FILE` (with invariant warnings).

## 6. `PHYSICS.PHS`

- Five PHS members in GTL `.gtl` archives: four PAR2 `Main`/`RecvSlic` chains,
  one opaque blob. Slice size 384,000; only **3** recovery slices (exponents
  53/58/59) vs ~160 needed for the 61 MB GTL 1.1 updater — reconstruction is
  mathematically insufficient.
- No shipped GTL/GTR2 binary references PHS; GT Legends 0.9.01 updater was not
  found in local mirrors or accessible web sources. Explicitly blocked.

## 7. Methodology rules learned the hard way

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

## 8. Verification

- Tests: `python3 run_tests.py --mode quick|normal|full`; quick tier is kept
  under its budget (currently 20 modules / ~27 s).
- Safety: `python3 pre_push_check.py` before any push; no push without explicit
  authorization.
- Full suite evidence is recorded in `CHANGES.md` with its starting commit
  caveat; targeted experiments have their own full-tier regression tests.
