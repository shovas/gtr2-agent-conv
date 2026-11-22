# Open issues — offline research record (2026-11-23)

All work here is **offline**: no game was launched. "Runtime-dependent" means
conclusively establishing it requires actual game execution.

## 1. In-game validation alternatives
- **Understanding/confidence**: structural validation existed; runtime correctness unproven.
- **Hypothesis**: exact semantic equality between source and converted geometry, plus an independent parser cross-check, provides strong offline compatibility confidence.
- **Experiment**: `validate_conversion.validate()` compares positions, UVs, faces and material tail, and re-reads the converted file with an independent schema-offset reader. 100/100 converted rF1 GMTs pass every check.
- **Evidence**: `tests/test_validate_conversion.py` (2 tests), corpus probe `converted 100 pass 100`.
- **Added**: `validate_conversion.py`, tests, README/CAPABILITIES entries.
- **Remaining**: actual GTR2 rendering is **runtime-dependent**.
- **Next**: independent renderer comparison (PIL wireframe) if visual confidence is needed.
- **Classification**: **Partially resolved** (offline confidence high; runtime unverified).

## 2. GMT bridge semantics
- **Understanding/confidence**: 552 same-name old/new pairs had no geometry match (71 same vertex count, but different meshes).
- **Hypothesis**: rather than finding ground truth, prove the bridge is a lossless semantic transform.
- **Experiment**: exact array equality of decoded positions/UVs/faces on 100 converted GMTs.
- **Evidence**: 100/100 exact; material tails byte-identical; independent reader agrees.
- **Remaining**: whether GTR2 renders those semantics identically is **runtime-dependent**.
- **Classification**: **Partially resolved** (transform proven lossless; in-game semantics unverified).

## 3. Residual fields
- **GTTF frame fields**: cross-file analysis of 12 files found slot +12 is heading in radians (-pi..pi in every file) and +16 a small angle. `read_frames()` now exposes both; other slots are zero or uninterpreted. **Partially resolved**.
- **FXM key_count**: all 148 node records across 91 files have value 3; meaning still unconfirmed (likely a fixed channel/version marker). **Unresolved**.
- **GMT f7**: ARGB vertex colour — 0xFFFFFFFF in 52,176/53,082 vertices; other values 0xFFA0A0A0 etc. are grey tints. **Resolved**. `f0` remains unconfirmed (zero in ~99%).
- **CUBE MTS per-rig tables**: 4 distinct shared tables across 22 files (9 pit crew, 8 R_ARM/R_TGT, 4 L_ARM, 1 JET); interpretation as rig/skeleton IDs stands, exact semantics **unresolved**.
- **PHYSICS.PHS**: 13 KB opaque blob with no PAR2 packets; **unresolved**, low value (recovery artifact context).

## 4. GTR (2004) corpus
- **Correction**: `../GTR1Vanilla` **is installed** (3,613 files) — earlier task-plan claim was stale and has been fixed.
- **Hypothesis**: GTR1 uses a 48-byte vertex record.
- **Experiment**: tested strides 32/48/64 against unit-normal constraint; 48 gave 40/40 unit normals, others ~50%.
- **Evidence**: `gmt_semantic.read_gtr1_vertices()`; 5,024/5,024 normals unit length across 53 files.
- **Added**: function + test; docs updated.
- **Remaining**: extra 16 bytes per vertex, descriptor variants for 127+ files with zero first count. **Partially resolved**.

## 5. PHS runtime consumer
- **Hypothesis**: GTL contains a PHS/PAR2-aware loader.
- **Experiments**: radare2/strings over `GTL.exe`, `GTLDedicated.exe`, `GTLConfig.exe`, `GTLReporter.exe` and all DLLs: **no** `.phs`, `PAR2`, `RecvSlic`, `FileDesc`, `Update_0901` strings. Source-path strings show an ISI "Cobra" engine with chunk processors (`PhysicsInfoChunkProcessor1`, `MeshChunkProcessor*`) but no PHS module. Wine runtime trace blocked earlier by missing MFC42.dll.
- **Evidence**: static scans recorded in `docs/phs-research.md`.
- **Interpretation**: no evidence of a PHS consumer; consistent with unused update artifacts. Absence of literals is not proof (loader could use hashes/indices).
- **Remaining**: consumer confirmation is **runtime-dependent**.
- **Classification**: **Runtime-dependent** for confirmation; resource identity resolved.

## Second-pass experiments (same session)

- **FXM `key_count`**: tested 3×28-byte keys (pos+quat) across all 148 node records —
  **0/148** yield unit quaternions, while the established 2×40-byte TRS layout yields
  **148/148**. So `key_count==3` definitively does **not** denote the number of
  keyframes; it is a fixed field (likely channel/version marker). Negative result
  codified in `tests/test_fxm_records.py`. **Unresolved meaning, wrong interpretation excluded**.
- **GMT `f0` — RESOLVED as marker**: non-zero in only 0.36% of 108,878 vertices,
  and **all 302 non-zero cases occur at vertex index 0** of a mesh. It is a per-mesh
  first-vertex marker/flag, not a per-vertex attribute. Added test.
- **CUBE MTS rig tables — RESOLVED (geometry decode corrected)**: the 36-byte table records are indices/materials, not positions (embedded `NASCAR_FACE` name). Real float streams are located by the table+48 descriptors; `read_geometry()` now decodes those as 64-byte-strided records and restores the `vertices` field (1,561 points). `rig_table_triangles()` proves all 79/79 per-rig triples index descriptor 0 with edge median 0.657. **Partially resolved** (geometry decoded and validated; exact semantic role unknown).
- **GTTF frame slots 7/9**: u32 bit patterns have constant low 16 bits (slot 7 =
  `0x2000`, slot 9 = `0x0000`) across files, suggesting quantized/fixed-point fields.
  Correlated slot 7's high byte against speed from position deltas: r=0.34, and the
  value *lags* the speed (e.g. speed rises 2→110 km/h while slot7-adjusted rises
  33→54) — a smoothed/delayed quantity, not direct speed. Slot 9 shows no speed
  correlation (|r|<0.1). Exact meanings **unresolved**.
- **GTR1 extra 16 bytes — RESOLVED**: always `[0, u, v, 0]` (zero padding + 2D float UV pair),
  confirmed across 2,215 vertices in 100 files. Added as `uv` field in `read_gtr1_vertices()`.
- **GTR1 descriptor variants**: 22,287 GMTs lack the 0x194 grid. Resolved the gap:
  all GTR1 GMTs carry a universal rF1-style 8-u32 table at **0x11c** (20,000/20,000 valid),
  with 32-byte vertex stride. Car meshes additionally have the 0x194 grid. Added
  `gmt_semantic.read_gtr1_table()` + test. **Partially resolved** (table semantics known,
  extra columns unconfirmed).

## Metamorphic validation (issues 1+2)

- **Experiment**: perturb one source vertex x by +1.0 in a real rF1 GMT, re-convert,
  and compare decoded output positions. Result: exactly vertex 0 changes, by
  exactly +1.0. Codified in `tests/test_validate_conversion.py`.
- **Third-party oracle**: the pure parsing functions of the GPLv3 Blender GTR2/rF1
  GMT importer were executed in /tmp (not committed) against a converted GMT.
  Its positions matched ours exactly (after its Blender Y/Z swap), and its UVs
  matched exactly after undoing its V-flip. This is an independent implementation,
  not our own reader.
- **Interpretation**: the bridge is a genuine per-vertex semantic transform confirmed
  by an independent implementation. Strengthens offline compatibility confidence.

## Recommendation
No issue is fully runtime-resolved without launching GTR2/GTL. The highest-value
offline work is complete: a reusable offline validator, exact semantic-bridge
proof, and several decoded residual fields. Defer further PHS/runtime work; pursue
GTR1 descriptor variants and MTS rig semantics only if new evidence appears.
