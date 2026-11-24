# Open issues — offline research record (2026-11-23)

All work here is **offline**: no game was launched. "Runtime-dependent" means
conclusively establishing it requires actual game execution.

## GTTF byte +31 event/smoothed-speed hypotheses (2026-11-24)

Tested whether the varying byte +31 marks discrete track events: it changes between consecutive frames in **47.3%** of 44,573 transitions (far too frequent for pit/lap markers), and speed near changes (median 22.3) is just the naturally higher speed where quantization steps toggle. A bounded search over lags 0-20 and EMA smoothing alphas 0.1-0.9 found best speed correlation only r=0.34 (lag 20, alpha 0.1), with most files below 0.25. Byte +31 is therefore neither a rare event flag nor a smoothed speed signal; its quantized magnitude semantics remain unresolved.

## IRSR replay frame grids (2026-11-25)

Cross-corpus check: `simbin_events_tool.find_frame_grid()` detects the 63-byte frame grid in 4/4 GTL IRSR replays but in **0/6 Superleague, 0/5 RF1Vanilla and 0/9 GTR2 IRSR replays** (metadata parses in all). A generic scan of a Superleague replay for monotonic f32 timestamps at strides 16-128 and phases 0-127 found no sequence of >=20 frames. Only GTL IRSR (and GTTF `.gtt`) replays expose the documented frame grid; other IRSR variants remain metadata-only.

## TR2009 `.hdv` opaque variant (2026-11-25)

`../SimuladorTopRace2009/GameData/Vehicles/TRV6_2009/trv6_09.hdv` (12,746 B) has a valid `//[[gMb1.002f (c)2007]]` 44-byte header followed by a 12,701-byte high-entropy payload (`7b 4a 9b 6c...`). Exhausted: ISI-crypt forced enctypes 0/1 at skips 0/4/12/16, all JCA keys, zlib/gzip at offsets 0/44/45 — no printable text or valid layout. The corpus test now skips this one file; no speculative decoder added.

## GTTF +24/+28/+44 packed-integer hypotheses (2026-11-25)

Using ccgepmonitor's `mLapDist`/`mPathLateral` semantics as a guide: slot +24 is the constant marker `01 00 00 34` in 29/29 files (no data); slot +28 begins `00 20 00 XX` (fixed low 16 bits `0x2000`) in all files, and its varying byte +31 shows no correlation with cumulative distance (median r=-0.014) or frame delta-time (-0.010). Slot +44 holds near-1e38 floats (±1.6e38 range) — not bounded lateral metres. No packed-integer or bounded-range interpretation matched any runtime field; recorded as negative.

## GTTF slots 28/36/40 kinematic hypotheses (2026-11-25)

Using ccgepmonitor's documented GTR2 runtime ranges as a guide, slots +28/+36/+40 were correlated against speed and longitudinal acceleration across all 29 files: median r ≈ 0 for every combination, max |r| ≤ 0.08, no file above 0.5. These slots are not speed or acceleration signals under any simple linear or sign-flipped interpretation. The 24-bit integer at +32 was also tested against cumulative lap distance (ccgepmonitor `mLapDist` semantics): median r=-0.05, max 0.254, no file above 0.9 — not a lap-distance field. Combined with earlier quadratic/quantization/exclusion results, they remain uninterpreted.

## GTTF field +16 pitch hypothesis (2026-11-25)

Tested whether the small angle f32 at frame offset +16 encodes pitch/vertical motion: correlation with position-derived vertical velocity across all 29 GTT files gave median r=0.003 (max |r|=0.298), and smoothing the vertical velocity (alpha 0.2/0.5) did not help (median ~0.002). Field +16 is not a pitch/vertical-velocity signal.

## GTTF slot +32 structural finding (2026-11-24)

The 4 bytes at +32 are **not** a meaningful f32: byte +35 is 0x00 in 860/860 sampled frames, forcing every float interpretation to 0.0. The first three bytes instead form a varying **24-bit integer** (46/128/55 distinct byte values at +32/+33/+34), with a near-constant maximum ~5,873,825–5,873,841 across files. The integer is upward-monotonic in only 68% of consecutive pairs (0.64-0.74 across 29 files) and shows no meaningful correlation with inter-frame distance (median r=-0.019), elapsed time (-0.024) or speed. Reinterpreting bytes +31..+34 as f32 yields mostly near-zero values with rare enormous outliers and no kinematic correlation (median r=-0.011). Recorded as a structural characterisation only; no semantic decoder promoted.

## GTTF slot +40 quantized-field structure (2026-11-24)

The 4-byte field at frame offset +40 is zero in 740/860 sampled frames (86%) and takes only 94 distinct f32 values, dominated by ±28.x and ±7.x. Unlike slot +36, both byte pairs vary (251 distinct at +40/+42, 312 at +42/+44), so it is a genuinely varying signal. Tested against position-derived kinematics across all 29 GTT files: correlation with unwrapped heading delta has median r=-0.002 (max 0.063), with lateral acceleration median -0.004 (max 0.103), and with longitudinal acceleration median -0.002 (max 0.037). No file exceeds |r|=0.5 for any of the three. Recorded as a negative result — no semantic decoder promoted.

## GTTF slot +36 quantized-field structure (2026-11-24)

The 4-byte field at frame offset +36 is **not** a free f32: bytes +36/+37 are `00 00` in 853/860 sampled frames (99.2%; only 3 distinct patterns, including `00 40`). All variation lives in bytes +38/+39 (54 distinct patterns). f32 interpretation yields only **82 distinct values** across 44,631 samples, dominated by ±34·4^k (34, 136, 544, 2176, 8704, 34816 and negative counterparts) plus ±8.5/±8.8 — a heavily quantized signal. A second hypothesis (v = ±38·4^k) fits only 27/44,631 and was rejected. The big-endian u16 at +38 shows only weak correlation with position-derived speed (median r=0.146, max 0.359 across 29 files; no file exceeds |r|=0.5). Recorded as a structural characterisation; no semantic decoder promoted.

## `.hdr` index table (2026-11-24)

Beyond the verified +8 block count, the 4-/8-byte tables following the 16-byte `.hdr` header do not resolve to per-sound MP3 offsets with any tested interpretation: parsing the remainder as u16/u32 (little- or big-endian) yields monotonicity 0.06-0.51 (random ≈0.5), mod-3 bias at most 0.43 vs uniform 0.33, and MP3-frame-sync hit rates that merely mirror the natural 1/3 of `.dat` block boundaries that begin with a sync. `u16@0` has 125 distinct values (not a filename index; `0002.hdr` etc. all carry 0x62) and does not correlate with the MP3 sample rate (24000 Hz mono 128 kbps across sampled files). Only the block-count field is used by `hdr_dat_mp3()`; the table semantics remain undecoded. No speculative decoder added.

## `.svm` conversion gap (2026-11-25)

Systematic same-name GTL↔GTR2 comparison across 16 config extensions found `.svm` car setups are the clearest conversion gap: the rF1 versions of `Donington.svm`/`Spa.svm` carry only **6 keys** (174 B, `gMa1.000f` header) while the GTR2 versions carry **72 keys** (~2,380 B). The 6 rF1 keys are a strict subset (0 rF1-only) with identical values in 5/6 and 6/6 cases (the single difference is car-specific `finaldrivesetting` 0→1). The 66 additional GTR2 keys are car-specific setup values (brakes, camber, diff, engine maps, suspension) that cannot be derived from the rF1 setup alone — they require a same-car GTR2 template. `gtl_to_gtr2.convert_config_bytes()` does **not** handle `.svm` (only `.trk/.aud/.hdc/.tyr/.dmg/.gdb/.car/.aiw/.rcd/.ani`), so a converted tree copies the minimal rF1 setup verbatim into GTR2 — a real gap. No template-free conversion rule can be promoted; documented rather than guessed at. A template-based adapter is also not viable from local corpora: the same-name GTL/GTR2 `.svm` files belong to **different cars** (e.g. GTL `Donington.svm` is an Austin Healey 3000 / Corvette / Ferrari 275 GTB while GTR2 `Donington.svm` is a Chrysler Viper / Ferrari 550 / 575), so no same-car GTR2 template pair exists.

## GSC-encrypted GMT deep probe (2026-11-25)

Deep field-level probe of the minimally investigated `../Automobilista`, `../StockCarExtreme`, `../GameStockCar` and `../CopaPetrobrasdeMarcas` corpora: all sampled archived `.gmt` members carry the known GSC ISI signature `0x4b1dca9f960524e8` (enctype 1) and `isi_crypt.decrypt_bytes()` decrypts them successfully. In a 2,000-file sample, the 16-byte word at offset **0x1D4** is a near-magic `c8 cf d2 d8 ce d8 e6 c3 d6 de d8 be bb a8 bf 90` — the standard GMT magic except byte 13 is `a8` rather than `a6` — in 101 files. `gmt_semantic.read_gmt()` finds submeshes in 92/101 of those, versus only 9/1,899 files without the near-magic (strong statistical discriminator, not a strict rule). Files with submeshes yielded real geometry (e.g. 258 vertices / 220 faces in one sample). The remaining ~95% of decrypted GSC GMTs do not expose submeshes to the current parser; whether this is a further encryption layer, a compression variant or a distinct old layout remains unresolved. Cross-corpus contrast: a 500-file sample of `../RF1Vanilla` old-layout GMTs decodes **500/500** through `gmt_semantic.read_gmt()` (1,466,934 vertices / 715,234 faces), without any ISI decryption and without the standard magic at 0x1D4 — the parser scans for per-submesh 0x2000-magic headers rather than a file-level marker. Thus the failure on GSC-encrypted GMTs is specific to those files, not to the old-layout parser. Further discriminating probes confirmed this is a **distinct layout**, not a decryption-offset or enctype problem: both decodable and undecodable files decrypt correctly with enctype 1 (calling `isi_crypt()` directly with enctype 0/1 shows only enctype 1 yields structured data); the decodable files carry per-submesh headers with magic `0x20004035`/`0x20004015` at offsets 0x2e4/0x368, whereas a full byte-wise scan of an undecodable 114,816-byte file found **zero** occurrences of any `0x20004011/15/35` (or strip) magic. The undecodable files also fail all GTR1-style readers (`read_gtr1_object_mesh`, `read_gtr1_table`, `read_gtr1_descriptors`) and contain no zlib header in the first 4 KB. Compression-layer probe: a whole-file scan of a decrypted undecodable GSC GMT found exactly one `78 9c` and one `1f 8b` byte pair, both at random offsets producing invalid streams ("invalid distance too far" / "unknown compression method"); raw-deflate at every offset produced 83 "large" hits but all at 32-byte vertex stride with identical lengths — clearly vertex-data artifacts, not compression. The `../MAS2Extract` rF2 `GMOTOR_MAS_2.90` reference uses a salt+XOR archive header (a different container level) and does not apply to member-level GSC GMT. Unit-triple probe: a 60-file-per-corpus scan found unit-norm float triples in 25-31 "other" (non-magic) files per corpus (e.g. `AMBULANCE001.GMT` has 1,345), forming consecutive runs at a **16-byte stride** with a trailing zero 4th float — i.e. real vertex normals exist. However `gmt_semantic.read_gmt()` finds 0 submeshes in these files because the `0x200040xx` per-submesh magic headers are entirely absent. Thus the ~95% are not empty: they contain geometry indexed by a different (undecoded) container layout, not a submesh-header format. Follow-up: the 16-byte-stride unit-normal runs are **not universal** across the undecodable files — a 50-file-per-corpus sample found runs in only 9/50 (Automobilista), 8/50 (StockCarExtreme), 10/50 (GameStockCar) and 17/50 (Copa). Examination of a longest run (49 records at 0x19cdc in `AMBULANCE001.GMT`) showed 16-byte records of 3 floats + a constant `0x8c8c8c8e` word with no accompanying count/offset table, so no vertex/face table invariant could be promoted across all four corpora. No speculative decoder added. A second ISI-crypt layer was excluded: after one decrypt pass the 16-byte signature is unrecognised by `isi_crypt.GAMES`, and forced enctype-1 re-decryption at skips 0/4/8/16 produces only garbage. The decrypted payload begins `ee 68 ee ee 20 00 00 04` (0x04000020 flags-like field) but does not carry a recognised second-layer signature.

## `.gdb`/`.car` universal-key survey (2026-11-24)

Generic section/key parsing of all 1,287 `.gdb` and 3,385 `.car` files found **667 / 173 distinct keys respectively but no cross-corpus universal key**. Only family-specific universals exist: `.car` GTR2-family files (165) all carry `genstring`, `pitgroup`, `number`, `driver1`, `team` (the GTR2-only key set already used by `gtl_to_gtr2`); rF1 `.gdb` (81) all carry `racelaps`. Seven zero-length `.gdb` fixtures in `../rfactortools/tests/data` are legitimately empty. `parse_gdb()`/`parse_car()`/`validate_config()` therefore perform structural validation only — no universal key rule can be promoted beyond the existing family-specific validators.

## Encrypted `.svm` setups (2026-11-24)

10 shipped `.svm` files (only **2 distinct payloads**, duplicated across corpora: `Toban Long.svm` 558 B and `Orchard Lake Oval.svm` 449 B) carry `//[[gMb1.000f ...]]` headers followed by a high-entropy payload beginning `5b 79 6d 98 7f 80 a9 e0` (221 distinct byte values, ~11 short ASCII runs, implausible f32 alignments). The two payloads share a 20-byte prefix. Exhausted offline hypotheses:
- single-byte XOR (0..255): best printability 0.45, no valid plaintext.
- XOR with filename / `gMb1.000f` / `gMa1.000f` / `ISI` / `gtr2` / `rFactor` repeating keys: 0.33-0.40 printability, no valid plaintext.
- gzip / raw-deflate / bz2 / lzma: all fail.
- `isi_crypt` forced enctypes 0/1 with skips 0..64: best 0.475 printability, no valid decrypt.
- JCA with all known keys: no valid decrypt.
Known-plaintext XOR against typical GTR2 setup prefixes (`[GENERAL]\r\n`, `VehicleClassSetting=`) yields no repeating keystream or recognisable pattern. **Undecoded** — likely a proprietary compiled/encrypted setup format; needs the originating tool or source. No speculative decoder added.

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
  **`wp_score` lap distance / `wp_path` (no strict rule)**: the Turbo Basic hint says `wp_score`'s second field is lap distance from start/finish. In 26 AIW files the maximum score matches the declared `lap_length` exactly in 15 cases and within 1% in 23, but three files differ by up to 251 m; the score is not a cumulative distance from file-order start because waypoints form a cyclic list. `wp_path`'s "dry/wet" fields are both signed (dry 13,055 negative / 10,642 positive / 7,013 zero), but the wet field is non-zero in 19,015/30,710 cases, so neither is a constant. No validator rule promoted.
  **GTTF post-marker bytes (structural invariant)**: across all 29 files the 7-byte marker at +24 is identical (`01 00 00 34 00 20 00`), and the trailing byte at +31 is 0x40/0x41/0x42. The 4-byte field at +32 always has its high byte (+35) equal to 0x00 (29/29), i.e. a small value in the low 24 bits; the 4-byte fields at +36/+40 show fixed mantissa-style byte patterns (e.g. `40 00 18 43` = 152.0, `00 00 18 42` = 38.0) consistent with quantized/bit-packed values rather than plain floats. Recorded as structural evidence only; no semantic rule promoted. A steering hypothesis for slot +36 was tested via sign agreement with unwrapped heading delta across all 29 files: 0.499 mean agreement (chance), definitively excluding it.
  **GTTF marker cross-check (confirmed)**: searched the 63-byte GTTF records for the `gtr2-accel-challenge` reference marker at *all* byte offsets across all 29 `.GTT` files. The 7-byte prefix `01 00 00 34 00 20 00` occurs in 29/29 files, consecutive markers are exactly **63 bytes apart in 29/29 files**, and the varying 8th byte is 0x40 most often (10,082 frames) with 0x3F/0x41/0x42 etc. also present — matching the reference's `...00 40` with a variable trailing byte. The marker's absolute file offset modulo 63 varies by file (metadata length), consistent with `find_frame_grid()`.
  **GTTF unknown slots, lagged correlation (excluded)**: across all 29 GTT files, every unknown 4-byte slot at +24..+60 was correlated against heading (+12), unwrapped heading delta, and pitch (+16) with lags 0..20 frames. Best per-file |r| means were 0.0–0.066 and signs were inconsistent (e.g. slot +28: 21/29 same sign, mean 0.066; all others ≤0.03 with ~17/29 split). No slot is a lagged heading/pitch signal. Combined with the earlier acceleration/speed tests, slots 7/9 remain uninterpreted.
  **GTTF byte +31 (partial, negative)**: across 6 GTT files the varying byte of slot 7 (+31) takes 42–62 distinct values, all in the ASCII range 32..94 with 64 (`@`) most common. Given the fixed low bytes `00 20 00`, interpreted as f32 this yields powers of two (0.5, 1, 2, 4, 8…), confirming the earlier "fixed-exponent artifact" conclusion. Tested whether byte +31 is an XOR or additive checksum of the other 59 frame bytes: matches were 36/10,535 and 41/10,535 respectively — chance level (1/256). No derived-field rule promoted.
  **E30 wiper record structure (partial)**: the two 890/1562-byte LMA BMW E30 wiper files contain NUL-terminated names at offsets 190, 386 and 582 — exactly 196 bytes apart — with the first two records byte-identical after their names. Each record starts with `f8 60 69 0d 08 10 00 00 ... cd ab ba dc 78 01 ...`; the `cd ab ba dc / 78 01` bytes look like a zlib marker but **zlib decompression fails at every offset and window bits** (decompressobj also fails), and a full-file XOR (0..255) and bit-rotation scan finds zero TRS keys. Online search confirms `CD AB BA DC` is the **MSVC debug-heap fill pattern** (it appears in Windows crash/memory dumps), and the surrounding values are pointer-like (0x0d61xxxx). The records therefore contain uninitialised/garbage in-memory data rather than a usable animation encoding. No decoder added; treated as corrupt shipped placeholders.

  **`wp_width` / `wp_dwidth` (no strict rule)**: the guitarmaen reference documents `edgeL=pos+perp*(-widthA)`, `edgeR=pos+perp*widthB` and 4-element width/dwidth vectors. Corpus checks on all 30,710 waypoints found `dwidth[0]==width[2]` in only 19,309 and `dwidth[1]==width[3]` in 18,505 cases; `dwidth[2]==0` in 28,293 and all 8 width/dwidth values non-negative in 30,655. No strict invariant was promoted.
  **`wp_groove_lat` (partial)**: the Turbo Basic source describes it as a signed lateral offset from the AI line (− left, + right). Corpus: both signs occur in every corpus (e.g. GTR2 −6.26..+8.76, GTR1 −6.63..+9.06), confirming the sign convention. A magnitude bound `|wp_groove_lat| <= GrooveWidth` fails on 320/29,227 waypoints in 24 files with a `GrooveWidth` field (e.g. 3Oschersleben max 8.76 vs width 6), so no strict range rule was promoted.
  **Shared-memory-header hypothesis (excluded)**: the newly added `../rFactorSharedMemoryMap`/`../rF2SharedMemoryMapPlugin` headers document runtime units (RPM, throttle 0..1, steering −1..1, gear −1/0/1+, yaw/pitch/roll rad, speed m/s). Using these as a guide, all unknown GTT frame slots (+24..+60, 4-byte floats) were correlated against position-derived longitudinal acceleration, lateral acceleration and speed across 12 GTT files. No slot shows a consistent correlation (best |r| values 0.0–0.27 and varying sign between files), so the headers provide no new field mapping for the ghost-frame format. Note: frame slots +0/+4/+8 are the car XYZ position and +12/+16/+20 are heading/pitch/time — only +24 onward are unknown.
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
