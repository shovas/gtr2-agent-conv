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
  preserved (raw 32-byte vertex records are copied, not rebuilt).
- **Winding:** GSC, rF1 old-layout and GTR2 target meshes all show *inverted*
  face winding relative to stored normals (cross-product agreement ~0 forward,
  ~1 reversed). Do **not** flip indices during conversion.
- `batch_convert.py` includes a `gsc` family; all written meshes are re-parsed
  and pass `validate_materials.check_gmt()`.
- **Open gap:** sampled GTR2 meshes expose no 16-byte extra UV vertex block, so
  transferred old-layout UVs cannot be validated with the current parser. No
  UV correctness claim is made.

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
- Header fields after filenames: `u8, u8, f32, u8, u32`; the f32 is one of
  **36000/43200/46800** (10/12/13 h in seconds — strong inference) across 42
  files. Exposed as `EventFile.session_seconds` etc.
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
  - frame `+20` (time) tracks path x (|r| 0.568 vs 0.017) — x is longitudinal progress;
  - path-heading field follows its own x/z tangent (0.973 vs 0.086);
  - frame/path-record count ratio median 2.44, range 1.93–3.49;
  - `+32/speed` clusters near `.grb`-derived gear bands (p≈0.01);
  - `path_f4` decreases with gear index (r −0.200 vs −0.005) — throttle-like;
  - `path_f3` rises mildly with racing-line curvature (median |r| 0.060 vs
    0.019 permuted), consistent with a brake-like channel;
  - `path_f3`/`path_f4` are complementary normalized channels: median correlation
    **−0.59** (vs −0.001 permuted), median `f3+f4 = 1.0`, and `f3 == 0` in 77% of
    frames — consistent with brake/throttle shares but not proven as pedals;
  - `path_f4` also tracks curvature (median |r| 0.072 vs 0.020, positive in
    23/29 ghosts) — an association, not a simple throttle interpretation;
  - `+48` low i16 tracks steering/path f3; high i16 tracks engine +32;
  - `+36` is an exact quantized float lattice (`±34·4^k`) whose exponent
    **tracks path f4** (median r 0.274 vs 0.016 permuted, positive in all 29
    ghosts) — a magnitude/demand relationship, not yet a decoded unit;
  - bytes `+24..+30` are a fixed marker `01 00 00 34 00 20 00` in all 44,631
    sampled frames; only byte `+31` varies and it tracks path y (median |r|
    0.164 vs 0.020 permuted) — not merely a random exponent;
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
- Tooling: `gmt_format.split_f0()`, `gmt_tool.py info --meshes` and
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
