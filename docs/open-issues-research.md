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
- **GMT f7**: ARGB vertex colour — 0xFFFFFFFF in 52,176/53,082 vertices; other values 0xFFA0A0A0 etc. are grey tints. **Resolved**. A full 8,109-file sweep confirms the semantic bridge is lossless offline (8,109/8,109), while the structural bridge is deliberately non-lossless. `f0` was also resolved later as a
per-mesh first-vertex marker (see Second-pass section); this first-pass entry is superseded.
- **CUBE MTS per-rig tables**: 4 distinct shared tables across 22 files (9 pit crew, 8 R_ARM/R_TGT, 4 L_ARM, 1 JET). Later work showed the triples form coherent disk-like triangle surfaces (chi=1), supporting a geometric role; exact semantics **unresolved**.
- **PHYSICS.PHS**: 13,064 bytes, no PAR2 magic/packets, no repeated 8-byte blocks (1,632 unique of 1,632), overall entropy 7.986. One slightly-low-entropy 512-byte window at 0x3200 (7.12) but no recognizable structure. XOR entropy vs the other four is ~7.8 over 1,024 bytes (the ~7.1 figure from 256-byte samples was a small-sample artifact) — no shared keystream. Tested zlib/raw-deflate/gzip/bz2/lzma at every bit shift (1..7) of the full file with byte offsets 0..127 — no decompression. XOR autocorrelation at periods 2..1024 gives match rates 0.0033..0.0047 (random baseline 0.0039) — no periodic key. Plausibly a truncated PAR2 recovery slice for the same `GTL_Update_0901.exe` set (the other four are PAR2 containers for it); **unresolved**, low value.

## 4. GTR (2004) corpus
- **Correction**: `../GTR1Vanilla` **is installed** (3,613 files) — earlier task-plan claim was stale and has been fixed.
- **Hypothesis**: GTR1 uses a 48-byte vertex record.
- **Experiment**: tested strides 32/48/64 against unit-normal constraint; 48 gave 40/40 unit normals, others ~50%.
- **Evidence**: `gmt_semantic.read_gtr1_vertices()`; 5,024/5,024 normals unit length across 53 files.
- **Added**: function + test; docs updated.
- **Remaining**: none of the originally listed gaps — extra bytes resolved as UV pair and descriptor-less variant decoded (see Second-pass section). **Resolved**.

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
  **148/148**. Both quaternion-first and position-first 3×28 alignments were tested
  (0/138 either way), so no 3-key layout fits. Also tested 3×28 with derived quaternion
  w (`w=sqrt(1-x²-y²-z²)`) — 0/138 valid. `key_count==3` is a fixed field (likely
  channel/version marker), definitely not a key count. Negative result codified in
  `tests/test_fxm_records.py`. Also verified nodes are contiguous: all 57 transitions
  have zero gap and span exactly `name_len+96` (fixed 84-byte keyframe block), so
  `key_count` cannot imply variable-length records. The 84 bytes decode as **2 TRS
  keys** (pos/quat/scale each) + 4-byte trailer; a plausible reading is that `3`
  counts the TRS *components* per key, but this cannot be confirmed offline.
  **Unresolved meaning, several wrong interpretations excluded**. A general regex
  scan across 604 files found 6,472 key_count=3 candidates plus 63 false positives
  (the `Mar  1 2005` FXM build timestamp and DDS texture bytes), confirming 3 is the
  invariant for real animated nodes. Separately, some FXM files (e.g.
  `FPDRIVER_Vectra-SteerL_01.FXM`, `LMA ` magic) use NUL-terminated node names with
  no marker/key_count fields — a distinct FXM variant. **Resolved**: `fxm_tool.parse_nul_name_nodes()`
  decodes it: `name\0`, 40-byte header, single 40-byte TRS key (pos/quat/scale), 12-byte
  trailer `(1,0x50,1)`; the parser now tries keyframe offsets (40,80,44,76) to also
  handle wiper files (offset 80, trailer `(0,0xb8,1)`). Validated on 69/79 nodes in the
  driver file and **160/160** `LMA `-magic files parse; added tests. Broadened the
  general scan to all file types (exe/bik/dds): every non-3 key_count value was a false
  positive (x86 opcodes, Bink audio header, DDS pixels). No genuine animated node has
  key_count != 3 across 6,472 candidates. Extended to 13 more corpora (Automobilista,
  F1C, F1 2000/01/02, NascarSimRacing, StockCarExtreme, GameStockCar, NT2003/04,
  SportsCarGtUsa, Copa, RF1Vanilla): **zero** genuine FXM nodes — they predate FXM;
  all regex hits were false positives.
- **GMT `f0` — RESOLVED as marker**: non-zero in only 0.36% of 108,878 vertices,
  and **all 302 non-zero cases occur at vertex index 0** of a mesh. It is a per-mesh
  first-vertex marker/flag, not a per-vertex attribute. Added test.
- **CUBE MTS rig tables — RESOLVED (geometry decode corrected)**: the 36-byte table records are indices/materials, not positions (embedded `NASCAR_FACE` name). Real float streams are located by the table+48 descriptors; `read_geometry()` now decodes those as 64-byte-strided records and restores the `vertices` field (1,561 points). `rig_table_triangles()` proves all 79/79 per-rig triples index descriptor 0 with edge median 0.657. **Partially resolved** (geometry decoded and validated; exact semantic role unknown). New evidence: the
triples form coherent triangle **surfaces** — the shared 79-triangle pit-crew table has 68 vertices,
146 edges (91 shared twice, 55 boundary), Euler characteristic V-E+F=1 (a disk); larger rig tables have
chi=31. This rules out arbitrary index triples and supports a geometric surface role (collision/deformable
patch), but does not identify the exact engine-side use. Further refinement: the 68 patch vertices are
  **strictly planar** (all x=0, extent 0 x 3.23 x 1.76 for TIREMANFRONT; 0 x 3.27 x 1.77 for
  PITOFFICIAL), so these are planar 2D triangulations (silhouette/shadow/collision-profile like) rather
  than volumetric 3D surfaces. Codified in `tests/test_mts_format.py`.
- **GTTF frame slots 7/9**: u32 bit patterns have constant low 16 bits (slot 7 =
  `0x2000`, slot 9 = `0x0000`) across files, suggesting quantized/fixed-point fields.
  Correlated slot 7's high byte against speed from position deltas: r=0.34 raw,
  r=0.40 if the high u16 is interpreted as float16 (0.01..256 range). The value
  *lags* speed — a smoothed/delayed quantity, not direct speed. Slot 9 shows no
  speed correlation (|r|<0.1). Tested as a steering field: correlation with per-frame
  heading change |r|<0.19 across 8 files — **excluded**. Across 10 trials, slot 7
  (float16) correlates weakly with speed (mean r=0.14), essentially not at all with
  acceleration (0.005) or curvature (-0.02) across 10 trials — a smoothed speed-like
  quantity. The published rF2 VCR format packs steer/throttle/RPM into u32 bitfields
  (`rpm=v>>18`, `throttle=(v>>11)&63`, `steer=v&127`); applying that to slot 7 yields
  "RPM" 2,048–6,016 correlating with speed (r=0.15–0.34 across 6 trials). **Definitively
  excluded**: across 1,500 samples steer is always 0 and throttle always 4 (artifacts
  of the constant low-16 bits `0x2000`), so the rF2 bitfield layout does not transfer.
  Also tested slots 6-18 as X/Y/Z rotation triples: no unit-norm triples, so the rF2
  driver-event layout does not map onto GTL's 63-byte ghost frames.
  ISI crypt with all game keys + name-derived keys and skips 0..32 gives
  printability 0.375 -> 0.438 (no valid decrypt). Structurally, slot 9's low 16
  bits are zero in 100% of frames across all files (1437/1437), i.e. a float quantized
  to 16-bit granularity (~43 distinct high-16 values, e.g. ±8.5, ±35, ±136) — a coarse
  control value, not a raw angle. Slot 7's high byte takes ~50 distinct values but with a
  median run length of 1 (changes nearly every frame) — not a discrete gear/throttle
  plateau. No 2-byte small-integer fields (gear/flags) found; only time is monotonic.
  FXM `size_hint` (94-100, mostly 96) was tested as a variable keyframe-record length: in a file with
  six different hints, all 22 nodes still have fixed 84-byte keyframes with zero inter-node gaps, so it
  is not a length field. Codified in `tests/test_fxm_records.py`.
  Focused online search found **no** GTL/GTR2 `.gtt` parser or format spec (results were
  modern Gran Turismo telemetry, unrelated). The local `gtr2-memory-operations-tool-wpf`
  `Gtr2VehicleTelemetry` struct documents GTR2 in-memory telemetry (plain-float
  throttle/steering/RPM, 3x3 orientation matrix) — no authoritative `.gtt` file layout.
  Tested the 63-byte frame for an orthonormal 3x3 orientation matrix: none found, so the
  ghost frame is a compact subset, not a raw telemetry dump. However, the recorded slot-12
  heading is **cross-validated**: heading derived from consecutive position deltas
  (1.608 rad) matches the frame's heading values (1.583/1.615 rad). The local
  `gtr2_driving/telemetry.py` reference documents GTR2 in-memory fields (pos@140, vel@152,
  gear@240, RPM@244) — a separate layout.
  Byte-level profiling of GTR2 GTT frames (1,512 samples) shows the field at +28 is
  **`00 20 00` constant in bytes +28..+30, with only byte +31 varying** (0x3F–0x41 in one
  file, 0x1F–0x71 across the corpus). Slot 7 is therefore a packed integer-like value,
  **not a float** — the earlier float reading (values near powers of two) was an artifact
  of the fixed low bytes. Its correlation with position-derived speed is weak and
  inconsistent (r=0.03–0.30 across 6 trials), as is the neighbouring byte +32
  (r=0.05–0.31, sign varies). An RPM-like sawtooth is not confirmed.
  Independently, the reference-only `gtr2-agent-tools/gtr2-accel-challenge.py` documents 63-byte ghost
  records marked by `01 00 00 34 00 20 00 40` at 20 Hz; in GTT the marker is at +24 with a varying
  trailing byte (0x3F-0x41), and its 7-byte prefix count matches the parser frame count 29/29.
  **Offset reconciliation**: in GTT the car-position floats are at marker−24/−20/−16 within the same
  63-byte record (equivalently marker+39/+43/+47 of the preceding record), whereas the reference `.dsi`
  loader reads them at marker+35/+39/+43 — a 4-byte phase shift between the `.dsi` and `.gtt` layouts.
  Direct inspection of 180 local `.dsi` files confirms both use 63-byte records with the same marker, but
  `.dsi` places **four** floats between position and the marker (offsets +12/+16/+20/+24, values
  approx. {small angle, heading, small angle, time-like}) whereas GTT has **three** (heading at +12,
  small angle at +16, time at +20). The extra field explains the 4-byte shift. Applying the reference
  offsets to GTT yields nonsensical values (e.g. −514 for x), so the two formats are structurally
  related but not byte-identical. **Post-marker alignment RESOLVED**: aligning both formats by the marker
  (marker at relative +0) and comparing per-byte statistics (zero fraction, mean, std) over +8..+62 for
  all 68,774 `.dsi` records and 44,602 `.gtt` frames gives a best lag of **0** with score 2.938/3.0
  (lag 4 scores only 0.357; mean |Δzero-frac| = 0.014 across 55 positions, with the single clear exception
  of marker+12 where DSI has extra data). So the **4-byte shift is confined to the pre-marker region**
  (position-to-marker 35 bytes in DSI vs 39 in GTT); the post-marker packed fields share one layout, and
  DSI files supply 68,774 additional samples for them. Reproducible via `ghost_align.py`; codified in
  `tests/test_simbin_events_tool.py`. Using those samples, DSI bytes at marker+16/+18/+20/+22 correlate
  ~0.63 with consecutive-position step distance, but the corresponding 4-byte float readings correlate
  ~0 — reinforcing that these are packed-byte fields, not little-endian floats. The shared marker+7 byte
  is strongly peaked at 64 (43% of 5,877 DSI samples, range 39–87 — a bias-64 signed byte) but correlates
  ~0 with both step distance and heading rate, so it is not speed or steering. Further fresh hypotheses all
  excluded: no correlation with acceleration (r=-0.02), position coordinates (|r|<0.14) or heading (r=-0.01);
  not a byte-XOR/sum checksum of position floats (0.3% chance-level matches). Slot 7 autocorrelation decays
  smoothly from r=0.995 at lag 1 with a +0.176/frame trend (a continuous signal, not a periodic counter);
  correlation with heading curvature (13,528 samples) is r=-0.012. A lattice search over 15 scales x 3 biases
  against DSI heading/pitch/time found no exact fixed-point quantization for any packed byte (best 52%, driven
 A lagged cross-correlation with speed (10,527 samples, lags -10..+10) peaks at only |r|=0.137, so slot 7 is not a delayed speed signal. Frame-to-frame deltas of slot 7 also show no correlation with acceleration (r=0.003) or heading-rate (r≈0, 9,011 samples). Across 44,631 GTT frames the byte is bimodal: 63-68 (clean high bit) and 191-196 (high bit set) — sign-magnitude-like with the same low 7 bits; the split varies within files, so it is not a per-file constant.  by constant values). Its exact meaning remains **unresolved**.
  A 17,392-frame test appeared to show within-file slot-9/pitch correlation r=0.687, but that is an artifact:
  the byte is 0 in ~all frames with only 1-2 exceptions at 64, which drive the correlation. With corrected
  63-byte alignment, those exceptions occur only at the **first or last frame** of each file (e.g. index 0 or
  n−1), and their larger dt/step values are boundary artifacts — slot 9 is effectively constant-zero padding.
  Exact meaning **unresolved**.
  FXM keyframe-field survey (148 nodes across 5 corpora): quaternions are exactly unit, scale components are all +/-1 (one mirrored bone), and the 4-byte trailer equals `size_hint - 84` in 148/148 nodes — a new corpus-confirmed structural invariant via `fxm_tool.check_node_consistency()`. FXM `key_count`: a fresh child-count hypothesis was excluded (0 children for 47/49 nodes), and an
 Expanded to 12 corpora: 91 files / 148 standard nodes, all key_count=3 — invariant corpus-wide.  unfiltered node scan still found only value 3 (53/53 nodes, size_hint 96). Cross-variant header diff: the
  standard node header triple is `(1, 96, 3)` (second field varies 94–100 across the corpus), while the
  NUL-name variant trailer is `(1, 0x50=80, 1)` in 239/239 nodes. The variants never coexist in one file
  (5 standard-only, 55 NUL-only), and NUL files use `LMA `/`FXA ` magic with mixed header bytes, so the
  third field is consistent with a variant/version tag but its exact semantics remain **unresolved**.
  A follow-up checked all FXM header u32 fields for a value of 3 or the node count: none matched, so
  `key_count` is not derived from a header animation-frame count. For GTTF, testing the packed bytes as
  fixed-point wheel-speed/steering against DSI-derived speed (3,722 samples with a proper DSI time field)
  gave |r|<0.11 for all u16/u32 readings — no fixed-point speed relationship.
  Slot 9 (+36) shows the same artifact: its float mantissa is effectively constant, so its values are
  exactly `0, ±8.5, ±34, ±136, ±544, ...` (each step x4) — i.e. only the exponent/sign byte at +39 carries
  data (0x43/0xC3 etc., a sign bit plus a ~7-bit magnitude). Both "floats" are really packed-byte fields,
  not physical measurements; this refines the earlier "16-bit-quantized float" description. Headings and
  speed correlations for these bytes remain weak/inconsistent. Characterized the remaining per-frame
  bytes +40..+62: the apparent 4×int16 structure at +40/+42/+44/+46 does **not** behave like wheel
  speeds (corr with car speed ~0, values span ±32k); no monotonic counters or steering-correlated
  fields found (best |r| ~0.3). Exact slot 7/9 and remaining per-frame field meanings **unresolved**.
- **GTR1 extra 16 bytes — RESOLVED**: always `[0, u, v, 0]` (zero padding + 2D float UV pair),
  confirmed across 2,215 vertices in 100 files. Added as `uv` field in `read_gtr1_vertices()`.
- **GTR1 descriptor-less variant — RESOLVED**: 22,287 GMTs lack the 0x194 grid. Their
  0x11c table's `vertex_offset` holds 36-byte triangle records (u16 indices at +4),
  `index_offset` holds positions (32-byte records, first 3 floats xyz, 4-byte lead), and
  the object table at +12 gives the true vertex count. `gmt_semantic.read_gtr1_object_mesh()`
  decodes ARMCOSHAD01.GMT: 30 positions, 28 valid triangles; validated on 200/200 files
  with all triangle indices in range. **Resolved**.

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
GTR1 coverage is now complete: a full `../GTR1Vanilla` scan (33,477 GMTs with the GTR1 magic) is decoded by `read_gtr1_descriptors()` (10,359) or `read_gtr1_object_mesh()` (23,118), with 0 undecoded files. Revisit MTS rig semantics only if new evidence appears.
