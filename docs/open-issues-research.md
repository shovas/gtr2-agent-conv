# Open issues — offline research record (2026-11-23)

## GSC-family EXE static loader trace — blocked by packing (2026-11-28)

Tried to trace the GSC-family mesh loader statically to derive the ISI decryption skip from code. Result:
- `CopaPetrobrasdeMarcas/Marcas.exe`, `StockCarExtreme/GSC.exe` and `Automobilista/AMS.exe` are **packer stubs** (imports `VirtualAlloc`/`GetProcAddress`; no GMT loader strings at all).
- `GameStockCar/GSC.exe` is YMY-packed but retains an unpacked data image containing `Error reading mesh from GMT file %s` at RVA `0x128b008`; radare2 analysis finds **no code xrefs** and no immediate references to that address, so the corresponding loader code is not present in the static image.
- The unpacked `GTR2.exe` loader (`fcn.005d68d0`) is a different-generation reader and does not establish the GSC skip parameter.

So the code-first route to the GSC loader is blocked without unpacking/runtime tooling. The correct `skip=4` remains empirically validated on 150/150 sampled members. Full-tier regression test records the packing state.

## Face winding convention verified across old/new layouts (2026-11-28)

Compared triangle cross products against the stored vertex normals:
- decoded GSC members: forward agreement 0.0, reversed **1.0** (14 samples);
- rF1 old-layout meshes: forward 0.0, reversed **1.0** (12 samples);
- GTR2 target meshes: forward 0.0, reversed **1.0** (17 samples).

All three generations use the same inverted winding-vs-normal convention, so `gmt_layout.old_to_new_semantic()` correctly preserves index order — no winding flip should be introduced. Full-tier regression test added.

## GSC GMT geometry SOLVED: wrong ISI skip, not region masks (2026-11-27)

**Breakthrough.** All earlier "region-specific mask" work was an artifact of decrypting ISI-encrypted GSC GMT members with `skip=1`. The correct parameter is **`skip=4`**: `isi_crypt.decrypt_bytes(raw_member, 4)` yields the native GSC magic (`...bba8bf90`) directly with **no residual XOR**, and the bulk vertex/index data is intact.

Evidence:
- **150/150** sampled members across Automobilista, StockCarExtreme, GameStockCar and Copa Petrobras de Marcas decode via `gmt_semantic.decode_gsc_member()` with submeshes, **plausible positions and faces** (e.g. `AMBULANCE001.GMT` 2,433 faces, `PURCHASED.GMT` 5 submeshes / 8,786 faces, `ARMCO01.GMT` 96 faces).
- Five unmasked GMT images embedded in `GameStockCar/GSC.exe` (file offsets `0x3a3980`, `0x3a3ed0`, `0x3a44f0`, `0x3a5080`, `0x3a5cb0`) were found with the same native magic and fully plausible geometry — direct confirmation that the magic byte `0xa8` is a real GSC-era format revision, not a masked GTR2 magic.
- With `skip=1` those same members show the apparent per-file `magic ^ K` masks and implausible vertices; sweeping `skip` showed `skip=4` collapses every magic key to `K=0` and restores geometry.

`decode_gsc_xor_gmt()` is retained only as a historical artifact path (structure without geometry); the old "mask schedule", "per-vertex run", "name/metadata derivation", "no alignment counterpart" and "geometry caveat" sections below are **superseded** and kept for provenance. Use `decode_gsc_member()` for conversion work. Full-tier regression test added.



All work here is **offline**: no game was launched. "Runtime-dependent" means
conclusively establishing it requires actual game execution.

## GTTF +48 packs two signed channels (2026-11-28)

Extending the +48 halfword study across all 29 ghosts:
- **low i16** ↔ steering +8: median |r| **0.099** vs 0.015 permuted (already recorded);
- **high i16** ↔ engine +32: median |r| **0.122** vs 0.021 permuted, with 21/29 files exceeding 3× their own permutation baseline.

So slot +48 is best described as two packed signed 16-bit channels, one steering-related and one engine-related. Neither has a confirmed fixed scale (the empirical slope varies by file), so no unit is claimed. Full-tier permutation-controlled regression test added.

## GTTF +48 units: low signed 16-bit half (2026-11-28)

Slot +48 is almost always near `0xFFFFxxxx`, i.e. two signed 16-bit fields rather than a float. Decoding the **low half as int16** produces a much stronger steering association than the raw u32:

- median |correlation| with steering `+8` = **0.503** across 12 ghosts, vs **0.021** permuted (~24×);
- the high half gives only 0.134, and neither half tracks curvature (0.016) or yaw rate (0.06–0.07);
- the empirical slope `low_i16 ≈ A * (+8) + B` varies by file (A ≈ 29k–42k), so no fixed unit/scale is claimed.

This is a verified structural invariant: +48's low half is a steering-related signed quantity, but its units and sign convention remain unknown. Full-tier permutation-controlled regression test added.

## GTTF remaining slots vs reconstructed kinematics (2026-11-28)

Permutation-controlled study across all 29 ghosts using reconstructed world speed, steering `+8`/`+16` and engine `+32`:

| Slot | median \|r\| with +8 | with +16 | with engine | with speed | verdict |
|---|---:|---:|---:|---:|---|
| +40 | ~0.05 | ~0.05 | ~0.04 | ~0.03 | at chance |
| +44 | ~0.04 | ~0.01 | ~0.03 | ~0.02 | at chance |
| **+48** | **0.193** | 0.08 | 0.168 | 0.03 | **modest steering/engine coupling** |
| +52 | ~0.05 | ~0.06 | ~0.05 | ~0.04 | at chance |
| +56 | ~0.02 | ~0.03 | ~0.04 | ~0.02 | at chance |
| +60 | ~0.05 | ~0.03 | ~0.04 | ~0.06 | at chance |

For +48, the permuted baseline for the +8 coupling is 0.018 (≈10× lower) and 19/29 files exceed twice their own baseline; the sign varies by track. This is a weak but real association, not a decoded semantic — exact units remain unknown. Full-tier permutation-controlled regression test added.

## GTTF +36 is not an AIW surface attribute (2026-11-28)

Tested slot +36 against nearest-AIW-waypoint `galpha`, `width` and waypoint index across 12 ghosts: median |correlation| 0.009 / 0.012 / 0.012, all at or below permutation baselines. Combined with the curvature negative (|r|<0.01), +36 remains structurally characterized (quantized lattice) but semantically unresolved. Full-tier regression test added.

Session-time inference attempt: searched `GTR2Steam/GameData` and `Config.ini` for 36000/43200/46800 outside event files; only `LAUNCHTIME=600` exists and the other matches are coordinate substrings in `.ds` files. The 10h/12h/13h interpretation remains an inference from the exact header values, not corpus-confirmed.

## GTTF +32 gear-ratio bands and +36 curvature negative (2026-11-28)

With reconstructed world positions and 5-frame smoothing, `+32 / speed` clusters near the F550's gear-ratio-derived bands. Bands were computed **from the actual setup files**: `HewlandLS200.grb` ratios, `BMS550.hdc` gear settings (0/3/7/11/17/22), final drive 3.10 and `Michelin_GT.tyr` rear radius 0.355 m, scaled by the observed `1024` engine-speed factor → ~85.5k/97.5k/111k/138k/177k/250k raw per m/s. Across 7,047 samples from 8 ghosts the median relative distance to a band is **0.0496**, versus **0.1247** for six random log-uniform bands (permutation p≈0.01). This strongly supports an engine-speed interpretation but the exact scale remains unconfirmed; full-tier regression test added.

Slot `+36` is **not** path curvature: median |correlation| with 3D path curvature is **0.007** across 10 ghosts (full-tier regression test). Its quantized-lattice structure remains the only verified fact.

## GTTF heading semantics resolved: atan2(dx,dz) (2026-11-28)

With reconstructed world x, ghost `+12` heading aligns with AIW pointer-chain tangents in the **world x/z plane** as **`heading = atan2(dx, dz)`**: median circular coherence **0.858** across 15 matched ghosts (dominant convention in 10/15 files; equivalent `-atan2(dz,dx)` in the rest). The earlier y/z-only test gave 0.404 and the DSI-line test 0.318 — both were degraded by the missing x. Full-tier regression test added (median >0.7 across 29 ghosts).

## GTTF frame +16 vs engine speed (2026-11-28)

Frame `+16`, with its clamped (`|+16| > 0.99`) frames removed, still couples weakly to engine `+32`: median |correlation| **0.152** across 29 ghosts vs **0.020** for shuffled values. Unlike the +8/+16 "steering" result, this survives removal of the saturation frames. It is consistent with a throttle/engine-related control signal but does not establish pedal semantics (the earlier acceleration negative stands). Full-tier permutation-controlled regression test added.

## GTTF slots +40/+44/+52/+56/+60 packed-half study (2026-11-28)

Decoded each sentinel-like u32 slot as two signed i16 halves and tested them against engine, path controls, steering and speed with permutation baselines:
- **slot +44** halves vs `path_f4`: median |r| **0.071** vs **0.013** permuted (5.4×; 26/29 files >2× baseline); vs engine 0.126 vs 0.021.
- slot +40 halves vs `path_f3`: median |r| 0.024 vs 0.015 — weak, not promoted.
- slots +52/+56/+60: at chance.

Slot +44 therefore carries a weak but reproducible path/engine-related packed signal; exact units remain unknown. Full-tier permutation-controlled regression test added.

## GTTF path_f4 vs gear bands (2026-11-28)

Assigned each frame to one of six gear bands derived from the F550 `.grb`/`.hdc`/`.tyr` setup (as in the +32 study) and compared `path_f4`:
- pointwise correlation with gear index: median **−0.200** across 29 ghosts, vs **−0.005** with permuted gear labels;
- within-gear correlation with normalized engine position is modest (median r 0.142 vs 0.003 permuted);
- `path_f3` is high (>0.9) in only 6.4% of decelerating frames — not a simple brake flag.

This supports f4 as a throttle/demand-like channel on the reference line (stronger in low gears), but neither channel reproduces the ghost's own pedal positions; exact semantics remain unclaimed. Full-tier permutation-controlled regression test added.

## .Vcr replay files share the IRSR container (2026-11-29)

The nine shipped `GTR2Steam/ReplayData/*.Vcr` files are gzip-compressed with
the same `//[[gMb1.000f…]]` wrapper and `IRSR` v1.05 magic as time-trial
ghosts. `simbin_events_tool.parse_payload()` already reads all nine: TRK/AIW
names, driver, co-driver, team, car and `session_seconds` (always one of
36000/43200/46800) parse cleanly, and the CLI handles them without changes.
However, `find_frame_grid()` returns None for every replay: the GTTF 7-byte
marker `01 00 00 34 00 20 00` is absent and a stride autocorrelation shows
a 20-byte repeating pattern instead. A broader search over strides 20..2040
(phases and 4-byte field offsets up to 128) found **no** monotonically
increasing f32 or u32 field with plausible frame deltas, so the replay frames
are not laid out as a simple fixed-stride time series with a leading time
word. Replay frame layout is therefore a distinct, undecoded format —
recorded as a new avenue, not claimed as solved. Full-tier header regression
test added.

## UV tiling ratios are material properties (2026-11-29)

Grouping 8,816 meshes with decoded tiling ratios by their material name found
487 groups with at least three meshes. In **91.6%** of those groups every mesh
had the same `(ratio4, ratio6)` pair, versus **4.8%** when the same ratio pool
was shuffled across groups (distribution-preserving). So the tiling ratios
are a material-level property rather than per-mesh noise, which is promising
for transferring UV scaling during conversion once a source material is known.
Full-tier permutation-controlled regression test added.

## UV parser fallback tightened after regression (2026-11-29)

The earlier change exposing single-block UV blocks whenever `rec[7]==0` was
too permissive: a few meshes have `index_offset - rec[6]` larger than
`vertex_count*32`, producing a misaligned `stream2_data`. A targeted run of
`tests.test_gmt_format` caught this (`448 != 256`). The parser now exposes the
fallback block only when its length is exactly `vertex_count*32`. The
column-7/column-1 stream invariant was also re-scoped to the two-stream layout
(it does not hold for single-block UVs, which end in zeros). All 35 module
tests and the five affected full-tier tests pass after the fix.

## VCR payload has an 86-byte fundamental period (2026-11-29)

Byte-level autocorrelation (unaligned, lags 1..200) on `Anderstorp.Vcr`
initially appeared to peak at lag **86** (0.567 matching bytes vs 0.127
shuffled) over the window 0x400..0x3000. Localizing the measurement showed
the periodicity is **confined to the header region** (first ~0x2000 bytes:
0.78 at lag 86, and 0.91 in 0x800..0x1000), while the bulk data drops to
0.04–0.06. So the 86-byte structure is a header table, not the frame grid —
the earlier "86-byte frames" reading was too broad and is corrected here.
Earlier 4-byte-aligned stride searches also skipped 86 because it is not a
multiple of 4. A short 12-record run in the header has an increasing f32 at
+0 (~0.022 s steps) and a constant 10.545 at +16, but it does not extend
across the file. Frame semantics remain undecoded. Full-tier test scoped to
the header region.

## GTTF vs IRSR header flags (2026-11-30)

Parsed the post-filename header fields on all 29 GTTF ghosts and nine IRSR
replays. Every GTTF file has the identical flag tuple `(a=0, b=0, c=1, u=0)`;
session variation is carried solely by `session_seconds`
(36000/43200/46800). IRSR replays use several tuples (`a` 0/1, `b` 0/1/6,
`c` 5/8, `u` 0/1); `b=6` appears in two of the three "HOT LAP" files and
`c=8` only in Magny-Cours, but with nine samples no semantics are claimed.
Full-tier regression test added.

## Replay time-shift editor (2026-11-30)

Added `shift_replay_times()` on top of the verified decoders: it patches every
frame's f32 time word and each participant's finite activity-window bounds in
place, leaving sub-record bodies and the summary duration (a span) unchanged.
Verified on three GTR2 replays: per-frame deltas are 64.0 s within f32
tolerance (Monza's 4,920 frames show max rounding ~1e-5 s), participant starts
shift identically, and re-parsing yields identical frame counts, sub-record
counts and end offsets. Full-tier test added.

## GTL v1.01 replay format resolved (2026-11-30) — correction

The earlier "GTL declares zero frames" conclusion was an artifact of applying
the v1.05 summary layout to a v1.01 file. The v1.01 summary starts after the
participant records with the f32 sentinel `-1e32`, then three zero-prefixed
fields: u24 frame count, u24 sub-record count, and f32 duration. Example:
`ae c5 9d f4 | 00 cc 04 00 | 00 55 06 00 | 00 ca 63 76 42` decodes to
1228 frames, 1621 sub-records, 61.6 s. `parse_replay_summary()` now detects
both versions and `parse_vcr_frames()` uses a version-aware start offset.
**All 13 local replays (9 GTR2 + 4 GTL) parse exactly to their final byte.**
Full-tier tests updated.

## GTL replay v1.01 frame variant (2026-11-30)

The four GTL `.Vcr` replays parse as IRSR v1.01 but their summary declares
zero frames and zero duration, and the post-summary region begins with zero
bytes followed by the -1e32 sentinel. A permissive frame loop produced three
phantom empty frames from those zeros; `parse_vcr_frames()` now rejects
zero-count summaries and zero-subcount frames, returning None for GTL replays
while all nine GTR2 replays still parse exactly. Full-tier test added.

## Remaining driver-state fields (2026-11-30) — negative

Tested the four u16 fields at body +8 and the small f32s at bytes 41/49
against derived speed, frame index and half-float/fixed-point interpretations.
In Monza.Vcr the u16s divided by 256 cluster near 70 (median 72, 86% in
30..130), suggesting fixed-point temperatures, but Imola.Vcr has a median of
2.0 under the same transform — so the interpretation does not generalize.
The small f32s have no speed correlation (|r| < 0.03). These fields remain
undecoded. The replay CLI now prints the decoded first-driver position/angle
and raw u16s for inspection.

## Driver-state angle field (2026-11-30)

Corrected a labeling error in `vcr_driver_state()`: the angle-like f32 is at
byte 45 (`floats[4]`), not byte 41. At byte 41 and 49 the values are small
(typically |v| < 0.05). On 542 moving frames of Monza.Vcr the byte-45 field
correlates with `atan2(dx, dz)` derived from consecutive decoded positions at
|r| ≈ 0.52 (shuffled baseline ≈ 0.05), so it is heading-related but not an
exact match — likely a steering/YAW value with different smoothing or
wrapping. Added a full-tier permutation-controlled test.

## Driver-state body alignment resolved (2026-11-30) — correction

The apparent "varying f32 alignment" in 53-byte driver bodies was an
off-by-one: searching every byte offset found plausible world coordinates at
offset **29** in 288/300 sampled records (not 28). `vcr_driver_state()` now
reads four u16s at +8 and six f32s from +29. On a 793-frame Monza sample the
first three f32s have lag-1 autocorrelation ~0.999 and median consecutive
displacement <5 m, versus ~100× larger for shuffled samples — they are the
car's world position. The fourth field lies in ±pi and is associated with
position-derived heading (|r| ~0.52 on moving frames vs 0.05 shuffled), but
is not an exact match. Remaining fields and units are still unknown.
Full-tier test added.

## Replay sub-record tags (2026-11-30)

Classified the low byte of sub-record headers across all nine GTR2 replays.
Tags `0..N-2` appear once per driver participant (counts thousands per
replay), `0x68` accompanies the `Safety Marshal` entry, and `0xff` marks event
records. Some `0xff` bodies contain NUL-separated texture names such as
`DYTEX000`, `SRTEX000`, `SSTEX000`; others carry short numeric payloads whose
sub-types are not yet decoded. The 53-byte driver-state bodies contain four
u16 values plus six f32 fields, but alignment of the f32 block varies between
records, so no field-level decoder is claimed. Added `vcr_record_tag()` and a
full-tier test.

## Replay CLI reporting (2026-11-30)

`simbin_events_tool.py FILE --replay` now reports participants (with decoded
CAR/skin names and activity windows), the summary record, and the parsed frame
stream (declared/total frames, sub-record count, first/last times, exact EOF).
The PHS producer/consumer avenue was revisited: GTL.exe contains no
`Physics2.gtl`/`AIStrat.gtl` string (only generic `.GTL` archive references),
and searches for the GTL 0.9.01 updater again found only v1.1 material. No new
PHS evidence; that avenue remains blocked by the missing updater.

## Replay variants resolved: all 9 GTR2 files parse (2026-11-30)

Two exceptions to the frame decoder were traced to data handling, not new
formats:
- `Anderstorp.Vcr`: after the declared 121 frames, a second continuous
  82-frame segment follows; parsing until EOF yields 203 frames and lands
  exactly on the payload end. Frame time wraps from 18.85 s to 0 at index 81
  (lap boundary). `parse_vcr_frames()` reports both declared and total counts.
- `Dubai International.Vcr`: the participant name `René Wijnen` contains a
  Latin-1 byte (0xE9), rejected by an ASCII-only printable check. That stopped
  the participant chain at two records and mislocated the summary. Allowing
  high Latin-1 bytes finds all four participants; the real summary is at
  offset 740 (`count_a=24`, `count_b=64`, duration 28.954 s) and frames parse
  exactly.

All nine GTR2 replay payloads now parse to their exact final byte. Full-tier
test updated.

## Replay frame decoder complete (2026-11-30) — correction

Re-reading `fcn.00527890` revealed that the `+1` applies **only** in the
special branch; the normal size is `((header >> 8) & 0x3ff)` with no +1. My
first parser incorrectly added one in both branches, which is why frame
alignment failed. With the corrected `vcr_subrecord_size()`,
`parse_vcr_frames()` consumes **7 of 9** GTR2 replay payloads exactly:
- frame count = `count_a` (24–7,460);
- each frame = u32 absolute session time + u16 sub-record count;
- each sub-record = u32 header + packed-size payload;
- total sub-records == `count_b` (90–142,974);
- `last_time − first_time` == summary duration (f32 tolerance);
- first frame time == that replay's participant window start.

`Anderstorp.Vcr` parses all 121 frames but leaves trailing bytes, and
`Dubai International.Vcr` uses a different summary marker. Both remain
variants. Full-tier regression test added.

## Replay frame/sub-record layout from reader disassembly (2026-11-30)

`fcn.0052be30` (ghost reader) loops `count_a` times (summary field stored at
`0x2c2420`): each iteration calls `fcn.00526730`, which reads a **u32** into
the frame object and a **u16** at `+8` (the sub-record count), then calls
`fcn.00527890` that many times. The sub-record reader reads a u32 header and
derives a payload size of `((header >> 8) & 0x3ff) + 1`, with `+1` when bits
30–28 are `0x2` and bits 18–23 are zero; the low 10 bits look like a type tag.
These layouts are code-verified. However, applying them from the end of the
summary does not align with the sampled payload bytes (no size formula parsed
more than a handful of frames), so either an additional structure intervenes
for IRSR files or the virtual read method interprets that value differently.
Recorded as code-level layout knowledge plus a parser negative; byte-pattern
test extended.

## Per-frame replay records not located (2026-11-30)

Attempted to extend the participant/summary decoders into the bulk payload by
using the `0x52a540` writer loop and the summary counts. The bytes immediately
after the summary contain a one-off header-like block (e.g. 26 bytes beginning
`06 00 68 34 00 21 00 40` in Anderstorp.Vcr) that does **not** repeat. Bulk
autocorrelation peaks vary per file (86/120 for Anderstorp.Vcr, 20/86 for
Brno.Vcr, 166/40 for Monza.Vcr), and the summary counts divide the remaining
payload with non-integer, file-dependent quotients (22–90 bytes). `fcn.00527700`
writes another variable-length record type (u32 + u8-prefixed string) for a
list at `edi+0x6d0`, but those records were not found in the sampled payloads
either. No per-frame/per-object state decoder is claimed — this is a negative
with structural observations for the next attempt.

## Post-object replay summary (2026-11-30)

Immediately after the participant records, eight of nine GTR2 replays have a
13-byte summary: u8 marker 0, two u32 counts with `count_a < count_b`, and an
f32 duration in seconds (8.97 s for Brno.Vcr up to 284.17 s for Imola.Vcr).
Dubai International.Vcr is the exception (marker 2, implausible counts).
The duration for Anderstorp.Vcr (16.550 s) closely matches that replay's
participant window end (16.594 s), supporting the duration reading. Count
semantics remain unclaimed. Added `parse_replay_summary()` with a full-tier
test.

## Object-record trailing fields (2026-11-30)

The EXE reader `fcn.005268e0` copies the record's u32 fields at `+0xc4` and
`+0xc8` verbatim into the in-memory object without interpreting them, so their
meaning must come from consumers. Across all 36 participant records in the 13
local replays: the second u32 is the classic f32 "unset" sentinel
`0xF49DC5AE` (-1e32) in 31 records and zero in 4 (the GTL files), i.e.
35/36 are sentinel-or-zero. The first u32, read as f32, is finite and
non-negative, usually constant across a replay's participants (8/13 files)
but sometimes differs (e.g. 2355.2 vs 2348.2 in Brno.Vcr). Disassembling `fcn.005269c0` (called from replay update paths) resolved the
semantics: it compares both fields against the global f32 at `0x69B810`,
which is exactly `-1e32`, then compares each bound against a supplied time.
The pair is therefore an **activity window** `[start, end]` for the object,
with `-1e32` meaning unbounded. All five records with a finite end satisfy
start <= end (e.g. Anderstorp.Vcr `[0.027, 16.594]` and Safety Marshal
`[0, unbounded]`). `parse_object_records()` now exposes `window_start` and
`window_end` (None for unbounded). Full-tier test updated.

## Object-record parser validated on real replays (2026-11-30)

Implemented `simbin_events_tool.parse_object_records()` from the disassembled
layout. It walks chains of variable-length records from a scanning start and
recovers coherent participant lists in all 13 local replays: GTR2 files yield
2–6 records whose first two strings are entries like `Sim 10 Original` /
`Jean-Philippe Belloc` and a final `Safety Marshal`; GTL files yield a single
`Shovas` entry. Across the nine GTR2 files every chain has ≥2 records and
seven or more contain `Safety Marshal`; shuffling each payload drops chains to
~1 chance record. This is the first code-grounded parser for replay payload
structure, though the 64-byte blocks and trailing u32s remain undecoded.
The two 64-byte blocks were decoded as fixed-size NUL-terminated strings:
block 1 is always the participant's `.CAR` filename (36/36 records across all
13 replays) and block 2 is usually a `.BMP` skin name (often empty). The first
u32 decodes to f32 ~1.531 in every GTR2 participant record; the second is
sentinel-like. `parse_object_records()` now exposes `car`, `skin`, `value` and
`trailing_u32`. Full-tier permutation-controlled test extended.

## Replay object record format from code (2026-11-30)

Disassembled the per-object serializer `fcn.005267f0` (writer) and its
counterpart `fcn.005268e0` (reader, called from the ghost reader
`fcn.0052be30`). The record layout is now clear at the code level:
- one flags byte, whose top bit is stored separately at record `+0xcc`;
- two **u8 length-prefixed strings** from record `+1` and `+0x21`;
- two 64-byte blocks at `+0x41` and `+0x81`;
- two u32 fields at `+0xc4` and `+0xc8`.

Because the strings are length-prefixed, object records are **variable-length**;
this is direct code evidence that fixed-stride frame searches were the wrong
abstraction for replay payloads. Combined with the 105 sixteen-byte object slots
in the writer, the payload is best modeled as a per-object event/state stream.
No full field semantics are claimed yet. Full-tier byte-pattern test extended.

## GTR2.exe ghost writer located statically (2026-11-30)

radare2 disassembly identified `fcn.0052a540` as the GTTF/IRSR writer: it
selects the `GTTF` magic from pointer `0x6ead90` when a game flag equals 1 and
`IRSR` from `0x6ead7c` otherwise, then writes the TRK/AIW strings with u32
lengths. At `0x52a6ca` it loops over **105** sixteen-byte object slots starting
at `edi+0x40`, serializing each object's linked list through `fcn.005267f0`.
A second list at `edi+0x75c` is counted and summarized (count, first-record
word, and last−first time span) before the frame payload is written via
`fcn.00526a30`. This is the first concrete code evidence for object-oriented,
variable-length replay serialization and explains why fixed-stride frame
searches failed. It is a structural finding only — no field layout is claimed
yet. Full-tier byte-pattern test added.

## VCR 20-byte stride: no frame fields found (2026-11-30)

Followed the 20-byte lag excess: at stride 20, every 4-byte-aligned f32 field
in bulk windows is sentinel-like (|value| up to 1e38, lag-1 autocorrelation
undefined), and no byte offset within the 20-byte cycle is constant in more
than 50% of records. Byte deltas at lag 20 are smaller than at lags 21/86
(median 26–40 vs 64–88) but not small enough for a simple delta encoding.
So the periodicity reflects gradual local similarity, not a decodable fixed
frame record with a time word. No frame serializer is claimed.

## VCR bulk data has a 20-byte lag excess (2026-11-29)

Byte-autocorrelation on a bulk window of each of the nine `.Vcr` payloads
showed lag 20 exceeds the mean of neighbouring lags 18/19/21/22 in **7/9**
files, with a median excess of **+0.16** matching bytes. Dominant bulk lags
also cluster on multiples of 20 (20/60/80/120) in several files. Together
with the raw 20-byte repeated pattern seen earlier, this suggests a small
repeating record in bulk replay data — but no monotonic time field could be
found at that stride, so the record semantics are still unknown. Full-tier
neighbour-lag-controlled test added.

## UV tiling ratios confirmed in Race07 (2026-11-29)

The `(1,2,3,4,5,6,1)` UV signature with integer column-4/6 ratios is not
GTR2-specific: a deterministic scan of the first 400 sorted `Race07Vanilla`
GMTs (JCA-decrypted) found signature meshes such as `Collisionwall.gmt`,
`Shape01.gmt` and `TRACK_2007_01.gmt` whose ratios decode cleanly, while
`road_crack*.gmt` have the same signature without the ratio rule. The rule is
therefore shared across SimBin titles but not universal within a title.
Full-tier regression test added.

## PHS cipher-header negatives (2026-11-29)

Scanned all five GTL PHS members for an ISI `crypt_info` signature at byte
offsets 0..64 (none matched any known `GAMES` signature), for the JCA magic
`0fb1ffff` and the gMb wrapper `//[[` (absent from every member), and confirmed
exactly one member lacks a PAR2 packet entirely — the opaque 13,064-byte
`PHYSICS.PHS`. gzip-like byte sequences inside the large members do not
decompress and are chance occurrences. The PHS cipher remains unidentified;
full-tier guard test added.

## f0 is not a geometry CRC (2026-11-29)

Tested CRC32 of the first vertex's 32 bytes and of the first eight vertices
against each mesh's f0 marker over 20,000+ GTR2 meshes: zero exact matches and
zero 16-bit-half matches, identical to a shuffled baseline. f0 is not a
checksum of geometry bytes.

## CAM inversion is shared across rF1/GTL/GTR2 (2026-11-29) — correction

The earlier note that CAM inversion "matters for rF1→GTR2 conversion" implied
a GTR2-specific difference. Repeating the activation-point test on rF1 and GTL
showed the **same** inversion everywhere: rF1 594/684 cameras favour negation
(median nearest waypoint 15.3 vs 304.6 without), GTL 246/274 (10.1 vs 113.9),
GTR2 336/422 (25.2 vs 110.2). So CAM positions are stored inverted relative to
AIW across the whole local gMotor corpus, and no negation should be introduced
by an rF1→GTR2 converter. Full-tier cross-generation test added.

## CAM activation points confirm the inversion at point level (2026-11-29)

Follow-up on the track-mean result: for 422 cameras across matched GTR2
`.cam`/`.AIW` pairs, the nearest AIW waypoint to the camera's
`ActivationLocation` is a median **25.2** world units away after negating the
camera coordinate, versus **110.2** without negation — a 4.4× improvement.
Negation wins for **336/422 (80%)** cameras, against a ~50% random sign-flip
baseline (20 seeded trials). So the GTR2 CAM/AIW inversion holds per point,
not merely in aggregate. Orientation-field semantics were not tested here.
Full-tier regression test added.

## CAM positions invert AIW world coordinates (2026-11-29)

Verified the guitarmaen CAM/AIW note empirically on 30 GTR2 tracks with
matched `.cam`/`.AIW` file pairs. Using per-track mean positions, camera x and
waypoint x have opposite signs in **27/30 (90%)** tracks versus **53.5%** for
a distribution-preserving shuffle of waypoint means (Pearson r **−0.842**).
The y and z axes show the same inversion (opposite signs 20/30 each, r −0.990
and −0.750), though their weaker magnitude leaves larger offsets. The relation
is therefore a coordinate-frame inversion, not an exact per-point negation —
cameras and waypoints are sampled differently. This matters for rF1→GTR2
track conversion, where CAM positions must be transformed consistently with
AIW. Full-tier permutation-controlled regression test added.

## Template-free GMT container verified (2026-11-29)

All converters currently require a real GTR2 GMT as a structural template.
A minimal new-layout container was synthesized from scratch: zeroed 0x18..0x16C
header region, new magic at 0x08, mesh table at 0x16C, one mesh record with
flag `0x20004011`, a 3-vertex block, a single-block UV block and a 3-index list,
plus an empty material tail. `gmt_format.parse_gmt()` reads it correctly,
`validate_materials.check_gmt()` returns no warnings, and a `relayout_gmt()`
round-trip preserves vertex and UV bytes. Added
`gmt_format.build_synthetic_gmt()` and a full-tier test. Caveat: no materials
or textures are present, so this is a structural fallback/test fixture, not a
render-ready replacement for a real template.

## GTTF 20-byte tail is a track-level finish point (2026-11-30)

Every GTTF payload ends with exactly 20 bytes after the frame grid. Decoding
them as five f32s showed the first two floats are nearly identical for ghosts
recorded on the same track (10 tracks with ≥2 ghosts, median within-track
distance **0.594** world units) but far apart across tracks (median **178.3**
for 1,000 random pairs). They sit close to, but are not identical to, the last
frame's y/z (median offsets 0.007 / 0.124), consistent with a fixed
start/finish-line coordinate. Tail floats 2/3/4 were then decoded: float 3
matches the last frame's heading (median |error| 0.0004 rad vs 0.0026 shuffled),
float 4 matches the last frame's +16 (~0.0003), and float 2 tracks the last
frame's `slot48_low` (|r| 0.993 vs 0.24 shuffled). These are near-copies, not
bit-exact, so the tail is a summary of final car state. Full-tier
permutation-controlled test added.

## Frame-time editor and f32 precision (2026-11-30)

Added `shift_frame_times()` to modify every grid frame's +20 time word while
preserving positions, controls and tail. On sampled ghosts, a +64 s shift
produced per-frame differences accurate to 7.6e-6 s — the expected f32
rounding at session-time magnitudes (values up to ~650 s), not a decoder
error. This confirms the time words are independent f32 fields and can be
edited without disturbing other frame data. Full-tier test added.

## Tiling ratios are weakly enriched in material records (2026-11-30)

Since ratios are material-associated, tested whether each ratio is stored in
the corresponding material record: a mesh's `(k1,k2)` f32 bytes occur in its
material raw bytes in 31.4% of 500 sampled cases, versus 16.0% when the ratios
are replaced by random values drawn from the *same* ratio distribution
(10 seeded trials). This is a real but modest enrichment, not a fixed field:
the ratios were not consistently found at any particular material offset
(e.g. f32 at raw+140 matched only 6% of the time). Recorded as a partial lead;
no material decoder promoted. Full-tier test added.

## GTL replays use IRSR v1.01 (2026-11-30)

The four shipped `GTLSteam/ReplayData/*.Vcr` files use the same gzip/gMb +
IRSR container as GTR2 replays but carry version **1.01** instead of **1.05**.
All four parse with the existing reader (TRK/AIW names, driver, session
seconds) and rewrap byte-identically with `compress_simbin()`. No frame-grid
detection was attempted for them. Full-tier test added.

## GTTF session-field editor (2026-11-30)

With containers reproducible, added `session_field_offset()` and
`set_session_seconds()` to `simbin_events_tool.py`. On all 29 ghosts the
session f32 was located at payload offset 93; editing it changed at most the
four bytes of that float, left every other payload byte unchanged, and the
edited payload rewrapped into a valid container. This is the first verified
payload-level mutation, demonstrating a path toward a ghost writer without
reconstructing frame fields from scratch. Full-tier test added.

## SimBin gzip containers are byte-identically reproducible (2026-11-30)

Compared shipped `.GTT`/`.Vcr` gzip bytes against Python's deterministic
`gzip.GzipFile` output: only header bytes 8/9 differ (XFL/OS `00 02 ff` vs
shipped `00 0b`); the compressed stream and CRC/size trailer are identical.
`gzip_simbin_tool.compress_simbin()` patches those two bytes and reproduces
all 29 ghosts and all 9 replays byte-for-byte. This removes the container
barrier for a future ghost writer (payload semantics are largely decoded).
Full-tier regression test added.

## GTTF path f3 vs AIW attributes and curvature (2026-11-30)

A systematic scan of path f3 against all decoded AIW waypoint attributes
(galpha, widths, dwidths, path fields, perp components, groove_lat,
score_distance) found only chance-level associations (max |r| 0.046).
Curvature computed from consecutive AIW waypoints is a better match: across
27 ghosts median |r| is **0.142** versus **0.068** for shuffled controls,
with 14/27 files above 2× baseline. This complements the earlier path-record
curvature result (0.060 vs 0.019). f3 is curvature-related, but no
brake/throttle semantics are claimed. Full-tier permutation-controlled test
added.

## GTTF path f4 tracks AIW galpha (2026-11-30)

Mapped pre-frame path records to the nearest AIW waypoint of the same track
(within 3 world units) and correlated record field f4 with waypoint attributes.
Across 27 ghosts, |correlation| with `galpha` has median **0.276** versus
**0.085** for distribution-preserving shuffles, with 16/27 files above 3×
baseline. f3 showed only weak path0/path1 associations and other attributes
(width/dwidth/perp) were at chance. This is a genuine AIW↔ghost link —
distinct from the earlier negative about frame slot +36 not being an AIW
surface attribute — but no pedal/surface semantics are claimed. Full-tier
permutation-controlled regression test added.

## GTTF frame time field definitively validated (2026-11-30)

The 29 ghost filenames encode lap times such as `1_23_404` (83.404 s). Frame
field `+20` is an absolute session time with an arbitrary starting offset
(first frame 18–560 s across files), but `last_time − first_time` matches the
filename lap time with median absolute error **0.0023 s**, maximum **0.034 s**,
and all 29 files within 0.05 s. Shuffling the lap-time pairings raises the
median error to **23.59 s**. This settles the time field's units and scale:
it is seconds, and the ghost's lap duration is a span, not the final value.
Full-tier permutation-controlled regression test added.

## f0 bytes do not index material stages (2026-11-29)

Tested whether f0's two bytes are small indices into the mesh's material stage
list or material count. Over 26,125 meshes, the high byte was below the stage
count in 3,935 cases versus **3,937** for a distribution-preserving shuffle of
stage counts — exactly chance. The high byte was below the material count
slightly more often (5,310 vs 4,859), consistent with the already-known mesh-0
distinctness rather than an index relation. No decoder promoted; full-tier
guard test added.

## GTR2 UV streams carry integer tiling ratios (2026-11-29)

A seeded, stratified sample of streams with the `(1,2,3,4,5,6,1)` column
signature showed that columns 2/4/6 are position-derived (median max
|correlation| with world coordinates 0.617 vs 0.200 for shuffles) while
columns 1/3/5/7 are constants or binary flags. In 915/1,980 such meshes,
column 4 and column 6 are **constant multiples** of column 2 across every
vertex, with small per-mesh integer ratios (most often ×5/×8, then ×20/×24 and
×8/×10). A distribution-preserving shuffle of column 2 broke the relation in
0/500 cases. Added `gmt_format.uv_tiling_factors()` and a full-tier test. The
ratios look like texture-tiling factors, but no engine semantics are claimed.

## Mesh flag bit 0x20 selects the UV layout (2026-11-29)

Tabulating `rec[1]` flags against UV block structure over 40,327 GTR2 meshes
found a perfect structural rule: flag bit `0x20` is set if and only if the
mesh uses the two-stream layout (`rec[6] < rec[7] < rec[8]`), with **zero**
exceptions. `0x4011`/`0x20004011`/`0x4015` variants are single-block;
`0x4035`/`0x20004035`/`0x20006035` are two-stream. All 308 converted outputs
in a 100-per-family batch used the single-block form with the bit clear, so
converter flags are consistent with their UV blocks. Full-tier test added.

## GTL meshes are already new-layout (2026-11-29)

Sampled 2,529 GMT members from GTL `.gtl` archives: every one carried the new
GTR2/GTL magic at offset 0x08 and none the old magic at 0x1D4. This confirms
that GTL→GTR2 conversion does not require mesh relayout — only the TRK/GDB/
archive conventions handled by `gtl_to_gtr2.py`. Full-tier test added.

Note: the fresh full-suite run on an older HEAD exceeded the 60-minute shell
timeout and was terminated without a result; it is not cited as verification.

## f0 high byte vs material index: mesh-0 artefact (2026-11-29)

A byte-level test found the f0 high byte equals the mesh's material index in
**13.3%** of 26,125 meshes versus **4.2%** for a distribution-preserving
shuffle — apparently a material link. Splitting by mesh ordinal showed the
association is almost entirely mesh 0: 44.9% of mesh-0 markers have high byte 0
and material index 0, while later meshes match at only 0.5–2.1%. No material
index mapping exists; the corpus-wide signal is just the already-known
mesh-0 distinctness. Full-tier guard test added.

## f0 marker semantics do not transfer to Volvo/Race07 (2026-11-29)

Attempted to cross-validate the f0 byte-pair rule on JCA-decrypted Volvo and
Race07 GMTs. It did not hold (Volvo 5.5% consecutive even pairs, Race07 28%,
versus 60% in GTR2). Inspection showed the reason: the first u32 at rec[4] in
those games is a float-shaped value (e.g. `0xBE49F597`), not the small
per-mesh marker seen in GTR2 (343/343 sampled GTR2 meshes had <100,000 there).
`gmt_format.mesh_marker()` and all f0 findings are therefore scoped to the
GTR2/GTL layout only; sibling games use a different base-vertex layout.

## UV layout confirmed across sibling SimBin games (2026-11-29)

Decrypted JCA-encrypted GMTs from Volvo and Race07 with `jca_crypt.py`
(Volvo key for both) and parsed them with `gmt_format`. In 300 sampled files
per game, all 300 exposed a `vc*32` UV block at the expected record offset,
and 257 (Volvo) / 264 (Race07) had one of the two dominant GTR2 signatures
`(1,2,0,0,0,0,0)` or `(1,2,1,2,1,2,1)`. A per-record shuffle of the eight
floors (preserving each vertex's value multiset) reduced the match to 0/60,
confirming the signatures are structural. This independently validates the
UV layout used by the converters. Full-tier test added.

## VRL UV transfer completed (2026-11-29)

The gap recorded below was closed: `vrl_to_gmt.prepare_geometry_with_uvs()`
expands each shared vertex into one vertex per corner, so every corner keeps
its own UV, and re-quads the triangle list in the expanded index space.
`vrl_to_gmt()` writes those UVs into the GTR2 UV block and `verify_gmt()`
now checks them with `verify_gmt_uvs()`. 25/25 sampled conversions round-trip
UVs byte-exactly, while shuffled UVs fail in >90% of meshes. Full-tier
distribution-preserving regression test added.

## VRL UV transfer remains a gap (2026-11-29)

VRL files expose a per-corner `coords` array verified as UV-like by
`vrl_uv_quad_score()` (1,046 files, mean 0.753 vs 0.271 shuffled). However
those coordinates are indexed per corner, not per vertex: in 300 sampled
VRL files only 36 have `len(coords) == vertex_count`, and **none** has an
identity index buffer. Transferring them therefore requires splitting shared
vertices at UV seams and rebasing every triangle index, which would also
invalidate the current `verify_gmt_geometry()` checks. Left as an explicit
gap rather than shipping a speculative mapping.

## GTR1 UV fields identified and transferred (2026-11-29)

Previously `gtr1_to_gmt` deliberately dropped GTR1 UVs as unconfirmed.
Inspecting 12-float GTR1 vertex records showed fields 8 and 11 are exactly
zero in **20,017/20,017** sampled vertices, while fields 9/10 hold UV-like
values (91.7% / 82.6% within [-2, 2], the rest tiled world-space coordinates;
e.g. AMBULANCE00 `(0.0306, -0.6735)`, ARMCO1 `(3.0, -97.77)`). Added
`uvs_from_gtr1()` and extended `vrl_to_gmt.build_gmt()` with an optional UV
block written in the dominant real-GTR2 layout (u at +4, v at +8, no count
lead). 30/30 sampled GTR1 conversions reproduce source UVs byte-exactly and
the batch `gtr1` family now emits UV streams (e.g. 328 vertices -> 10,496
bytes). Full-tier regression test added. VRL UV transfer was completed in a later step (see above).

## GTR2 stream3 column 0 vs f0: sparsity artefact (2026-11-29)

A per-vertex correlation between stream3's first f32 column and the base
vertex f0 reported a suspicious median |r| = **1.000** (vs 0.008 shuffled).
Inspection showed both fields are nonzero **only at vertex 0** in essentially
every mesh (stream3 col 0: 1,701/1,731; f0: all sampled meshes), so the
correlation is entirely a two-point sparsity artefact. Across meshes, the
vertex-0 values themselves are essentially unrelated (|r| 0.047 vs 0.006
permuted). Recorded as a negative methodology lesson: check sparsity before
trusting a per-vertex correlation. Full-tier regression test added.

## GTR2 two-stream meshes duplicate one UV pair (2026-11-29)

Compared stream2 and stream3 on 1,731 two-stream GTR2 meshes. Stream3's
columns 3..7 are exactly zero in **all** meshes, and its columns 1/2 agree
with stream2's on a per-vertex basis in **1,662 (96%)** meshes. Median
agreement is 1.0 versus 0.023 when stream3 rows are shuffled within each mesh
(a distribution-preserving baseline). Stream3's remaining column 0 is a
distinct per-vertex value but shows no world-position relationship (median
max |correlation| 0.135, none above 0.9). Interpretation: the two streams
carry one UV-like pair, largely duplicated — not two independent UV sets.
Added `gmt_format.stream_cross_agreement()` and a full-tier test.

## GTR2 UV block layouts and converter misalignment FIXED (2026-11-29)

Cross-checking converted files against real GTR2 exposed two related problems:
1. `parse_gmt()` only exposed a stream when `rec[7] > rec[6]`, missing the
   dominant layout (~86%): a single `vc*32` block at `rec[6]` ending at the
   index offset. The parser now exposes both layouts.
2. `old_to_new_semantic()` wrote a 4-byte count lead before the UV block and
   put UVs at `+8/+12`, whereas real GTR2 single-block UVs are at `+4/+8`
   with no lead (verified on GOALPOST: `[0, 3.998, -0.002, 0, ...]`). This
   made converted files structurally invalid for the engine's UV reader and
   broke offline UV equality. Removed the lead, moved UVs to `+4/+8`, and set
   the gtr2 schema `uv_sub_off` to 0 in `gmt_semantic.py` and
   `validate_conversion.py`.

After the fix, converted UV blocks are exactly `vc*32` bytes with the dominant
real signature `(1,2,0,0,0,0,0)`, and 5/5 validator tests plus the quick suite
pass. Full-tier regression test added.

## GTR2 stream column signature (2026-11-29)

Extending the stream-pattern study: a column-signature analysis of 2,601
GTR2 meshes shows the final f32 column repeats the second in **2,594**
(99.73%). The dominant signature `(1,2,1,2,1,2,1)` (747/1,601) is the
three-value pattern; other recurring signatures are `(1,2,3,4,5,6,1)` (542)
and `(1,2,3,4,3,4,1)` (139). Seven TRACKnn meshes are the only cases where
column 7 does not equal column 1. Added `gmt_format.stream_column_signature()`
and a full-tier regression test; no UV semantics claimed.

## GTR2 extra vertex streams: located, not decoded (2026-11-29)

Investigated where GTR2 GMTs keep UV-like data. Meshes whose 108-byte record
has `rec[6] < rec[7] < rec[8]` carry two extra 32-byte-per-vertex streams in
addition to the 32-byte base vertices (confirmed on ROADPITADDON, BRIDGE1,
FENCE*, GRDR* etc. in Anderstorp). Each extra record is 8 f32s. A strong
structural pattern holds in **750/1605 (46.7%)** meshes: every record is
`[U, S, V, S, V, S, V, S]`, i.e. columns 1/3/5/7 are equal and columns 2/4/6
are equal — only three distinct values per vertex. A column-wise shuffle that
preserves each column's distribution drops the pattern rate to 0%.

On ROADPITADDON specifically, column 2 is a planar world-x projection
(correlation 1.0) and columns 4/6 are exactly ×10 and ×15 copies with tiling
factors 10/15 in columns 3/5. This does **not** generalise: only 39/447 sampled
meshes have any stream column correlating >0.9 with world position. So these
streams are a credible UV/scale carrier, but their semantics are still
unassigned — added `gmt_format.decode_stream_records()` plus a full-tier
permutation-controlled test, no UV correctness claim.

## f0 is a consecutive byte pair, not a hash (2026-11-29)

A byte-level decomposition of 30,000 GTR2/GTL f0 markers found that in 69.6%
both u16 halves are byte-sized (bytes 1 and 3 zero), so the payload lives in
byte 0 and byte 2. The classic "near-equal halves" invariant resolves to a
**consecutive-integer** relation: `hi - lo = +1` in 37.8% of all markers, and
restricted to even low bytes `hi == lo + 1` in **60.3%** vs **0.8%** for a
distribution-preserving shuffle of the same high bytes (odd low bytes most
often pair with `hi = lo - 3`). This replaces the vague "near-equal halves"
description with a concrete structural rule and rules out hash-like encodings.
Added `gmt_format.f0_byte_pair()` and a full-tier permutation-controlled test.

## Debug-artifact sweep across ISIMotor installs (2026-11-29)

Checked all `../` game installs for leftover development/debug material:
- no `.pdb`, linker `.map`, `.idb`, `.ilk` or COFF symbol tables in game EXEs;
- `GTR2.exe`, `GTR2Dedicated.exe`, `Race_Steam.exe` and `Volvo.exe` embed RSDS
  CodeView references with build paths (GTR2: `…\copperhead\…\GTR2.pdb`,
  GUID `a274677040fef54fbbdf2a81da5bcd3d`, age 16) but the PDBs are not shipped;
- `GTR2.exe` exports only five C++ symbols (`Game::Init`, `PlayerFile::Create`,
  etc.) and its RTTI names are UI classes; no ghost/telemetry data structures;
- the numerous `.map` files in F1 2000/F1CS 2000 are **audio** maps, not linker maps.

So no usable debug symbol source was found locally. Full-tier regression test added.

## GTTF +36 exponent tracks path demand (2026-11-29)

Slot +36's value is a heavily quantized lattice (base ±34 with `4^k` steps).
Taking `k = log2(|value|/34)/2` reveals a strong relationship to path `f4`:
median correlation **0.274** across 29 ghosts vs **0.016** for shuffled levels,
and the sign is positive in **all 29** files. The *raw* +36 value had shown no
correlation with speed/steering/curvature; the information is in its exponent,
which likely encodes a magnitude/demand scale. Exact units remain unknown.
Full-tier permutation-controlled regression test added.

## GTR2Dedicated.exe ghost serializer search (2026-11-29)

`GTR2Dedicated.exe` contains `GTTF` at RVA `0x6996f8` with a pointer table at
`0x6e8d90` and the same validator/fixup functions as `GTR2.exe` (`0x526dc0` /
`0x52a300`). A scan of the ghost-code range for `push 0x3f` near a vtable read
call found **zero** sites, matching the `GTR2.exe` result. No frame serializer
is recoverable statically from either build. Full-tier regression test added.

## GTTF path control complementarity is frame-level only (2026-11-29)

Re-tested f3/f4 on the 24-byte source path records rather than the mapped
frames: median `f3+f4` is **0.847** (not 1.0), median correlation **−0.136**
vs **0.009** permuted, and `f3 == 0` in 68% of records. So the near-perfect
frame-level complementarity is introduced by the frame/record mapping (or by
frame-side interpolation), not present verbatim in the path stream. This
qualifies the earlier brake/throttle-share interpretation; no pedal semantics
are claimed. Full-tier regression test added.

## GTTF path controls are complementary (2026-11-29)

Across all 29 ghosts, path `f3` and `f4` are strongly anti-correlated: median Pearson **−0.59** vs **−0.001** for distribution-preserving shuffles. `f3 == 0` in a median 77.4% of frames, and the median of `f3 + f4` is exactly **1.0**. This strongly suggests two complementary normalized shares (e.g. brake/throttle), but the earlier acceleration negatives prevent claiming literal pedal positions. Full-tier regression test added.

## GTTF byte +31 tracks engine speed (2026-11-29)

A multi-field permutation-controlled matrix showed the varying byte at +31
has its strongest association with `engine_speed` (frame +32): median |r|
**0.263** vs **0.021** for shuffles across 29 ghosts, with a mostly negative
sign (20/29). Because +32 has known gear-band clamps, the test was repeated
after dropping the outer 2% of engine values; the signal survives at **0.198**
vs **0.022** (22/29 files above 3× baseline), so it is not a saturation
artefact. Path y (0.164) and f4 (0.126) are weaker companions. A follow-up
test of the "monotonic code" hypothesis (rank correlation between the 93
observed byte values and their median engine speeds) gave only 0.311 vs 0.096
permuted, 16/29 files above 3× — both byte clusters (0x12–0x1a and 0x6b–0x70)
occur at similar engine speeds, so the byte is not a deterministic RPM code.
The low-24-bit partner `0x002000` stays constant, confirming a structured
bitfield whose encoding remains unexplained. Two further negatives: a 6-band
gear clustering of engine speed explains only 2.8% of the byte's variance
(0.3% shuffled), and it has no usable correlation with engine acceleration,
heading rate, speed change or speed squared (all |r| <= 0.026 vs ~0.015
permuted). Full-tier test added.

## GTTF frame marker prefix constant (2026-11-28)

Across all 29 ghosts and 44,631 frames, bytes `+24..+30` are exactly
`01 00 00 34 00 20 00` (one distinct value per position). Only byte `+31`
varies. This makes the 7-byte prefix a reliable frame-grid validator, and
explains why earlier byte-statistics work treated `+31` separately. Full-tier
regression test added.

## GTTF byte +31 tracks path elevation (2026-11-28)

The `+28` u32 has constant low bits `0x00200000`; its high byte (frame offset `+31`) was previously called a "car-independent exponent artifact". A matrix against path-record fields shows it tracks the path's world y coordinate: median |correlation| **0.164** vs **0.020** permuted across 29 ghosts, 23/29 above 3× baseline; it also tracks path f4 (0.123 vs 0.017). So byte +31 carries real track-state information, not just a packing exponent. Full-tier regression test added.

## GTTF path f4 vs curvature (2026-11-28)

Complementary to f3: path `f4` has median |correlation| with racing-line curvature **0.072** vs **0.020** permuted across 29 ghosts, and the signed correlation is positive in 23/29 files (median +0.045). This is a reproducible association but does not support a simple "throttle decreases in corners" reading; curvature, gear and engine band are confounded on this reference line. Full-tier regression test added.

## GTTF path f3 vs curvature (2026-11-28)

Using curvature computed from the 24-byte path records' own x/z points, path `f3` shows a mild but reproducible association: median |r| **0.060** vs **0.019** permuted across 29 ghosts, with 20/29 files above 2× baseline. Curvature is higher where `f3 > 0.9` (median 0.265 vs 0.216 overall). This is consistent with a brake-like channel but does not establish pedal semantics. Full-tier regression test added.

## GTTF slot +48 vs path f3 without clamps (2026-11-28)

Re-tested slot +48's packed halves against path-control fields after removing frames where `+16` saturates (the source of the earlier spurious +8/+16 coupling):
- low i16 half vs path f3: median |r| **0.101** vs **0.022** permuted across 29 ghosts, 17/29 files above 3× baseline;
- high i16 half vs path f4: 0.062 vs 0.024 — weak.

So +48's low half has a genuine, though modest, steering/path-f3 association independent of saturation. Full-tier regression test added.

## GTTF frame slots vs path fields matrix (2026-11-28)

A permutation-controlled matrix across 15 frame slots and 6 path-record fields confirmed the direct mappings and revealed one new relation:
- frame +0 ↔ path y (r≈1.000), +4 ↔ path z (r≈1.000), +12 ↔ path heading (r≈0.96) — all with permuted baselines ≈0.02;
- frame +20 (timestamp) ↔ path x (field 5): median |r| **0.568** vs **0.017** permuted — x is the longitudinal progress coordinate used by playback;
- frame +32 ↔ path f4 (engine-related) r≈0.51; no other slot/field pair stands out.

Full-tier regression test added for the time/x relation.

## GTTF heading comes from the path records (2026-11-28)

Directly comparing each ghost frame's `+12` heading with the heading field of its matched 24-byte path record gives median circular coherence **0.992** across all 29 ghosts vs **0.024** for permuted path headings. This is the strongest heading result so far and shows the frame's heading is copied from / derived directly from the reference path record, not independently reconstructed from frame-to-frame motion. Full-tier permutation-controlled regression test added.

## GTTF path record count ratio (2026-11-28)

Across all 29 ghosts, the number of 63-byte frames divided by the number of 24-byte pre-frame path records is bounded: median **2.44**, range **1.93–3.49** (10th–90th percentile 2.08–3.05). This is a useful structural validator for path-grid detection, not a semantic decoding. Full-tier regression test added.

## GTTF path records: heading validates the x field (2026-11-28)

The 24-byte racing-line record's third float is a heading following the same convention as ghost `+12`: **`heading = atan2(dx, dz)`** using its own x (field 5) and z (field 1). Median circular coherence across 15 ghosts is **0.973** vs **0.086** permuted; 13/15 files prefer this sign/axis convention outright. This independently confirms that field 5 is world x and removes the earlier ambiguity about the missing coordinate. Full-tier regression test added.

## GTTF path records f3/f4: control-like channels (2026-11-28)

The 24-byte racing-line records' 4th and 5th floats are normalized [0,1] channels with many exact 0.0/1.0 values. `read_frames()` now exposes them as `path_f3` / `path_f4` using the same monotone path mapping as x. Across all 29 ghosts (permutation baselines in parentheses):

- `path_f4` vs engine `+32`: median |r| **0.502** (0.020 permuted) — ~25×;
- `path_f3` vs steering `+8`: median |r| **0.097** (0.015 permuted) — ~6×;
- neither channel tracks longitudinal acceleration from reconstructed speed (|r| < 0.01).

These are likely driver/target inputs on the reference racing line rather than the ghost's own controls; exact semantics (throttle/brake/gear) are **not** claimed. Full-tier permutation-controlled regression test added.

## GTTF missing x RECONSTRUCTED from pre-frame path records (2026-11-28)

**Breakthrough.** The 63-byte frame records store only y/z (and steering), but the **24-byte records immediately preceding the frame grid** contain a path with six f32 fields: `(y, z, heading, f3, f4, x)`. The 6th float is the missing world x. `find_preframe_records()` and `reconstruct_frame_x()` map frames onto this path in chronological order (monotone index search, small look-back window) and add `frame["x"]` / `frame["world_position"]`.

Evidence across all 29 GTR2 ghosts:
- nearest-record y/z distance median **0.73 m**;
- reconstructed world speed median **30.0 m/s** (per-file range 16.1–49.9 m/s), versus **~0.1 m/s** when x was absent;
- reconstructed x span agrees with AIW x span within 0.6–1.4× (median) across matched tracks;
- the records' 3rd float is a heading in `[-π, π]` coherent with the (y,z) path tangent (best circular coherence 0.652), confirming they are a racing-line path, not padding.

This resolves the long-standing "position transform" blocker: earlier failures came from treating the 63-byte triple as world XYZ. Full-tier regression test added.

## GTTF header fields recovered from GTR2.exe (2026-11-27)

Static analysis of the unpacked `GTR2.exe` (`.text` at RVA `0x401000`) located the `GTTF`/`IRSR` pointer table at RVA `0x6ead90`, the validator `fcn.00527000` (version constants 1.0/1.02/1.03/1.04/1.05) and the reader `fcn.0052be30` / writer `fcn.0052a540`. The reader's field order confirms that the five bytes after the TRK/AIW filenames are `u8, u8, f32, u8, u32` — now exposed as `simbin_events_tool.EventFile.flags_a/flags_b/session_seconds/flags_c/flags_u`.

Across all 42 local event files (29 GTTF + 13 IRSR) the float takes only **36000 / 43200 / 46800**, exactly 10/12/13 hours in seconds — consistent with a session time limit (strong inference, not runtime-confirmed). The GTTF `+8` steering relationship and the rest of the frame field work remain separate. Full-tier regression test added.

## GTR2 UV extra-block negative (2026-11-28)

Sampled GTR2 meshes (n>100) expose **no** 16-byte extra vertex block (`has_extra_vertex_block` false for all); UV-like data in old-layout GSC meshes therefore cannot be validated against a parsed GTR2 UV representation. The GSC→GTR2 converter preserves the old UV region verbatim but no correctness claim is made. Full-tier regression test added.

## GTR2 mesh-0 f0 vs member size (2026-11-28)

Mesh-0 f0 half-sum also grows weakly with the GMT member's byte length: Pearson r **0.159** vs **0.009** for distribution-preserving permuted sizes (n=8,000). Like the mesh-count relation, this suggests a file-level/scene-level component in mesh 0's identifier. Full-tier regression test added.

## GTR2 mesh-0 f0 vs mesh count (2026-11-28)

Mesh-0's f0 half-sum grows weakly but significantly with the number of meshes in the GMT: Pearson r ≈ **0.13–0.14** vs **0.009** for distribution-preserving permuted counts (n≈6,000). This is consistent with mesh 0 carrying a file-level/scene-level identifier related to mesh population. Full-tier regression test added.

## GTR2 f0: mesh 0 is structurally distinct (2026-11-28)

For the first mesh in each GMT, f0's halves are much larger and further apart:
- mesh 0: median halves **542 / 678**, median `|high-low|` **314** (n=5,496);
- later meshes: median halves **63 / 63**, median delta **1** (n=14,509).

The median delta difference (313) vs 0.1 under a distribution-preserving permutation baseline makes this a strong validator. It explains the earlier "index 0 threshold" result: mesh 0 carries a different kind of identifier than subsequent meshes. Full-tier regression test added.

## Clarification: f0 "material index" is the mesh ordinal (2026-11-28)

In 14,998 of 15,003 sampled meshes (99.97%), `GmtMeshRecord.material_index` equals the mesh's ordinal within the GMT. Therefore the f0 half-delta / half-sum / sign invariants described below are relationships to the **mesh's position in the GMT mesh list**, not to an independent material identifier. The wording "material index" in earlier notes should be read as "mesh ordinal (= material index in practice)". Full-tier regression test added.

## Correction: f0 half vs material index was a baseline artifact (2026-11-28)

A probe appeared to show a half of f0 equal to the local material index far above chance (2.4% vs 0.01%). That baseline shuffled **uniform** indices, while real indices are heavily skewed toward 0 and small values. Re-running with a distribution-preserving shuffle gives **278 observed vs 239 expected** matches — at chance. No relationship; no test was retained.

## Correction: GTTF +8/+16 "steering coupling" is a clamp artifact (2026-11-28)

The earlier reported median |correlation| 0.585 between frame `+8` and `+16` was **driven by frames where +16 saturates at ±1.0**. Recomputing per file:
- all frames: median |r| **0.675**;
- excluding `|+16| > 0.99`: median |r| **0.146** (≈4.6× lower).

Spearman rank correlation is also low (median 0.145), confirming there is no strong monotone relationship. The earlier sign-vs-heading-trend observation is likewise driven by the saturation pattern. The new regression test asserts the drop after removing clamped frames. The `+48`-low ↔ `+8` and path-control ↔ `+8` associations (which use `+8` directly, not clamped `+16`) are unaffected.

## GTTF slots +48/+52/+56/+60: car-independence negative (2026-11-26)

Across all 31 GTT files, every one of these slots reaches sentinel-like u32 maxima (>4.0e9 in **31/31** files for each slot; medians 4.295e9 / 4.295e9 / 4.295e8 / 4.291e9). Ferrari F550 and BMW M3 show no distinguishing ceiling or range. Slot +52 has small clusters near `0x00000000` and `0x00800000` (sign-bit artifact) in both cars, together covering a median 16.7% of frames (range 5.3–30.6%) — far too little to be a bounded physical signal. The earlier per-byte smoothness and throttle/brake/acceleration negatives for these slots stand; no car-calibrated semantics promoted. Regression test added (`test_gttf_slots48_52_56_60_no_car_ceiling`).

## GTTF slot +44: car-independence negative (2026-11-26)

Across all 31 GTT files, slot +44 has **no car-specific ceiling** (every file's raw u32 exceeds 4.2B; F550 and BMW M3 both span ~1.4e7..4.29e9). The byte44==byte46 structure is shared: per-file equality fraction median 0.83 (range 0.752–0.901), dominant byte pairs 224–238 for both cars. The earlier packed-half/acceleration/heading-rate negatives therefore stand; this slot is not a bounded kinematic or car-calibrated field. Regression test added (`test_gttf_slot44_no_car_ceiling`); no semantic promoted.

## GTTF slot +7: car-independent exponent artifact (2026-11-26)

Across all 31 GTT files, the varying byte +31 of the `00 20 00 XX` u32 at +28 has mode **64 in 28 files** and 65 in the other 3, per-file medians 63–66 (overall median 64), and 93 distinct values for the Ferrari F550 vs 59 for the BMW M3 — i.e. no car-specific invariant separates the two cars (both clusters centre on the same 0x40/0x41 exponent byte). This corroborates the earlier conclusion that slot +7 is a fixed-low-byte integer/float exponent artifact rather than a car-dependent physical signal; no semantic promoted. `test_gttf_slot7_byte31_exponent_artifact` locks the distribution bounds.

## GTTF slot +40: counter/state negative (2026-11-26)

Across all 31 GTT files the raw u32 at +40 is neither a monotonic counter nor a stable two-state flag: monotonic fraction median 0.555 (range 0.503–0.586), |correlation with frame time| median 0.025 (max 0.119), and the two exponent clusters (raw >2³⁰ vs lower) flip in a median 26.6% of consecutive frames (range 0.4–29.6%). The hi fraction varies by file (0.475–0.997), so it is not a car-invariant state either. The earlier quantized-float kinematics negatives for this slot stand; `simbin_events_tool.frame_s40_word()` and a regression test lock in these bounds. No semantic promoted.

## GTR2 vertex f0: raw-record hashes negative (2026-11-27)

Tested CRC32 / CRC32-high / Adler32 / FNV-1a / MD5-first-2 over the **raw** material record and all stage record bytes (20,005 meshes). Halfword matches were 0 / 0 / 6 / 0 / 3 versus permutation baselines 0.6 / 1 / 7.8 / 0.6 / 1.6 — all at chance. With the name-hash, count, offset and stage-type negatives, f0 is not derivable from any GMT-local field tested; it remains an external identifier. Full-tier regression test added.

## GTR2 vertex f0: set-hash encodings negative (2026-11-27)

Tested order-independent hash constructions from normalized material/stage name sets on 20,000 meshes: CRC32 / Adler32 / MD5-first-2 of the sorted, `'|'`-joined set plus XOR and sum of per-name CRC16 halves. Matches to f0 halfwords were 3 / 2 / 0 / 3 / 4 respectively — chance level (permutation baselines 2.4 / 0 / 0.2 / 2 / 2). So the material-name grouping found above is not produced by a simple set hash; f0 likely encodes an external ID unrelated to a derivable string hash. Full-tier regression test added.

## GTR2 f0 is not archive-scoped (2026-11-28)

Adding the source archive stem to the normalized material/stage name set lowers f0 agreement from 28.7% to **16.2%** of 7,481 multi-member groups (permuted baseline 0.1%). So f0 is not a hash of "archive + material name"; it is more consistent with an identifier assigned outside the GMT files. Full-tier regression test added.

## GTR2 shader lookup helpers are not f0 consumers (2026-11-28)

Disassembled `fcn.005e54e0` and `fcn.005e55e0`, called from the mesh fixup `fcn.005e9ab0` with stage names such as `L0DIFFUSET0`. Both take a **small stage-type enum (1/2/3 or 0x63)** selecting one of three arrays at object offsets `0x110`/`0x21c`/`0x328`, plus a name string; neither takes or derives from the per-vertex f0 marker. Corpus check: f0 spans **4,364 distinct values** in 20,005 vertices, with only 3.1% equal to one of the four enum values — so f0 is not a shader/material registry index of this kind. Full-tier regression test added.

## GTR2 f0 is not a shader-registry index (2026-11-28)

Code-first check around `fcn.005e9ab0` and the shipped shader members:
- GTR2/GTL/BMW installs contain only **94 distinct `.psh`/`.vsh` names** (57/37 per game), far fewer than f0's 16-bit half range (>1,000 distinct halves, max ≫ 10× the registry size).
- CRC32/CRC32-high/FNV/sum of individual stage and material names, including ordered stage records, match f0 halves only at permutation chance.
- `fcn.005e54e0`/`fcn.005e55e0` select only a 1/2/3/99 stage-type enum, not an f0-derived ID.

So the paired near-equal halves are not indices or simple hashes of shipped shaders; they most plausibly originate from an external authoring/material identifier. Full-tier regression test added.

## GTR2 f0 half-sum invariant (2026-11-28)

The mean of f0's two 16-bit halves also decreases with the local material index: Pearson r = **−0.264** (n≈12,000) vs **0.006** for distribution-preserving permuted indices. This complements the half-delta and sign invariants and confirms that both components of the pair, not just their difference, depend on the material slot. Full-tier regression test added.

## GTR2 f0 paired-ID sign invariant (2026-11-28)

The sign of `high - low` is also structured:
- within cross-corpus material families, the sign is identical in **53.4%** of 2,376 multi-member groups vs **18.4%** under a distribution-preserving permutation baseline;
- material-index-0 meshes skew **negative** (26.2% positive) while index>0 meshes skew positive (58.6%), difference **−0.325** vs 0.007 permuted.

Together with the near-equality and delta-threshold results, f0's two halves behave like a pair of related authoring IDs whose ordering depends on the material slot. Exact source remains unknown. Full-tier permutation-controlled regression test added.

## GTR2 f0 half-delta: material-index-0 threshold (2026-11-28)

The correlation above is dominated by a sharp threshold: in multi-material meshes, `|high-low| <= 1` occurs in only **13.8%** of material-index-0 meshes but **61.5%** of index>0 meshes (difference −0.477 vs 0.009 under distribution-preserving permutation). Median delta is 747 for index 0 versus 1 for higher indices. So f0's paired IDs are much closer together when the mesh uses a later material slot. Full-tier regression test added.

## GTR2 f0 half-delta tracks material index (2026-11-28)

Within multi-material meshes, `|high-low|` of f0 decreases as the mesh's local material index increases: Pearson r = **−0.2125** (n=15,001) vs **0.004** for distribution-preserving permuted indices. It also tracks vertex count weakly (r≈0.10) and inversely tracks material count (r≈−0.12). No semantic claim is made — the paired IDs diverge more for early material slots — but this is a verified structural relationship usable as a validator. Full-tier regression test added.

## GTR2 f0 halves are individually family-stable (2026-11-28)

Across 3,153 cross-corpus groups sharing an identical normalized material/stage name set (37,814 records):
- low half identical within a family: **16.3%** (permuted 0.2%);
- high half identical within a family: **17.3%** (permuted 0.5%);
- both halves identical: 16.2%.

So the two near-equal 16-bit components are separately stable per material family — consistent with a *pair of related authoring IDs* (e.g. paired shader/material slots) rather than one value being derived from the other at load time. Full-tier permutation-controlled regression test added.

## GTR2 f0 packs two nearly-equal 16-bit identifiers (2026-11-28)

Across 30,000 mesh markers, the low and high u16 halves of f0 are nearly equal:
- `|high-low| <= 0`: 1.8%; `<=1`: **50.2%**; `<=2`: 58.3%; `<=4`: 74.8%; `<=8`: 77.6%.
- median `|high-low|` = 1; permutation baseline for `<=1` is 1.4% vs 49.2% observed (~35×).
- Typical values are pairs like 0x8a4/0x8a5, 0x9d7/0x9d4, 0x751/0x753.

This strongly suggests f0 is **two closely related 16-bit identifiers** (e.g. paired material/shader or vertex/pixel shader IDs) rather than one arbitrary number. It is consistent with the material-name and raw-record associations, but no simple hash of a single name reproduces the halves. Full-tier permutation-controlled regression test added.

## GTR2 vertex f0: code trace and material-record association (2026-11-28)

Traced the GTR2.exe GMT loader (`fcn.005d68d0`, located via the "Error reading mesh from GMT file" string) and its mesh/shader fixup (`fcn.005e9ab0`, "Could not find shader %s for mesh %s"). The loader relocates mesh records and looks up stage shaders by name (`L0DIFFUSET0`, `L0NOLIGHTINGT0`, …), but no code path that assigns the per-vertex f0 marker was identified — the marker appears to be preserved from the source file rather than computed on load.

Quantified association instead:
- meshes with **identical normalized material/stage name sets** share an f0 marker in **28.7%** of 6,036 multi-member groups, vs **0.1%** permuted;
- conditioning on **identical raw material+stage records**, P(f0 equal) = **0.347**; when raw records differ, P(f0 equal) = **0.036** — a **~10×** association.

So f0 is strongly tied to material identity but not derivable from the tested hashes; a file-specific/external component remains. Two full-tier regression tests added.

## GTR2 vertex f0: material-name group signal (2026-11-27)

A permutation-controlled test on 74,547 mesh records from GTR2/GTL/BMW found that meshes sharing an f0 marker are **~60× more likely** to share a *rare* normalized material/stage-name hash (8.06% of cross-family same-marker pairs vs 0.13% permuted; exact hash-set agreement 7.58% vs 0.09%). However, no simple hash of a single name reproduces the marker halfwords (CRC32/CRC32-high/Adler/FNV/djb2/MD5/sum all at or below permutation baseline). So f0 groups meshes by material/stage identity — consistent with an external material identifier — but the exact encoding is still unknown. Full-tier regression test added (20k-row sample).

## GTR2 vertex f0: counts/bbox identifiers negative (2026-11-27)

Across 8,003 markers from GTR2/GTL meshes, neither halfword matches material count, stage count, per-axis bounding-box spans (×1/10/100) or bounding-box diagonal (×1/10/100) more than chance: **1,019** observed matches vs **1,057** mean permuted matches (range 1,020–1,110; average 12.8 candidate values per marker). With the earlier material-offset/name-hash/stage-type negatives, no GMT-internal field explains f0; its cross-corpus family invariance points to an external identifier. Full-tier regression test added.

## GTR2 vertex f0: stage-type "matches" are a small-integer artifact (2026-11-27)

A naive check of 3,006 markers found 478 halfword matches against stage types / `tail_u32_64` / `tail_u32_65`, which looked significant versus a uniform-16-bit chance estimate (1.1). The correct null accounts for the fact that both f0 halves and stage types are small integers (stage type sets average 2.5 values): a permutation test that shuffles stage-type sets between meshes gives **434** matches versus **440** observed — no signal. Combined with the earlier material-offset/name-hash negatives, no stage-derived interpretation of f0 is supported. Full-tier regression test added.

## GTR2 vertex f0: material-derived hypotheses negated (2026-11-26)

Across 3,006 markers from 25 GTR2/GTL mesh archives, neither halfword matches: absolute material record offset, offset relative to the object list, stage-string offset (`+152`), CRC32 of the material name, byte-sum of the material name, or the name's first u16 — 2/3,006 chance matches total (0.07%) and 0 for the offset/stage/CRC variants. Combined with the cross-corpus/LOD-family invariance, f0 behaves like an abstract identifier of the source material/mesh setup, but not any direct offset, string hash or index derivable from the GMT itself. Full-tier regression test added; encoding unresolved.

## GTR2 vertex f0: cross-corpus invariant (2026-11-26)

Comparing 703 identically named mesh families present in two or three of GTR2Steam / GTLSteam / BMWM3Challenge (23,816 mesh members scanned), **298/703 (42.4%)** have byte-identical ordered f0 marker lists across corpora, vs **1.1%** under randomized family grouping. Examples: `ads`, `fuelrigrr`, `moon`, `night` are identical in all details; `ambulance` differs only in mesh-0's marker (`0x0` vs `0xbcf4007c`) while the remaining three mesh markers match exactly. Thus f0 markers are largely determined by mesh family/material setup and survive preservation across games; mesh-0's marker can still be file-specific. Full-tier regression test added (63 s); the halfword encoding itself remains unresolved.

## GTR2 vertex f0: LOD-family consistency (2026-11-26)

New invariant from a 500-file GTR2/GTL mesh sweep: among LOD/number-variant groups whose members each have ≥2 submeshes, **11/37 (29.7%)** share an *identical ordered f0 marker list* (e.g. `AMBULANCE00/01/N01.GMT` all carry `0, 0xa0009e, 0x8a008d, 0xae00af`), versus a 0% baseline under randomized grouping. Thus f0 encodes something tied to the mesh family/material setup rather than per-file or per-LOD state — a refinement of the earlier "per-mesh marker" finding. Exact halfword matches to `material_index` remain below 25% of markers in the same sweep, so the specific encoding is still unresolved. Full-tier regression test added.

## SCE embedded bounds vs GTR2 targets (2026-11-27)

Cross-checked `SCE_EMBEDDED_NUMERIC_BOUNDS` against the GTR2 target validators: SCE `.hdv` shares 19 keys with `HDC_NUMERIC_BOUNDS` but only **3** have source ranges inside the target (16 incompatible: e.g. `bumptravel` −0.085..0.026 vs −0.12..−0.02, `pressuresetting` 1..50 vs 30..65, `braketorque` 0..4800 vs 1017..4000). SCE `.tbc` shares 15 keys with `TYR_NUMERIC_BOUNDS` with only **4** compatible (11 incompatible: `radius` 0.125..0.365 vs 0.249..0.355, `damper` 360..1100 vs 1000..3850, `step` 0.0033..0.05 vs constant 0.009). This extends the earlier Marcas negative: a GSC-era → GTR2 adapter needs explicit rescaling or target templates for both families. Full-tier regression test added.

## GTTF heading vs AIW pointer-chain tangents (2026-11-27)

Using pointer-chain `ptrs[1]` tangents in the mapped (y,z) plane across 27 GTR2 ghosts, the best-of-four-convention circular coherence with `+12` heading has median **0.404** versus **~0.05** under permutation of tangents — an 8× above-chance alignment. Unlike the DSI-line test (median best coherence 0.318), this shows the ghost heading does follow the AIW racing-line direction, but the convention (`±`, axis order) varies per track, so no universal sign/axis rule is promoted. Full-tier permutation-controlled regression test added.

## GTTF heading vs DSI tangents in y/z plane (2026-11-27) — negative

After establishing that ghost `+0` = AIW y and `+1` = AIW z, recomputed DSI instructor-line tangents in the same (y,z) plane and compared them with ghost `+12` heading across 27 matched tracks. Even allowing four orientation conventions (`±atan2(dy,dz)`, `±atan2(dz,dy)`), the **best per-file circular coherence is only 0.318 median**, with no single convention dominant. So `+12` does not encode the DSI tangent direction despite sharing two coordinate axes; its earlier AIW-direction negative is confirmed in the correct frame. Full-tier regression test added.

## GTTF steering vs DSI curvature (2026-11-27)

Matched 27 ghosts to their track's DSI lap-instructor line by y/z and compared `+16` with signed curvature of the DSI polyline in the x/z plane. Median correlation is **−0.171** (median |r| **0.241**; 17/27 files above |0.2|; 20/27 negative). This is a modest but consistent curvature relationship, weaker than the +8/+16 link (0.585) because the DSI line is a different racing line and matching uses a ±2–3 m z/y window. It supports +16 being steering/curvature-related but does not establish exact units or sign; full-tier regression test added.

## GTTF steering-sign convention (2026-11-27)

The ± sign of the `+8`/`+16` relation is not random across the 29 F550 ghosts: files with positive correlation have a median net unwrapped `+12` heading trend of **7.9 rad**, negative-correlation files **4.74 rad**, and the per-file correlation coefficient versus heading trend is **0.583**. AIW waypoint file order/signed area does **not** explain the split (sign agreement 12/27, correlation 0.109). So the steering sign is tied to the recorded heading evolution (likely different ghost/recording configurations), but the exact convention remains unknown. Full-tier regression test added.

## GTTF +16 steering-rate hypothesis (2026-11-27) — negative

Tested whether `+16` is a steering-rate signal: its per-frame derivative (divided by frame dt) has **median |correlation| 0.011** with the steering-related `+8` field and **0.054** with the `+12` heading rate across all 31 ghosts (max |r| 0.061 / 0.102). There is no rate-like relationship to either quantity, so `+16` is not a steering rate under these conventions. Its earlier moderate curvature correlation and +8 coupling remain structural observations; exact semantics still unresolved. Full-tier regression test added.

## GTTF +16 vs setup pedal ranges (2026-11-27) — negative

The requested comparison against throttle/brake pedal ranges cannot be made: the F550 and M3 `.hdc` setups contain only `DownshiftBlipThrottle=0.50` plus mechanical brake settings (`BrakePressureRange`, `RearBrakeRange`, etc.); the `.car` files store only 3-D pedal *positions*, not 0..1 pedal envelopes. There is no setup-derived range to validate against. Independently, `+16` takes negative values in **31/31** ghosts (minimum down to −0.211 rad), so it cannot be a plain unsigned throttle/brake pedal signal despite its sparse 1.0 spikes. Full-tier regression test added; pedal semantics remain unsupported.

## GTTF +16 extrema vs .hdc steer lock (2026-11-27) — negative

Both `BMS550.hdc` (F550) and `BMW_M3.hdc` declare `SteerLockRange=(5.0,0.5,37)`, `SteerLockSetting=20` → 15° (0.262 rad). If +16 were a front-wheel steer angle, per-ghost extrema should respect that bound. They do not: **31/31** files exceed 0.262 rad and **27/31** hit exactly **1.0** at least once (median per-file maximum = 1.0). Globally the field is near zero (median 0.005 rad, 99th percentile 0.131) with sparse 1.0 spikes, so it is not a raw steer angle bounded by setup lock — likely a rate/clamped control signal. Full-tier regression test added; exact semantics unresolved.

## GTTF +8 vs steering +16 (2026-11-27)

**Superseded (see clamp-artifact correction above).** After detrending both fields on ghost z (+1) and a z-increment speed proxy, frame `+8` and the decoded steering-like field `+16` had a **median |correlation| of 0.585** across 29 GTR2 ghosts (24/29 above 0.3). The sign is not universal (17 positive, 12 negative), likely reflecting track/record orientation or a sign convention. So `+8` is a steering/lateral-control-related quantity rather than random padding or a world coordinate. Exact units and sign convention remain unresolved; full-tier regression test added.

## GTTF missing x: DSI-centerline reconstruction negative (2026-11-27)

Attempted to reconstruct the missing x from ghost `+8` using the Anderstorp DSI lap instructor line as a centerline: matched 773/860 ghost frames to DSI points by y/z, then correlated `+8` with the DSI x at those points (and with z). `+8` spans only −0.03..1.53 m while DSI x spans −346..339 m; correlation with x is **−0.049**, with z **0.03**, and the partial correlation after detrending on z is **−0.053**. No scale/offset model can recover x from this field. The lateral-offset hypothesis for `+8` is therefore unconfirmed (and if lateral, its scale would have to be unrelated to world x). Full-tier regression test added; x reconstruction remains blocked without a format spec or runtime capture.

## GTTF axes +0/+1 map to AIW y/z (2026-11-27)

A matched-track comparison of the 27 GTR2 ghosts with their AIW waypoint files found that ghost `+0` reproduces AIW **elevation (y)** endpoint ranges with median total error **0.4 m** (27/27 tracks within 10 m), and ghost `+1` reproduces AIW **z** endpoint ranges with median total error **6.6 m** (21/27 within 10 m). This is a strong partial coordinate map: the frame stores world y and z directly at scale 1, while AIW x (spans hundreds of metres) is **absent** from the 63-byte record — no byte-aligned or unaligned float field with a matching 1,000 m span exists. The small `+8` value (~1.6 m span) does not correlate with AIW x (r≈−0.05), so it is not a compressed x. Full-tier regression test added; the missing x reconstruction remains blocked (likely a lane/lateral-offset convention resolved by the game from the AIW path).

## GTTF frame +8: lateral-offset candidate, not elevation/progress (2026-11-26)

Tested the third position float at +8 against DSI/AIW track geometry. Across 29 GTR2 ghosts its per-file span is tightly bounded (median 1.66 m, range 0.13–2.71 m), whereas matching AIW waypoint elevation spans vary 0.3–73 m and do not correlate (0/29 within 0.5 m). It is not lap progress (monotonic fraction median 0.494) and not a scaled AIW x coordinate (correlation ≈−0.05 when matching frames to waypoints by z). It is moderately smooth (median lag-1 autocorrelation 0.506), consistent with a bounded lateral-offset-like quantity, but DSI instructor lines cannot confirm this while the ghost coordinate transform is unresolved. Full-tier regression test added; lateral offset remains a hypothesis, not a decoded semantic.

## GTTF position transform search (2026-11-26) — negative

Fitted candidate transforms of the ghost `+0/+4/+8` triples to the corresponding AIW track waypoints (6 axis permutations × scales 0.01–100 × centroid-based and grid-searched translations) on the Anderstorp F550 ghost. Best median nearest-waypoint distance was **10.3 m** (scale 0.5, perm `(1,0,2)`, translation offset −20/−20 m) — not a convincing fit to a ~10–15 m wide track, and no transform recovered the AIW coordinate ranges. Across all 31 ghost files, each position triple has one axis spanning <2.71 m and one spanning >307 m (medians 1.64 m / 623 m); the AIW waypoint spans in the same track are x≈685 m, y≈2 m, z≈395 m. The small axis matches AIW elevation and the large one matches longitudinal extent, but the third AIW axis is absent from the ghost triple: these are **track-local** coordinates (elevation / lateral / longitudinal-like), not world XYZ. No valid world transform was found; AIW-based heading/kinematic alignment remains blocked. Full-tier span regression test added.

## GTTF wheel-speed hypothesis blocked by position scale (2026-11-26)

Attempted to test slot +32 against wheel angular velocity from `.grb`/`.hdc` gear ratios and `.tyr` radius. The prerequisite failed: speed derived from consecutive frame positions at +0/+4/+8 is implausibly low in **all 31 GTT files** (median of per-file medians 0.53 m/s; every file <2 m/s, while a 45 s lap would require tens of m/s). In the Anderstorp file the three position axes span only 1.95 / 392.8 / 1.56 m over 45.3 s, so the +0/+4/+8 floats are not a conventional world-space metre triple at 20 Hz. Consequently `+32 / speed` has no meaningful gear-ratio bands (only 1 frame above 5 m/s in that file). This also explains the earlier failures to align ghost headings with AIW world waypoints. Full-tier regression test added; wheel-speed and any other position-derived kinematic hypothesis are **blocked** pending a correct position transform/scale, not negated as field semantics.

## GTTF +12 heading vs AIW waypoint directions (2026-11-26) — negative

Cross-checked the recorded `+12` heading against the nearest AIW waypoint's next-pointer direction in all 29 GTR2 ghost files (3,606 samples, every 10th frame). Under the tested horizontal conventions (`atan2(dx,dz)` and its sign/swapped variants) there is **no coherent relation**: circular concentration R=0.026 (uniform ≈0), median absolute angular error 1.606 rad (chance ≈1.571), and no consistent constant offset. A direct comparison with frame-to-frame position deltas is likewise poor (best median ~1.24 rad). This **corrects** the earlier single-sample "cross-validated" claim: it was a coincidence, not a general rule. Full-tier regression test added; `+12` remains a heading-like angle but its frame/axis convention is not resolved.

## GTTF slot +28 vs AIW progress (2026-11-27) — negative

Using the mapped y/z frame, matched each ghost frame to its nearest AIW waypoint and compared the u32 at +28 (`00 20 00 XX`) with both waypoint file order and pointer-chain rank/lap distance. Median |correlation| is 0.035 (file order), 0.08 (chain rank) and 0.08 (cumulative lap distance) across 15 F550 ghosts; no file exceeds 0.2. The field's constant `0x2000` low bits and slowly varying high byte are a packing artifact, not lap progress or waypoint identity. Full-tier regression test added.

## GTTF +32 vs peak-power RPM (2026-11-27) — negative

Tested whether the car-specific +32 ceilings mark `.eng` peak-power RPM instead of rev limits. From the torque tables, peak power is at **6500 rpm** (F550 `550_Std_V12.eng`) and **8250 rpm** (BMW `BMW_M3.eng`); peak torque at 5000 / 3750 rpm. Raw ceilings divided by peak-power RPM are **903.7** vs **768.1** — a 15% car-dependent discrepancy (and peak-torque ratios differ far more). So no common engine-table RPM band explains the ceiling under any single scale; the +32 signal remains engine-speed-like with unknown car-dependent normalization. Full-tier regression test added.

## GTTF +32 scale vs `.eng` rev limits (2026-11-26) — negative

Checked the /1024 RPM interpretation against the cars' physics configs. `550_Std_V12.eng` (Ferrari F550) has `RevLimitRange=(7200,100,7)`, `RevLimitSetting=2` → **7400 rpm**; `BMW_M3.eng` (BMW M3 Challenge) has `RevLimitRange=(8500,0,0)` → **8500 rpm**. The GTTF ceilings are 5,873,841 raw for F550 and 6,336,964–6,345,107 for BMW M3, giving raw/rev-limit factors **793.8 vs 745.5** — an 6.5% systematic difference between cars. Therefore the naive `/1024 = rpm` scale is **negated** as a direct RPM reading. The car-specific ceiling and shift-like drops still support an engine-speed-like signal, but its scale/normalization is car-dependent and unknown. Full-tier regression test added.

## GTTF slot +36: exact quantized-float shape (2026-11-26)

Across all 47,239 frames in 31 GTT files, slot +36's u32 has its low 16 bits zero in 46,529 frames (**98.5%**) and the mantissa's high 7 bits take only two values, **8 or 12** (`0x08`/`0x0C`). The float can therefore only be zero or ±(17/8 or 35/16)·4ᵏ — an exact quantization lattice, not a free measurement. By car: the Ferrari F550 files use mantissas 8/12 with exponents centred at 134; the two BMW M3 files use the same mantissas with exponents centred at 162 (a car-specific scale shift). `simbin_events_tool.is_quantized_s36()` detects this and a regression test checks ≥98% of frames. Earlier negatives still hold: no meaningful correlation with speed, acceleration, heading rate, steering or the +32 engine-speed word (|r|≤0.27 across files). No semantic promoted — this is a structural characterization of a car-scaled quantized field.

## GTTF slot +32: engine-speed hypothesis (2026-11-26)

**New positive structural finding** (refines earlier "unbounded 24-bit integer" negatives): across all 31 local `.GTT` files with frame grids, the 24-bit value at `+32` (byte `+35` is always 0) has a **car-specific hard ceiling**: 21/29 Ferrari F550 files peak at exactly **5,873,841** (≈5736 when divided by 1024), while both BMW M3 files peak at 6.19–6.20M (≈6190). The remaining F550 files peak 5.66–5.81M. The signal is very smooth (median lag-1 autocorrelation 0.994) and shows abrupt downward jumps of 200k–900k (~200–900 rpm at /1024) consistent with gear shifts, including at 30–70 m/s. Correlation with speed is mildly negative (median −0.14, consistent with upshifts), and with speed-derived acceleration ≈0 (gear changes dominate).

`simbin_events_tool.frame_rpm()` now exposes the raw word and a `/1024` reading; `read_frames()` includes `engine_speed`/`rpm`. **Status:** car-specific ceiling + shift-like drops are verified; the engine-speed interpretation and exact scale are strongly supported but not confirmed against runtime telemetry, so this is labelled a hypothesis rather than a decoded semantic. Regression test: 31-file ceiling bounds + ≥5 F550 files at the exact ceiling + ≥3 files with ≥10 shift-like drops. This does not rehabilitate the earlier throttle/brake/timestamp/lap-distance negatives for this slot.

## GTTF byte +31 event/smoothed-speed hypotheses (2026-11-24)

Tested whether the varying byte +31 marks discrete track events: it changes between consecutive frames in **47.3%** of 44,573 transitions (far too frequent for pit/lap markers), and speed near changes (median 22.3) is just the naturally higher speed where quantization steps toggle. A bounded search over lags 0-20 and EMA smoothing alphas 0.1-0.9 found best speed correlation only r=0.34 (lag 20, alpha 0.1), with most files below 0.25. Byte +31 is therefore neither a rare event flag nor a smoothed speed signal; its quantized magnitude semantics remain unresolved.

## IRSR replay frame grids (2026-11-25)

Cross-corpus check: `simbin_events_tool.find_frame_grid()` detects the 63-byte frame grid in 4/4 GTL IRSR replays but in **0/6 Superleague, 0/5 RF1Vanilla and 0/9 GTR2 IRSR replays** (metadata parses in all). A generic scan of a Superleague replay for monotonic f32 timestamps at strides 16-128 and phases 0-127 found no sequence of >=20 frames. Only GTL IRSR (and GTTF `.gtt`) replays expose the documented frame grid; other IRSR variants remain metadata-only.

## TR2009 `.hdv` opaque variant (2026-11-25)

`../SimuladorTopRace2009/GameData/Vehicles/TRV6_2009/trv6_09.hdv` (12,746 B) has a valid `//[[gMb1.002f (c)2007]]` 44-byte header followed by a 12,701-byte high-entropy payload (`7b 4a 9b 6c...`). Exhausted: ISI-crypt forced enctypes 0/1 at skips 0/4/12/16, all JCA keys, zlib/gzip at offsets 0/44/45 — no printable text or valid layout. The corpus test now skips this one file; no speculative decoder added.

Follow-up: `gMb1.002f` is not TR2009-specific — it is a **shared SimBin encrypted-config family**: 19 files across `../TC2000` (`.hdv/.pm/.tbc/.ini`), `../SimuladorTopRace2009` (`.hdv/.pm/.tbc/.ini`) and `../SuperleagueFormula2009` (`.hdv/.tbc/.ini/.pm`), 18 with high-entropy payloads and one IRSR replay that merely mentions the tag. The header's second bracket field is 12 bytes (`e7 22 20 20 4a 1c 2e ...`; Superleague `e7 22 20 20 2b de 21 ...`) and is **not** an ISI signature (all 16-byte-window signatures unknown; 12 bytes is too short). Fresh negatives: raw ISI crypt with header-derived seeds × enctypes 0/1 × skips 0/4/8/16/32 peaks at 0.390 printability vs 0.396 baseline; raw Blowfish across all JCA versions/keys peaks at 0.390; zlib/raw-deflate/bz2/lzma all fail. XORing the encrypted `doublewishbone.pm` against the plaintext 5,969-byte counterpart at every offset 0..1,999 gives a maximum zero-run of 2 (0.6% zero bytes) — no shared keystream. Header-field-derived repeating XOR keys give 0.40–0.42 printability. `media_tool.gmb_encrypted_config()` now identifies the family structurally (full-tier test: 19 found, 18 encrypted), but no decoder is promoted.

Fresh pre-decompression sweep (all 18 encrypted payloads): every single-byte XOR mask 0..255 and every repeating keystream derived from the 12-byte header field was tested against zlib, raw-deflate, gzip, bz2 and lzma decompression. Exactly 18 magic-prefilter candidates appeared — all LZMA-alone headers beginning `5d` produced by XOR mask 0x70 against a literal `'-'` first byte shared by many payloads — and **all 18 failed** `LZMAError`. No valid decompressed stream was produced by any mask/keystream/algorithm combination; no decoder promoted.

## GTTF +24/+28/+44 packed-integer hypotheses (2026-11-25)

Using ccgepmonitor's `mLapDist`/`mPathLateral` semantics as a guide: slot +24 is the constant marker `01 00 00 34` in 29/29 files (no data); slot +28 begins `00 20 00 XX` (fixed low 16 bits `0x2000`) in all files, and its varying byte +31 shows no correlation with cumulative distance (median r=-0.014) or frame delta-time (-0.010). Slot +44 holds near-1e38 floats (±1.6e38 range) — not bounded lateral metres. A packed-half interpretation was also excluded: bytes +44 and +46 are equal in 83% of frames (clustered 227-233), and float16 decoding of either 16-bit half yields unbounded values (−3.95..3.95 and −64448..64704) with no correlation to longitudinal acceleration (median r=0.001) or heading rate (0.005) and no file confined to 0..1/[-1,1]. No packed-integer or bounded-range interpretation matched any runtime field; recorded as negative.

## GTTF slots 28/36/40 kinematic hypotheses (2026-11-25)

Using ccgepmonitor's documented GTR2 runtime ranges as a guide, slots +28/+36/+40 were correlated against speed and longitudinal acceleration across all 29 files: median r ≈ 0 for every combination, max |r| ≤ 0.08, no file above 0.5. These slots are not speed or acceleration signals under any simple linear or sign-flipped interpretation. A final log-quantized test (throttle/brake hypothesis: `log2(|v|)` and signed-log vs signed/positive/negative longitudinal acceleration) also failed for +28/+36/+40 — median r≈0, max |r|≤0.12, no file above 0.5. The 24-bit integer at +32 was also tested against cumulative lap distance (ccgepmonitor `mLapDist` semantics): median r=-0.05, max 0.254, no file above 0.9 — not a lap-distance field. Slot **+60 is not throttle/brake** (2026-11-25 follow-up): across all 29 files the f32/u32 readings at +60 are sentinel-like (range −2.6e38..4.3e9 as u32) with lag-1 autocorrelation ≈0 and acceleration/speed correlations ≈0 (max |r| 0.072). Per-byte, +62 is extremely smooth (lag-1 0.996, range 62–196) and +61 moderately smooth (0.935), but their acceleration correlations are −0.001/0.001 (max |r| 0.027/0.036) and speed correlations −0.112/−0.018; byte +60 is random (lag-1 −0.024, full 0–255 range). As with +44/+48/+52/+56, smoothness comes from high bytes of sentinel-like values, not a physical signal. No pedal semantic promoted.

Slots **+48, +52, +56 are not throttle/brake** (2026-11-25 follow-up): across all 29 files their f32 readings have implausible sentinel-like ranges (e.g. −3.4e38..1e−33) and median lag-1 autocorrelation 0.573 / 0.107 / −0.001 (steering control 0.523). Correlations with speed-derived acceleration are 0.005 / −0.007 / −0.008 (max |r| 0.025/0.065/0.089) and with speed 0.162 / −0.083 / 0.004. A per-byte sweep of +48..+59 finds two byte positions with high lag-1 autocorrelation (0.984 at +51, 0.926 at +49, 0.899 at +58) but **every** byte's acceleration correlation is ≈0 (max |r| 0.068); apparent smoothness comes from high/sign bytes of huge sentinel-like floats, not a slowly varying physical signal. No pedal semantic promoted.

Slot **+44 is not throttle/brake** (2026-11-25 follow-up): across all 29 files the f32 at +44 has lag-1 autocorrelation 0.005 (steering control 0.523) and implausible range ±1.5e38; correlation with acceleration 0.001 (max |r| 0.065) and speed 0.005. The u32 reading has lag-1 0.679, driven by bytes +44/+46 (lag-1 0.996/0.995, narrow ranges 198–239 and 206–239) while bytes +45/+47 are less smooth (0.440/0.679); every byte's correlation with acceleration and speed is ≈0 (max |r| 0.044). This extends the earlier packed-half/heading-rate negatives for this slot.

Slot **+32 is not throttle/brake** (2026-11-25 follow-up): across all 29 files the u32 at +32 is very smooth (median lag-1 autocorrelation 0.992, steering control 0.523) but unbounded (2.3M–5.9M) and uncorrelated with acceleration (median r=0.002, max |r| 0.026) or speed (−0.029). Byte decomposition: +32 lag-1 0.871, +33 −0.013, +34 0.991, +35 constant 0; all byte correlations with acceleration/speed are ≈0. It is also **not a timestamp**: correlation with the decoded +20 time field is −0.024 (0/29 files above 0.9), monotonic fraction only 0.682, median delta −/+14,336 unrelated to frame dt (r=−0.010). This complements the earlier lap-distance negative for this slot.

Slot **+36 is not throttle/brake** (2026-11-25 follow-up): across all 29 files the f32 at +36 has median lag-1 autocorrelation 0.18 and range −143,360..557,056 (not a bounded 0..1 or small discrete pedal signal); its correlation with speed-derived acceleration is 0.001 (max |r| 0.061) and with speed 0.000. Per-byte decomposition: byte +36 lag-1 0.000, +37 0.354, +38 0.937, +39 0.413 (steering control 0.523), with median correlations to acceleration −0.016/−0.009/−0.008/−0.002 and to speed 0.000/−0.008/−0.034/−0.005. Sign-magnitude decoding of each byte leaves those correlations unchanged in magnitude (max |r| to acceleration 0.201 for byte +36, all others ≤0.055). This complements the earlier steering negative for this slot.

Slot **+7 is not throttle/brake** (2026-11-25 follow-up): across all 29 files its byte has median lag-1 autocorrelation **0.995** (min 0.992), smoother than the decoded steering control (0.523) — so smoothness alone is not evidence of throttle. It takes only 20 values in two clusters (63–68 and 191–196), and correlation with speed-derived acceleration is 0.005 (max |r| 0.036), with |acceleration| 0.031. Sign-magnitude decoding (`-(v & 0x7f)` for the high-bit cluster, signed range ±67) still gives no correlation with acceleration (median −0.005), positive-only acceleration (−0.018), negative-only acceleration (0.021), speed (0.036) or steering (−0.031); only 1/29 files reaches |r|>0.6 on speed. No pedal semantic promoted.

Slot **+9 is not throttle**: across all 29 `.GTT` files its byte takes all 256 values with near-uniform counts (~200 per value), has median lag-1 autocorrelation **0.002** (max 0.029) — i.e. frame-to-frame white noise, whereas the decoded +16 steering field has median lag-1 autocorrelation **0.523** (min 0.363) as a physical-signal control. Median correlation with speed-derived acceleration is 0.001 (max |r| 0.062); testing u8@8/@9, u16@8, f32@8 and u32@8 gives median |r| ≤0.006 (max 0.199). A throttle signal in ccgepmonitor's 0..1 units must vary smoothly and track acceleration, so this slot is excluded. A fresh gear-state hypothesis was also excluded: log2-magnitude levels of slot +40 take 5 dominant discrete values (0/3/5/7/9) in 29/29 files, but transitions are symmetric up/down in every speed band (e.g. 844 up vs 808 down at low speed), with no monotonic upshift-with-speed pattern — a quantization artifact, not `mGear`. Combined with earlier quadratic/quantization/exclusion results, they remain uninterpreted.

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

Follow-up (all 1,982 pairs): a direct offset test of every u32 field position against the companion `.dat` found no offset-like field — the apparent MP3-sync hits at +12 were simply the value 0 in 1,153 files (offset 0 always has sync). Of the 829 files with a nonzero +12 value, 789 point outside the `.dat`, only 15 land on a sync byte (1.8%, chance-level), and the values are powers-of-two or category flags (`0x10000`, `0x80000`, `0x5000000`). `u32@0` is either `0xFFFF00xx` (86 files) or `(n << 16) | 0x62`-style category/index (1,896 files), not a universal magic. What *is* corpus-verified is bounding: header length >=16 and 4-byte aligned, +8 block count >0 and `*256 <= dat_size` in 1,982/1,982, exposed as `media_tool.validate_hdr_dat_pair()` with a full-tier regression test.

## `.svm` conversion gap (2026-11-25)

Systematic same-name GTL↔GTR2 comparison across 16 config extensions found `.svm` car setups are the clearest conversion gap: the rF1 versions of `Donington.svm`/`Spa.svm` carry only **6 keys** (174 B, `gMa1.000f` header) while the GTR2 versions carry **72 keys** (~2,380 B). The 6 rF1 keys are a strict subset (0 rF1-only) with identical values in 5/6 and 6/6 cases (the single difference is car-specific `finaldrivesetting` 0→1). The 66 additional GTR2 keys are car-specific setup values (brakes, camber, diff, engine maps, suspension) that cannot be derived from the rF1 setup alone — they require a same-car GTR2 template. `gtl_to_gtr2.convert_config_bytes()` does **not** handle `.svm` (only `.trk/.aud/.hdc/.tyr/.dmg/.gdb/.car/.aiw/.rcd/.ani`), so a converted tree copies the minimal rF1 setup verbatim into GTR2 — a real gap. No template-free conversion rule can be promoted; documented rather than guessed at. A template-based adapter is also not viable from local corpora: the same-name GTL/GTR2 `.svm` files belong to **different cars** (e.g. GTL `Donington.svm` is an Austin Healey 3000 / Corvette / Ferrari 275 GTB while GTR2 `Donington.svm` is a Chrysler Viper / Ferrari 550 / 575), so no same-car GTR2 template pair exists.

## GSC-encrypted GMT deep probe (2026-11-25)

Deep field-level probe of the minimally investigated `../Automobilista`, `../StockCarExtreme`, `../GameStockCar` and `../CopaPetrobrasdeMarcas` corpora: all sampled archived `.gmt` members carry the known GSC ISI signature `0x4b1dca9f960524e8` (enctype 1) and `isi_crypt.decrypt_bytes()` decrypts them successfully. In a 2,000-file sample, the 16-byte word at offset **0x1D4** is a near-magic `c8 cf d2 d8 ce d8 e6 c3 d6 de d8 be bb a8 bf 90` — the standard GMT magic except byte 13 is `a8` rather than `a6` — in 101 files. `gmt_semantic.read_gmt()` finds submeshes in 92/101 of those, versus only 9/1,899 files without the near-magic (strong statistical discriminator, not a strict rule). Files with submeshes yielded real geometry (e.g. 258 vertices / 220 faces in one sample). The remaining ~95% of decrypted GSC GMTs do not expose submeshes to the current parser; whether this is a further encryption layer, a compression variant or a distinct old layout remains unresolved. Cross-corpus contrast: a 500-file sample of `../RF1Vanilla` old-layout GMTs decodes **500/500** through `gmt_semantic.read_gmt()` (1,466,934 vertices / 715,234 faces), without any ISI decryption and without the standard magic at 0x1D4 — the parser scans for per-submesh 0x2000-magic headers rather than a file-level marker. Thus the failure on GSC-encrypted GMTs is specific to those files, not to the old-layout parser. Further discriminating probes confirmed this is a **distinct layout**, not a decryption-offset or enctype problem: both decodable and undecodable files decrypt correctly with enctype 1 (calling `isi_crypt()` directly with enctype 0/1 shows only enctype 1 yields structured data); the decodable files carry per-submesh headers with magic `0x20004035`/`0x20004015` at offsets 0x2e4/0x368, whereas a full byte-wise scan of an undecodable 114,816-byte file found **zero** occurrences of any `0x20004011/15/35` (or strip) magic. The undecodable files also fail all GTR1-style readers (`read_gtr1_object_mesh`, `read_gtr1_table`, `read_gtr1_descriptors`) and contain no zlib header in the first 4 KB. Compression-layer probe: a whole-file scan of a decrypted undecodable GSC GMT found exactly one `78 9c` and one `1f 8b` byte pair, both at random offsets producing invalid streams ("invalid distance too far" / "unknown compression method"); raw-deflate at every offset produced 83 "large" hits but all at 32-byte vertex stride with identical lengths — clearly vertex-data artifacts, not compression. The `../MAS2Extract` rF2 `GMOTOR_MAS_2.90` reference uses a salt+XOR archive header (a different container level) and does not apply to member-level GSC GMT. Unit-triple probe: a 60-file-per-corpus scan found unit-norm float triples in 25-31 "other" (non-magic) files per corpus (e.g. `AMBULANCE001.GMT` has 1,345), forming consecutive runs at a **16-byte stride** with a trailing zero 4th float — i.e. real vertex normals exist. However `gmt_semantic.read_gmt()` finds 0 submeshes in these files because the `0x200040xx` per-submesh magic headers are entirely absent. Thus the ~95% are not empty: they contain geometry indexed by a different (undecoded) container layout, not a submesh-header format. A byte-swapped/alignment probe on an opaque file (`AMBULANCE_LOD001.GMT`) found **zero** occurrences of any `0x20004011/15/35` submesh magic at any byte offset, in either little- or big-endian form. Searching the 4 KB before a 49-record 16-byte-stride unit-normal run for a u32 count equal to the run length or an offset into the run found no candidate table. No alternative decode path identified. Follow-up: the 16-byte-stride unit-normal runs are **not universal** across the undecodable files — a 50-file-per-corpus sample found runs in only 9/50 (Automobilista), 8/50 (StockCarExtreme), 10/50 (GameStockCar) and 17/50 (Copa). Examination of a longest run (49 records at 0x19cdc in `AMBULANCE001.GMT`) showed 16-byte records of 3 floats + a constant `0x8c8c8c8e` word with no accompanying count/offset table, so no vertex/face table invariant could be promoted across all four corpora. No speculative decoder added. A second ISI-crypt layer was excluded: after one decrypt pass the 16-byte signature is unrecognised by `isi_crypt.GAMES`, and forced enctype-1 re-decryption at skips 0/4/8/16 produces only garbage. The decrypted payload begins `ee 68 ee ee 20 00 00 04` (0x04000020 flags-like field) but does not carry a recognised second-layer signature. A modern-container scan of 1,200 opaque decrypted members found **zero** Zstd (`28 b5 2f fd` / skippable), LZ4 frame/legacy, or LZOP magics at any byte offset (lz4/zstandard/brotli Python modules are not installed, but magic detection does not require them). Only 7 gzip and 4 BZh occurrences appeared, all deep inside payloads (offsets 29,878–1,693,900) and every one failed decompression (`zlib.error` / `OSError`) — random byte coincidences, not embedded streams. A GTR1-style descriptor-grid probe on **1,200** opaque decrypted members across all four corpora found zero `0x11C` universal tables and zero `0x194` 64-byte descriptor grids; a relaxed scan for any plausible `(v_count, v_offset, i_count, i_offset)` pair in the first 2 KB produced only 3 coincidences (shifted overlapping windows at offset 372, not aligned to 0x194). GTR1's container layout is therefore excluded for the opaque GSC subset. A structural marker does exist: across 800 sampled opaque members the u32 at +4 is `0x04000020` (600), `0x20` (162) or `0` (20) — 782/800 (97.75%), exposed as `gmt_semantic.opaque_gsc_flags()` with a full-tier regression test. Member lengths show no fixed-record framing (size mod 16/32/48/64 nearly uniform across 27,937 cached opaque members), so no record-size-based decoder can be inferred from length alone.

## `.gdb`/`.car` universal-key survey (2026-11-24)

Generic section/key parsing of all 1,287 `.gdb` and 3,385 `.car` files found **667 / 173 distinct keys respectively but no cross-corpus universal key**. Only family-specific universals exist: `.car` GTR2-family files (165) all carry `genstring`, `pitgroup`, `number`, `driver1`, `team` (the GTR2-only key set already used by `gtl_to_gtr2`); rF1 `.gdb` (81) all carry `racelaps`. Seven zero-length `.gdb` fixtures in `../rfactortools/tests/data` are legitimately empty. `parse_gdb()`/`parse_car()`/`validate_config()` therefore perform structural validation only — no universal key rule can be promoted beyond the existing family-specific validators.

## GSC region masks: not member-metadata derived (2026-11-27)

Tested 120 masked GSC GMT members against archive metadata: uncompressed size, compressed size, flags, CRC32 low/high byte of the compressed member, Adler32 low byte and byte-sum of the first 4 KiB. Magic-key matches were 0 / 0 / 1 / 1 / 1 / 1 / 2 respectively, all at permutation baseline (e.g. flags 6 vs 6, zsize 5 vs 1.9 in a 425-member extension sample). No metadata-derived mask rule found. Full-tier regression test added.

## GSC region masks: not name-derived (2026-11-27)

Tested 120 masked GSC GMT members: the magic XOR key at 0x1D4 and the per-submesh masks do not match CRC32-low/high, Adler32, byte sum, basename length, first or last character of the archive member basename. Magic matches were 0/1/0/0/0/1/1 respectively (permutation baselines ≈0.1–1), with 10 total coincidences across 120×7 correlated candidates — chance level. Full-tier regression test added; mask derivation remains blocked.

## GSC region masks: no alignment counterpart (2026-11-27)

Tried to derive the bulk mask by XOR-aligning region-masked GSC GMTs with plain GTR2/GTL counterparts of the same object (f0 family invariants provide mesh identity). Across **25,210** plain and **29,033** GSC GMT members (22,103 / 25,002 distinct name+size pairs) there are **zero** same-name **and** same-size pairs — meshes of the same family were re-authored with different geometry lengths across games. Whole-file or per-region byte alignment is therefore impossible, and this approach cannot recover the bulk mask schedule. Full-tier regression test added; the region-mask blocker remains.

## GSC opaque GMT: per-vertex-run key negative (2026-11-26)

A fresh hypothesis tested whether the bulk mask is a per-32-byte-vertex byte, derivable from the repeated-byte runs found at 32-byte stride in `PURCHASED.GMT` (618 aligned runs). Using each run byte as the vertex mask yields 469/618 finite, bounded float triples — but their median maximum magnitude is **<0.01** (values like 0.001–0.003), i.e. near-zero padding, not mesh positions. The runs therefore identify padded records, not a vertex keystream; no bulk decode is obtained. Full-tier regression test added; the region-mask schedule remains blocked.

## GSC opaque GMT: region-mask schedule negative (2026-11-26)

Targeted search for a derivable schedule on the remaining files (no decoder promoted):

- Across 120 sampled masked GMTs, `submesh_mask - magic_mask` is zero in only 61 cases; the other 59 deltas span 20+ distinct byte values (e.g. `0xA8`, `0xF0`, `0xFF`, `0x03`, `0xFB`) with no dominant rule. Only 88/120 magic and name masks agree.
- No correlation with file length: `mask == (size & 0xFF)` in 2/120 files and `mask == (size & 0xFF) ^ 0xFF` in 1/120.
- Section checksums do not produce the masks (name `purchased` sum `0xBF` / XOR `0x6F` vs key `0x0B`; table sum `0x50` / XOR `0xA0` vs `0x0C`; submesh header sum `0x78` / XOR `0xA4` vs `0xFB`).
- Applying the three known masks of `PURCHASED.GMT` (`0x0C` header, `0x0B` names/magic, `0xFB` submesh header) yields a valid table and a `0x20004011` submesh header, but the decoded mesh has **0 faces and implausible float positions** — the bulk vertex/index region uses further masks.
- Brute-forcing one XOR key for the bulk region and ranking by plausible float count gave no distinct candidate (best 596/1024 ~ chance level).

`decode_gsc_xor_gmt()` therefore deliberately returns `None` for these files; a quick-tier regression test locks in that negative. Unblock conditions remain: a spec/tool exposing the mask schedule, or a plaintext pair covering the bulk region.

## GSC opaque GMT: single-byte XOR subset decoded (2026-11-26)

**Partial decoder promoted:** `gmt_semantic.decode_gsc_xor_gmt()` derives the mask from the file-level magic at `0x1D4` and XORs the whole ISI-decrypted file, then accepts the result only if `read_gmt()` finds submeshes. Verified on 60 masked members per corpus: Copa **32/60**, GameStockCar **32/60**, StockCarExtreme **35/60**, Automobilista **39/60** (plus 104/160 in an earlier Copa sample that included unmasked files). **Correction (2026-11-26):** the early claim of "real geometry" was wrong. A follow-up quality sweep of 150 structurally decoded members found **0/150** with both plausible positions and faces; the four regression examples include submesh headers but their vertex positions are implausible (e.g. `TRACKWORKERRIGHT.GMT`, `AMBULANCE_LOD001.GMT`). The whole-file XOR restores the *header/submesh structure* only; the bulk vertex region usually keeps its own region mask, which is why f0 markers from such files have nonsensical byte-repeated values. `read_gsc_geometry()` must be used as a quality gate before any geometry is trusted. Quick-tier regression test covers structure **and** the geometry negative. The remaining ~45% use region-specific masks and stay blocked; no speculative fallback is added.

## GSC opaque GMT: XOR-masked headers found (2026-11-26)

**Refinement of the 2026-11-25 negatives** (not a decoder): 188/200 ISI-decrypted opaque GSC GMTs sampled from four corpora have the 16 bytes at `0x1D4` equal to the old-layout magic `c8cfd2d8…bba8bf90` XORed with a **single constant byte**; 12/200 have the plain magic. `gmt_semantic.gsc_xor_magic_key()` detects this deterministically. In `showroom.mas/PURCHASED.GMT` (Copa) the masks are **region-specific**: `0x0C` over `0x000–0x193`, `0x0B` over `0x194+` (name and magic), and `0xFB` at the submesh header at offset 740. The relaxed magic scan `gsc_masked_submeshes()` (which requires the full `0x200040xx` byte relation under an arbitrary one-byte mask) finds exactly one header there: `(740, 0xFB, 0x20004011)` — previously reported as "zero occurrences of any submesh magic" because only the unmasked magic was tested. After applying the two header masks, the table at `0x174` reads `(1, 736, 576, 868, 576, 19300, 0, 28516)` and the name field reads `purchased`.

**Still blocked:** no single whole-file XOR key restores `read_gmt()` submeshes (all 256 keys tested), and applying the three known region masks still yields zero submeshes — the mask schedule beyond those regions is unknown. No speculative decoder is added; the detectors and a quick-tier regression test document the verified structure. Unblock conditions: identify the mask derivation (per-section/per-mesh key schedule) from a tool or spec, or find a file pair that shares a schedule.

## Embedded Marcas physics vs GTR2 target fields (2026-11-26)

`validate_embedded_marcas_config()` encodes inclusive numeric envelopes for all 174 numeric keys in the 17 EXE-embedded vehicle configs. Cross-checking against the GTR2 target validators gives a **negative result for direct field copying**:

| Source → target | Shared keys | Source range inside GTR2 bounds | Incompatible |
|---|---:|---:|---:|
| Marcas `.hdv` → GTR2 `.hdc` (`HDC_NUMERIC_BOUNDS`) | 19 | 6 | **13**: `brakediscinertia`, `bumpstage2`, `bumpstopdamper`, `bumpstopspring`, `bumptravel`, `fastbumpsetting`, `frictiontorque`, `pressuresetting`, `reboundstage2`, `reboundtravel`, `slowbumpsetting`, `spininertia`, `springmult` |
| Marcas `.tbc` → GTR2 `.tyr` (`TYR_NUMERIC_BOUNDS`) | 15 | 7 | **8**: `aipeakslip`, `airtreadrate`, `aiwear`, `damper`, `radius`, `rollingresistance`, `springbase`, `step` |

Examples: Marcas `pressuresetting` 8–15 vs GTR2 30–65; `frictiontorque` 0.5–3 vs 5.5–12.5; `springbase` 20,000–25,000 vs 30,000–120,000; `step` 0.0125–0.024 vs the constant 0.009. These are different parameterizations/units, so any HDV/TBC → HDC/TYR adapter needs explicit rescaling or target-template defaults rather than name-based copying. The embedded configs still validate against their own derived bounds (all 17 pass).

## StockCarExtreme EXE-embedded resources (2026-11-26) — SOLVED

Fresh key search found `d42ac404-3acf-4a23-b79a-6d58e43a1a9e` (a lowercase GUID in `.keyMan` NAME2 at record 21) decrypts the first `.scn`; LZMA86 properties are `5d 00 00 80` (`lc=3, lp=0, pb=2`, 8 MiB dict) — the earlier brute excluded prop bytes >0x3F, which hid the solution. The general schedule is validated on **204/204** SCE type-1 resources: encrypted type-1 resource *i* uses `key_list()[i + 11]`. `gsc_exe_tool.extract_all()` now decodes **207/218** resources (the rest are unencrypted type-0x100 blobs), e.g. `bolognahistoric.scn` → 212,880 bytes beginning `CUBEASF`. Quick- and full-tier regression tests added. This replaces the earlier "blocked" conclusion; QuickBMS's own script still fails on SCE.

`StockCarExtreme/GSC.exe` (AXS.GS.0 ver 2, 218 resources) uses key material that neither our `gsc_exe_tool.py` nor QuickBMS 0.12.0 with the original `gamestockcar_exe.bms` can decode. Evidence: QuickBMS aborts at the first embedded `GSC.exe` resource with "uncompressed data (-5) bigger than allocated buffer"; bypassing that resource, it aborts on the first `.scn` with the same error. Our decoder tried 890 candidate strings from `.keyMan` (both name fields, upper/lower variants) against BF-CBC with SHA-1 keys — **zero** candidates produced a valid `lzma86head` properties/dict header. The mirror's BMS script header explicitly claims support only for GSC2012, GSC2013 and Copa Petrobras, and marks AMS encryption unsupported; no newer script exists in `../quickbms_scripts`, `../quickbms-mirror` or `../aluigi-mirror-261124` (all copies are byte-identical, MD5 `67ab40f6...`). Unblock conditions: an updated BMS script/tool for the SCE variant, a format spec, or a known uncompressed SCE resource whose plaintext identifies the cipher. Marcas and AMS variants are solved and independently verified; this does not affect them.

## Decrypted config vocabularies (2026-11-26)

All 26 distinct decrypted configs were surveyed: 8 rFactor `.svm` setups and 18 GTR-family `.hdv/.pm/.ini/.tbc` files. The rFactor setups share **15 universal keys** (`VehicleClassSetting`, `UpgradeSetting`, `Notes`, `Symmetric`, `RWSetting`, `Gear1–5Setting`, `Downforce`, `Balance`, `Ride`, `Gearing`, `Custom`) with tight numeric envelopes (gear1 1–3 … gear5 22–39; downforce/balance/ride/gearing constantly 0.5; symmetric/custom constantly 1). GTR-family configs have **no universal key across all 18** but strong per-family vocabularies (`.hdv` 280+ shared keys, `.tbc` 39, `.ini` 32, `.pm` 3) and 24 bounded chassis/brake fields. `validate_decrypted_gm_config()` enforces these; full-tier regression test. Conversion-relevant: rF1 setups remain a strict subset of GTR2 setup vocabulary with impossible-to-derive car-specific keys, but the decrypted GTR templates now provide concrete numeric ranges for any template-based adapter.

## Encrypted `.svm` setups (2026-11-24) — SOLVED 2026-11-25

**Correction to the negatives below:** all 10 encrypted `.svm` files and all 18 `gMb1.002f` configs are now decoded by `isi_gm_crypt.py`, an independent Python implementation of Luigi Auriemma's GPLv2 `rfactorgmdec` algorithm (obtained from `../aluigi-mirror-261124/papers/rfactorgmdec.zip`). Keynums: rFactor `0` for `.svm`, Top Race 2009 `0x000dfc2a` for TC2000/TR2009 gMb files, Superleague `0x0001be0b` for SLF09 files. Output is 100% printable setup/physics text, e.g. `VehicleClassSetting="FormulaIS"` and `[GENERAL]`. The earlier "no decoder" conclusion was wrong because our brute-force emulation had an off-by-one in the state update (`i` is incremented before the XOR). The separate GTL `Encryptomatic` cipher documented in `../gtl-tools/gtl_files.py` does **not** decrypt these files — two distinct ciphers share the `//[[gMb...]]` header. See `docs/tools-reference.md`.

## Archived negative record (kept for provenance)

10 shipped `.svm` files (only **2 distinct payloads**, duplicated across corpora: `Toban Long.svm` 558 B and `Orchard Lake Oval.svm` 449 B) carry `//[[gMb1.000f ...]]` headers followed by a high-entropy payload beginning `5b 79 6d 98 7f 80 a9 e0` (221 distinct byte values, ~11 short ASCII runs, implausible f32 alignments). The two payloads share a 20-byte prefix. Exhausted offline hypotheses:
- single-byte XOR (0..255): best printability 0.45, no valid plaintext.
- XOR with filename / `gMb1.000f` / `gMa1.000f` / `ISI` / `gtr2` / `rFactor` repeating keys: 0.33-0.40 printability, no valid plaintext.
- gzip / raw-deflate / bz2 / lzma: all fail.
- `isi_crypt` forced enctypes 0/1 with skips 0..64: best 0.475 printability, no valid decrypt.
- JCA with all known keys: no valid decrypt.
Known-plaintext XOR against typical GTR2 setup prefixes (`[GENERAL]\r\n`, `VehicleClassSetting=`) yields no repeating keystream or recognisable pattern. **Undecoded** — likely a proprietary compiled/encrypted setup format; needs the originating tool or source. No speculative decoder added.

Header-field key-schedule probe: the `gMb1.000f` encrypted SVM 12-byte bracket field is **all zeros** in `Toban Long.svm` and only `0x2c7` in `Orchard Lake Oval.svm` — effectively no key material. Seeding four keystream generators (xorshift32, LCG 1103515245, ISI crypt2 enctypes 0/1) with every field word plus u32 words sampled from an unencrypted `.svm` plaintext header (68 configurations) gives best output printability 0.441 vs 0.428 baseline, with zero outputs starting with known plaintext prefixes (`//[[gMa1.000f`, `[DRIVELINE]`). No decoder promoted.

Follow-up (fresh two-payload/cipher probes): the two distinct payloads share a **21-byte identical prefix** and diverge exactly at byte 21; XORing them at every alignment −64..+64 gives a maximum zero-run of 21 at offset 0 (6.9% zero bytes overall) — no shared keystream beyond the common header. Raw Blowfish decryption of the payload without a JCA header, across all 8 versions × default/`raceroom`/`raceroom_plr`/`volvo`/`old_raceroom` keys, peaks at 0.413 printability (vs 0.428 baseline). Raw ISI crypt without a signature header, across all enctypes 0–7 × six key seeds × skips 0/4/8/16, peaks at 0.430 printability (no meaningful improvement). XORing ciphertext against `//[[gMa1.000f`, `[GENERAL]\r\n` and `//[[gMb1.000f` yields aperiodic keystreams with no period ≤64. The payload signature/prefix bytes are category markers, not a known cipher header.

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
  ghost frame is a compact subset, not a raw telemetry dump. However, the earlier single-sample "cross-validation" of slot-12
  heading against position deltas (1.608 rad vs 1.583/1.615 rad) was **superseded
  in 2026-11-26**: the 31-file AIW/motion aggregate finds no coherent relation
  (see the dedicated section above). The local
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

## Coverage gaps (documented, not yet addressed)
- **GTR1 remaining vertex fields**: after confirming fields 4–6 as unit normals, the position/UV roles of the other fields remain unconfirmed. Cross-checking descriptor triples (1,2,3) and (9,10,11) against object-mesh positions from `read_gtr1_object_mesh()` in 60 files gave near-identical median nearest-neighbour distances (1.031 vs 1.000; 45% vs 47% below 1.0), so that comparison does not discriminate. A single ARMCO1 case showed overlap for both triples (5/16 and 6/16). Fields 9–11 are **not confirmed UVs**: field 11 is zero in 39,208/39,208 sampled records, fields 9–10 are outside [0,1] in 37,678/39,208 and are not quarter-step quantized (38,233/39,208). Their triangle-adjacency coherence (400 descriptors, `gtr1_triangle_coherence()`) is 0.706 vs 0.973 for shuffled vertices — genuine but weaker than the position-like fields 1–3 (0.44) and without UV-like value ranges. No UV label promoted. A triangle-adjacency probe on 400 descriptors is more informative: the median ratio of adjacent-vertex to random-vertex distance is **0.439** for fields (1,2,3) vs **0.803** for (9,10,11) (normal benchmark 0.310), supporting position-like spatial coherence of the former. `gmt_semantic.gtr1_triangle_coherence()` exposes this calibrated score with a full-tier regression test. This remains corpus-supported inference, not a strict position label; no semantic labels promoted.

- **Lexus IS F Track Time / Simulador Top Race 2009 reference resolution (not applicable)**: neither install ships `.aud`/`.car` files, loose or in their 21/26 MAS archives (media-only: GMT/textures, plus 189 archived MP3 in TR2009). Audio is loose WAV (148/158 files) and vehicle configs are encrypted `gMb1.002f` (TR2009) or rF1-era text. The full-tier corpus-fact test now covers four such installs; no `.aud`/`.car` reference validator applies.

- **NASCAR SimRacing / NT2003 reference resolution (not applicable)**: neither install ships `.aud` or `.car` files, loose or in their 311/179 MAS archives. Audio is loose WAV (105/91 files) plus archived `.djs` playlists, and vehicle configs are `.veh`/`.hdv` text. Full-tier corpus-fact test added; no `.aud`/`.car` reference validator applies.

- **Superleague Formula 2009 reference resolution (not applicable)**: no `.aud` or `.car` files exist, loose or in its 28 MAS archives; audio is 101 loose WAV plus 5 loose MP3 files, and vehicle configs are `gMb1.002f` encrypted (e.g. `SLF09.hdv`, `SLF09_engine.ini`, `SLF09_susp.pm`) — the opaque SimBin encrypted-config family. Full-tier corpus-fact test added; no reference-resolution validator applies.

- **TC2000 reference resolution (not applicable)**: TC2000 ships **no** `.aud` or `.car` files, loose or archived. Its 34 MAS archives (23,604 members) contain 189 `.mp3` audio members and media, while vehicle/track configs are `gMb1.002f` encrypted (e.g. `.hdv`, `.pm`, `.ini`, `.tbc`), already identified as the opaque SimBin encrypted-config family. No reference-resolution validator can be built for this install; a full-tier test locks in the corpus fact (zero `.aud`/`.car`, >100 archived `.mp3`).

- **AIW coverage extension**: pointer/path validation was extended to RF1Vanilla (39 files / 41,231 waypoints), Automobilista (145 / 132,580), StockCarExtreme (70 / 64,405) and F1 2002 (18 / 17,761) — all pass, for a total of 465 files / 457,832 waypoints. These corpora need no decryption for loose AIWs; F1 Challenge 99-02 ships none (no archived `.aiw` members in a 40-archive sample). The stricter waypoint validator flags a third file, `RF1Vanilla/Lienz_24H.AIW` (one track waypoint with `wp_perp` norm 0.9461), alongside the two Race07Complete addon tracks; all three are documented content defects.

- **gMb1.002f cross-file keystream test (negative)**: among the 18 encrypted payloads, only two clusters share leading ciphertext bytes: the TC2000 and TR2009 `doublewishbone.pm` copies are **byte-identical for 5,078 bytes** (same source file and key), and `tc2000_a/b/p.hdv` share 51–52 bytes. All other pairs are at chance similarity. Deriving a keystream from the plain `doublewishbone.pm` counterpart (best alignment offset 403) and applying it to the encrypted file gives only 0.682 printability; applying that keystream to `trv6_09.hdv` gives 0.613 with no recognisable text. There is no cross-game shared keystream to exploit, so TR2009's `.hdv` remains undecoded.

- **Encrypted `.svm` vs `gMb1.002f` cross-family test (negative)**: compared the 2 distinct encrypted `.svm` payloads against all 17 distinct encrypted `gMb1.002f` payloads. No pair shares even one leading byte, and XORing at every alignment −64..+64 yields a maximum zero-run of **2** with ≤0.81% zero bytes (chance level for random data). The two families do not share a keystream, prefix, or container cipher despite both using `gMb1.00xx`-style headers; no cross-family decoder is possible from this evidence.

- **AIW addon-track exceptions**: extending pointer validation to GTR2Steam and Race07Complete found 201,855 waypoints across 193 files with all pointers either -1 or in range and all `wp_path` values finite/bounded. Pointer -1 in slots 0/1 occurs in only 7 records, all in Race07Complete's addon `Hill.AIW`, so it is accepted as a "no link" sentinel. The stricter `validate_aiw_waypoints()` still flags two addon tracks: `Hill.AIW` (zero-length `wp_perp` on track waypoints) and `Nurburg.AIW` (class-200 waypoints with `bitfields=0`). These are documented content defects, not parser errors; no rule relaxed for them.

- **GTR2 base-vertex f0/f7 probe (f7 decoded)**: across 302 archived GTR2/GTL meshes with ≥100 vertices, `f0` is now structurally characterized: across **15,628,002** base vertices it is zero in 15,556,434 (99.5%); the 71,547 nonzero values occur in exactly **one vertex per mesh, always vertex 0** (71,547/71,547), exposed as `gmt_format.mesh_marker()` with a full-tier regression test. The packed u16 halves are small integers (60,923/71,547 have the low half <1000) but do **not** match material index, mesh ordinal or vertex count, and no UV/color quad-reuse pattern was found (nonzero values are too sparse for per-corner UVs). The pair's semantics remain unresolved; it is a per-mesh marker, not per-vertex data. A table-index probe on all 71,547 markers found no consistent target: the low half matches a material ordinal in only 7,868 cases (11%), the high half in 14,275 (20%), ASCII string offsets in 459/416, material-record starts in 352/345, and both halves are below the material count in only 6,558; these rates are consistent with coincidence in files with many materials. A two-u8 reading (bytes 0 and 2) is also not universal: both intervening bytes are zero in only 13,918/20,005 sampled markers. A mesh-local geometry probe found only weak correlations between either halfword and vertex/index count (r≈0.12), first-vertex position (|r|≤0.02) or bounding-box dimensions (|r|≤0.09) across all 71,547 markers; marker values do repeat across meshes (e.g. `0x3` in 1,679 meshes), but not in any geometry-derived pattern identified. No decoder promoted. `f7`, however, varies in 40 meshes and is a **packed color word**: 11,841/11,841 values have high byte 255 and equal lower three bytes (grayscale colors such as `0xff343434`). `gmt_format.unpack_vertex_color()` exposes the four bytes; channel order is not asserted because all sampled colors are grayscale. This confirms `f7` is not a packed UV pair and explains why VRL UV-like coordinates cannot be transferred through it. Full-tier regression test added.

- **GTR2 48-stride extra vertex blocks are not UV streams**: a full scan of all 761 GTR2/GTL archives (plus 1,500 loose GMTs) found exactly **one** mesh with `has_extra_vertex_block` — `FUELHOSE.GMT` (738 extra records) — and every record is `[0.0, NaN, 0.0, 0.0]`. Finite values are all exactly 0.0; there are no coordinate-like values, quad-corner reuse patterns, or plausible UV ranges. This rules out transferring decoded VRL UV-like coordinate pairs through the 16-byte extra block, and supports leaving UV mapping out of the VRL/GTR1 → GTR2 converters rather than guessing at packed base-vertex fields.

- **SCGT `.ani` is text, not binary ANM**: the single archived `ANI.ANI` (1,802 B) is CRLF text with 12 `AnimRuleName` blocks; `anm_format.read_anm()` rejects it (`unsupported ANM version 791621423`). A dedicated text parser/validator now covers it (frame count == sequence length, indices in range, positive rate, methods manual/transient). No binary ANM decoder applies to this file. Its 12 `AnimBaseName` values (`exha`, `Tailt`, tire anims, etc.) resolve to **no** shipped member: the corpus has zero `.anm` files and none of the 3,756 distinct archive member names match or start with those bases. The rules describe editor-level animation sequences not shipped as standalone files; no reference validator applies.

- **SCGT `.prt` object references (negative)**: the 5 archived `.prt` scene files are well-formed CRLF ASCII with balanced braces (7 `Group`, 940 `Instance` records, 977 `ObjFile` references), validated by `simbin_text_tool.validate_prt()` with a full-tier test. None of the 977 object names resolve to archive member basenames, `.vrl` meshes, `.scn` declarations or `.aiw` content; the references appear to be stale editor-level object IDs. No reference-resolution rule promoted.

- **AIW event/checkpoint fields**: `WP_EVENT` appears only in the four SimBin corpora (198,932 records); its first component lies in [0.5, 1.5], canonical form `1.000,0,0`. The other two fields are frequently bit-pattern garbage (e.g. `0xcdcdcdcd` debug fill, float-bits `1065353216`) and are not validated. `WP_SCORE` checkpoint values are strictly 0/1/2 across all 465 AIWs (188,749 / 141,874 / 127,209). `validate_aiw_event()` with full-tier regression test.

- **AIW path/perp bounds**: `WP_PATH` components lie in [-20.16, 17.54] across 915,664 values from 465 AIWs. `WP_PERP` vectors are unit length in 448,579 records and all-zero in 9,252; the sole nonzero non-unit vector (norm 0.9461) is in `RF1Vanilla/Lienz_24H.AIW` and is exempted. `validate_aiw_path_perp()` with full-tier regression test.

- **AIW dwidth/groove-lat bounds**: `WP_DWIDTH` components lie in [-28.95, 100] across 1,831,328 values from 465 AIWs. `WP_GROOVE_LAT` is a signed lateral offset in [-11.7, 12.6] everywhere except `StockCarExtreme/ortona4.AIW`, where 130 values are corrupt (up to 621,683) — that single file is exempted. `validate_aiw_dwidth_groove()` with full-tier regression test.

- **AIW width/groove bounds**: `WP_WIDTH` components lie in [-6.75, 100] across all 465 AIWs (1,831,328 values). `WP_GALPHA` is a groove-darkness scalar in [0,1] in six corpora, but rF1Vanilla (9 files, 3,167 values) and F1 2002 (1 file, 5 values) store packed/bit-pattern values such as -431602080.0 — they are explicitly exempted via `legacy_alpha=True`. `validate_aiw_width_galpha()` with full-tier test.

- **HED head-physics scope**: only 2 `.hed` files ship (one each in GTR2/GTL), so `validate_hed_numeric()` checks vector/ordering invariants rather than overfitting tight bounds: 3-vectors for min/max position and orientation with `min < max` componentwise, spring directions in [-1,1], and broad component envelopes from the two samples. Full-tier regression test; wider numeric bounds would need more samples.

- **ENG/GRB numeric field bounds**: `validate_eng_numeric()` covers 12 engine fields from 66 GTR2/GTL `.eng` files (e.g. revlimitrange 0–8900, emission −3.15..0.85, starter timing 0.2–1.5, idle RPM 1000–2250, inertia 0.08–0.345); `validate_grb_numeric()` covers gearbox `ratio` 7–51 and `bevel` 1–27 from 60 `.grb` files. Full-tier regression test.

- **HDC numeric field bounds**: `HDC_NUMERIC_BOUNDS` covers 20 chassis/suspension/brake fields from 86 GTR2/GTL `.hdc` files (344 records per universal field), e.g. springmult 0.49–1.2, bumptravel −0.12..−0.02, reboundtravel −0.3..−0.12, bumpstopspring 35k–250k, frictiontorque 5.5–12.5, spininertia 0.55–1.85, camber 0–42, brake torque 1017–4000. Full-tier regression test.

- **TYR numeric field bounds**: `TYR_NUMERIC_BOUNDS` covers 18 fields from 41 GTR2/GTL tire files (242 records per universal field), e.g. radius 0.249–0.355, width 0.105–0.36, springbase 30k–120k, springkpa 600–1396.58, damper 1000–3850, softness 0.5–1.0, aigripmult 0.97–1.17. Four "near-zero" fields are actually tiny non-zero constants (`radiusrpm` 1.01e-6, `wearrate` 1.28e-7..1.05e-6, `aiwear` 4.05e-8..9.2e-8) — rounded surveys must not treat them as zero. Full-tier regression test.

- **AUD numeric event bounds**: `AUD_NUMERIC_BOUNDS` in `validate_aud_map()` covers 20 high-frequency keys. Initial bounds from the four validated corpora were too tight for generated/modded trees (e.g. `enginerange=50`, `engineambient=14`, `naturalrpm=18000`), so they were widened to the global corpus envelope (RPM multipliers 0..4, backfire/splutter 0..50, shape keys 0.7..1.0, ambient 0.5..20, ranges 40..140, `maximumrpm` 1417.08..30590). Full-tier regression tests pass across all corpora. The path/numeric key split remains a strict invariant (139 path-valued vs 34 numeric-valued keys, no mixing).

- **SVM numeric bounds**: `validate_svm_numeric()` checks 11 high-frequency numeric keys against inclusive corpus-observed ranges (e.g. `brakediscsetting` 0..1, `brakepadsetting` exactly 2, `slowbumpsetting` 0..19, `pressuresetting` 4..107, `cambersetting` 0..160). Verified across all 21,183 plain `.svm` files (517 rF1 + 20,666 GTR2 variants from the earlier survey); encrypted `gMb1.000f` payloads are skipped. Bounds are intentionally broad across cars/games. Full-tier regression test.

- **TRK camera-name namespace negative**: across 152 GTR2/GTL/Race07 track scripts with sibling `.cam` files, none of 288 `View=` references or 135,196 `Instance=` references matches a parsed `.cam` camera name (0 matches). These are separate namespaces — `View` names view definitions, `Instance` names scene objects, while `.cam` names cameras. Full-tier corpus-fact regression test.

- **AIW camera-reference negative**: none of the 465 AIW files across the eight validated corpora contains a `ControlPoint` or `camera` token (case-insensitive). Camera/ControlPoint data lives in `.cam` and `.trk` files, not AIWs, so no cross-reference validator applies. Full-tier corpus-fact regression test added.

- **GDB TerrainDataFile references**: `parse_gdb_terrain_refs()` extracts `.tdf` overrides from rF1-era event files. RF1Vanilla has 26 references, all resolving to loose or archived `.tdf` files; F1C/F12002/NT2003 event files contain no `TerrainDataFile` keys. Full-tier regression test; no exceptions.

- **AIW Features vs actual counts (negative)**: all 464 AIWs with a `[Features]` section carry `pitlanes`, `startinggrid`, `pitspots`, `garagespots` (plus `auxspots` in 254 and `waypointspan` in 177). These are engine capacity/default settings, **not** counts of the GRID/PITS sections: `startinggrid` exceeds GRID size in 447/464 files (104 vs 36 typical), `pitspots` differs from PITS `pitpos` count in 445/464, and `garagespots` (usually 3) never equals `garpos` count. No consistency validator applies; full-tier corpus-fact test.

- **AIW TELEPORT consistency**: `validate_aiw_teleport()` checks 447 AIWs: GridIndex values are unique, with a contiguous main run 0..N-1 and optional pit-box indices >=100 appended (e.g. `100, 103` in `Curitiba_Oval`, `Macau`, `Puebla`). Pos and Ori counts always equal GridIndex counts (447/447). Full-tier regression test.

- **AIW GRID/PITS consistency**: `validate_aiw_grid_pits()` checks 465 AIWs: GRID Pos count always equals GridIndex count; garage Pos/Ori counts match and are 2× or 3× pit counts (459 3×, 5 Brianza files 2×); optional SCR counts match garage counts in all 36 files that have them. `Brianza_JR.AIW` has one extra TeamIndex entry and is exempted via a flag. Full-tier regression test.

- **GDB texture-reference negative**: none of the 252 GTR2/GTL/Race07 `.gdb` files contains any key mentioning sky, texture, DDS, TGA or image. `Weather` is a numeric index (0–4, 237 occurrences), not a texture filename. Sky/environment maps are selected by `.trk`/`.cam` files, not event GDBs. Full-tier corpus-fact regression test.

- **GDB race-setting bounds**: `GDB_RACE_BOUNDS` covers 17 fields from 252 GTR2/GTL/Race07 event files: laps 2–999, race time 4–1440 min, weather 0–4, AI grip 0.8–1.6 dry / 0.6–1.2 wet, point allocations −30..40, ambient 11–30 °C, track 13–37 °C, attrition 10–220, latitude −35..85. Full-tier regression test.

- **TRK View-block fields**: `validate_trk_view_fields()` enforces corpus bounds from 152 GTR2/GTL/Race07 track scripts: FOV 62.5–77.75, clip planes 0.5–10000, colors 0–254, view sizes 0.5–512, and `Clear` strictly TRUE/FALSE (302 TRUE / 4 FALSE). Full-tier regression test.

- **ANM bone-name negative**: across 904 archived `.anm` files in F1C/F12002/NT2003 (SCGT and RF1Vanilla ship none), 13,005 decoded bone names were compared with all `.gmt`/`.vrl`/`.mts` member basenames in the same corpora: only 2 matches (chance level). Bone names are internal node labels (`_END`, `MAIN`, `FCHAIN`, ...), not mesh references; no cross-reference validator applies. Full-tier corpus-fact regression test.

- **TDF numeric bounds**: `TDF_NUMERIC_BOUNDS` covers 17 surface grip/bump fields from all 203 local `.tdf` files across ten corpora (roads 0.7–1.04 dry / 0.7–0.8 wet, rumble 0.64–0.99 dry, bump amplitudes 0–0.1, lengths 0–54). Full-tier regression test.

- **CAM numeric bounds**: `CAM_NUMERIC_BOUNDS` covers 14 scalar/vector fields from 258 GTR2/GTL/Race07 `.cam` files: FOV 1–102, clip planes 0.05–9700, color 0–249, size/center fixed at 1/0.5, mipmap bias -1..2, LOD multiplier 0.75–65536, rates 0..999 and shake magnitude 0..48. Full-tier regression test.

- **RCD numeric bounds**: `RCD_NUMERIC_BOUNDS` covers 19 driver-stat keys across 3,310 `.rcd` files in the full local corpus. Initial envelopes from game installs were too tight for generated/modded trees (`minracingskill=0.9`, `composure=0.01`, `crash=60.7`, `recovery=100.0`), so they were widened to the global observed range. Full-tier regression test passes.

- **CAM ControlPoint vs AIW waypoints (negative)**: `parse_cam_control_points()` extracts 290 XYZ ControlPoint triples from GTR2/GTL/Race07 `.cam` files with sibling AIWs. None lies within 2 m of any AIW waypoint (nearest examples 14–17 m), with or without the documented X/Z sign flip. ControlPoints are camera-path spline nodes, not waypoint references; full-tier corpus-fact regression test.

- **GEN numeric fields**: `.gen` mesh configs are rF1-era (272 files across ten corpora; none in GTR2/GTL installs). `LODIn` components are 0..350, `LODOut` 0..3000, and all 167 `ReflectPlane` values are unit 3-vectors with a zero fourth component. `validate_gen_numeric()` with full-tier regression test.

- **VEH numeric/reference scope**: the 371 rF1-era `.veh` files all carry the seven universal keys (`HDVehicle`, `Graphics`, `Sounds`, `Classes`, `Driver`, `Number`, `Team`). Only `Eyepoint` is truly numeric (100 triples, components -0.1..1.05); other "numeric" keys are text with embedded numbers (e.g. class years) and are not bounded. `validate_veh_numeric()` with full-tier test.

- **WAV trailing chunks**: `wav_chunks()` walks RIFF chunks and `validate_wav_chunks()` enforces fmt-first, exactly one data chunk, and a closed chunk-ID set: `fmt `, `data`, `PAD `, `LIST`, `fact`, `bext`, `LGWV`, `_PMX`, `DISP`, `cue `. Verified on sampled GTR2/GTL/Race07/Volvo files. Two edge cases handled: final odd-sized chunks may omit the word-alignment pad byte, and `cue ` chunks occur in some GTR2 sound effects. Full-tier regression test.

- **WAV header scope**: `wav_header()` / `validate_wav_header()` cover PCM (format 1) consistency: 2 channels or 1, 8/16-bit, sample rates 8k/11.025k/22k/22.05k/44.1k/48k, with block-align and byte-rate arithmetic verified on sampled GTR2/GTL/Race07/Volvo files. WAVE_FORMAT_MPEGLAYER3 (0x55) files are common in GTR2 (100/692 sampled) and GTL (1/553) — they are deliberately left opaque (no PCM arithmetic to check). Volvo's JCA WAVs require the explicit `volvo` key; the default key fails. Full-tier regression test.

- **SCR Move/Parent reference validation**: `parse_scr_move()` splits a `.scr` Move value into quoted actor and uppercase animation tokens. Across four rF1-era corpora, 1,177/1,177 actor references resolve to another Actor or archive member and 1,160/1,160 Parent references resolve to an Actor or `world`. The 1,170 animation tokens (`FRONT_JACK_UP`, `LOLLIPOP_UP`, ...) resolve to **no** `.anm` member or bone name (standalone-animation hypothesis negative); they are internal mesh sequence names. Full-tier regression test.

- **rF1-era GDB class-reference negative**: RF1Vanilla/F1C/F12002/NT2003 GDBs (81 files) contain no `SpecialClasses` or `Game Filter` sections at all — they use `Filter Properties = ...` instead. The 154 tokens found are season/event filters (`2006`, `nscrs`, `srgrandprix`, `owchallenge`), and **0/154** match Classes/Categories tags declared in the 479 local `.veh`/`.hdv` files. No cross-format class validator applies; full-tier corpus-fact regression test added.

- **GDB SpecialClasses resolution**: `parse_gdb_class_blocks()` extracts `SpecialClasses` / `SpecialClassesShort` block keys; 112/117 SpecialClasses keys (95.7%) resolve to local `.car` class tags across 252 event files. All five misses come from the DLC file `Race07Complete/SIM_OFFICIAL_VENOM.gdb` (`WTCC_2007`, `F3000`, `FBMW`, `RAD`, `Caterham` — classes not shipped in the install), and the same five recur in its `SpecialClassesShort` block (3/8 resolve). Full-tier regression test; no strict validator promoted.

- **GDB filter class resolution**: across 252 GTR2/GTL/Race07 event `.gdb` files, 163/166 filter class tags (98.2%) resolve to `Categories`/`Classes` tags declared by local `.car` files. Three misses are content/type gaps: `SIM_FALC` (GTL `Cup_DAG.gdb`), `SIM_ELI` (GTL `Cup_DAG2.gdb`), and `WTCC_2007` (Race07 `WTCC_2006_OFFICIAL.gdb`). Full-tier regression test; no strict validator promoted because the misses are legitimate content gaps.

- **SCN reference resolution (partial)**: across 132 MASFile references in RF1Vanilla/F1C/F12002/NT2003 scene scripts, 131 (99.2%) resolve to a local archive; the sole miss is `F3.mas` from `RF1Vanilla/Vview.scn`. SearchPath entries are largely stale: only 13/83 resolve to an existing directory, almost all misses being NT2003 `SEASON03\...` paths (no `Season03` directory ships). Full-tier regression test locks in both rates; no SearchPath validator promoted because the missing directories are content gaps.

- **TRK reference resolution**: `parse_trk_refs()` extracts MASFile/MeshFile basenames; across 152 GTR2/GTL/Race07 track scripts all 293 MASFile refs and 140,120/140,123 MeshFile refs (99.998%) resolve to local files or archive members. The only misses are three Race07 Hockenheim layouts referencing an absent `3d_l_people48.gmt` crowd mesh. Full-tier regression test.

- **CAM ActivationRadius semantics (partial)**: across 1,153 cameras in GTR2/GTL/Race07Complete every `ActivationRadius` is a positive integer (635 multiples of five). It is **not** a sphere around the camera position: only 1% of non-sentinel cameras have `|ActivationLocation − AIW camera position| <= radius` (distances up to 7,314 vs radii 4–805), and correlation with `|ActivationLocation|` is only 0.098. The deactivated-camera sentinel (FLT_MAX location, radius 1) remains the only confirmed semantic; no new trigger rule promoted.

- **`.cin`/`.scr` script reference probe**: GTR2Steam, GTLSteam and Race07Complete ship zero `.cin`/`.scr` scripts (full-tier corpus fact test); these formats are rF1-era. In seven rF1-era corpora, 1,127/1,321 `.scr` Actor Mesh references (85.3%) resolve to archive member basenames; the 194 misses are dominated by pit-crew wheel variants (`lrwheelon.mts`, `rrwheeloff.mts`) not shipped as standalone members. Full-tier regression test asserts >80% resolution; the missing meshes are documented DLC/variant gaps, not a parser failure.

- **RaceRoomTheGame reference resolution (negative)**: the first RaceRoom install shows the same partial-audio pattern as RaceRoom2. All 8 `.aud` files decrypt with the JCA `volvo` key, but only **196/318** WAV references (61.6%) resolve locally — 122 references across **70 distinct missing basenames** (surface/skid sounds such as `gravel_skid_int.wav`, `dustcloud.wav`, `rain_ext.wav`). All 38 `.car` files decrypt but expose no standard HDVehicle/Graphics/Sounds references, so no `.car` validation applies. Together with the RaceRoom2 result, neither RaceRoom install supports a strict reference-resolution validator.

- **RaceRoomTheGame2 reference resolution (negative)**: all 14 `.aud` files decrypt with the JCA `volvo` key (matching its GMTs/shaders), but only **381/739** WAV references (51.6%) resolve to local files — 358 references over **196 distinct missing basenames** (surface/engine/skid sounds such as `rain_ext.wav`, `gravel_skid_int.wav`, `bmw_e90_2007_idle.wav`; `SafetyCar_BMW_e90.aud` lacks 99). Uppercase `.WAV` files are included in the scan, so this is a partial-install gap, not a parser failure. All 102 `.car` files decrypt but expose only 3 standard config references (3/3 resolve), too few to validate. Unlike the five corpora with validated resolution, this install cannot support a strict WAV-reference validator. No speculative rule promoted.

- **SCGT `.vrl` section payloads — earlier claim corrected**: the earlier note that the post-vertex sections are "not vertex-index lists" was based on sampling the wrong section (the first N*4 block is a flags array with constant value 15). The M*4 block at table index 10 is in fact a **vertex-index list**: all indices < N in 3,000/3,000 files. The two following M-float arrays are finite and bounded (|v| < 1e5) in 3,000/3,000 files and form plausible texture coordinates, but their exact UV semantics remain unproven (the second component can exceed 1, up to ~96, indicating tiling or a different axis). The N*4 region between the vertex block and the index list is now structurally decoded as 13 consecutive N-element arrays: blocks 0–7 all zero, block 8 constant 15, blocks 9–10 zero, block 11 a sorted vertex map starting at 0 with all values < M, and block 12 small per-vertex group IDs (<256) — all 3,000/3,000 on those bounds. Two `CONE10.VRL` copies are exceptions: their vertex map is not strictly increasing (2,998/3,000 strict) and three group IDs are zero; the validator tolerates these. Whether the group IDs are material indices remains unconfirmed.

`.vrl` coordinate semantics are now **corpus-supported (not strictly proven)** as per-corner texture coordinates: consecutive four-corner groups reuse at most two U and two V values in 75.3% of groups on average across 1,046 divisible-by-four files, vs 27.1% for randomly shuffled corners. Repeated vertex indices often carry different coordinates (only 23.5% of files have exactly one UV per index), consistent with texture seams. `simbin_text_tool.vrl_uv_quad_score()` exposes this calibrated score with a full-tier regression test; no per-corner semantic labels are asserted beyond UV-like behaviour.

