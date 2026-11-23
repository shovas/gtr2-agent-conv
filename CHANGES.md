# Changes

Newest-first change log. Timestamps use repository commit dates (ISO 8601, local offset).

## 2026-11-23 18:00:00 -0500 - BC6H UF16 DDS decode
- Added `bc6h_format.py`, decoding the two non-transformed BC6H UF16 modes (two-subset 6-bit and one-subset 10-bit) from spec-derived Khronos BPTC tables. `media_tool.py` now reads DX10 `BC6H_UF16` DDS files; write-back is intentionally unsupported. Verification: 4,000/4,000 random blocks match an independent spec-table reference, plus 8 synthetic-fixture tests. A 48,459-file loose-DDS scan confirmed no DX10 samples exist locally.

## 2026-11-23 17:30:00 -0500 - Multi-bone ANM decoding
- Extended `anm_format.py` to the corpus-verified multi-bone layout: 40-byte per-bone headers + TRS/time keys (32-byte stride), with time=0 sentinel handling. All 904 archived ANM files decode; tests updated.

## 2026-11-23 17:00:00 -0500 - Single-bone ANM decoder
- `anm_format.py` decodes the 162 single-bone ANM files in the corpus: 12-byte name + version + bone name + 32-byte TRS/time keys from +76 (position, unit quaternion, monotonic time). The 742 multi-bone files are reported as unsupported rather than decoded speculatively. Added CLI, tests and docs.

## 2026-11-23 16:30:00 -0500 - DXT4 decode and corpus surveys
- DXT4 DDS now decodes as a DXT5-alpha variant (alpha matches ffmpeg byte-exactly on the local sample). Documented the 2 undecoded SCGT compressed members, the 904-file `.anm` header survey, and corrected stale counts.

## 2026-11-23 16:00:00 -0500 - 8-bit palettized BMP support
- `read_bmp()` now handles 8-bit BI_RGB with palette/indices/trailer preservation; a real corpus sample (`legal256.bmp`, 512x384) round-trips byte-identically. Compressed DIB variants confirmed absent from the corpus.

## 2026-11-23 15:30:00 -0500 - Final verification after BC4/BC5 decode
- `python3 run_tests.py --mode full`: 47 modules / 320 tests / 794.3 s, 0 failures, 2 skips. Normal: 167 tests / 291.7 s, 0 failures. Quick: 96 tests, 0 failures. Pre-push check PASS.

## 2026-11-23 15:00:00 -0500 - BC4/BC5 DDS decode
- Native BC4/BC5 decode added (`BC4U`/`ATI1`/`BC5U`/`ATI2`) with known-palette synthetic fixtures; BC6H/BC7 and cube maps remain unimplemented (absent from the local corpus). Added regression test.

## 2026-11-23 14:30:00 -0500 - TGA RLE encoder improved
- `_encode_tga_rle()` now emits real run packets instead of raw-only packets; a corpus RLE TGA round-trips to 532,356 bytes (original 534,231) with identical decoded pixels. Added regression test.

## 2026-11-23 14:00:00 -0500 - Lossless mipmapped DDS round-trip
- `read_dds()` now preserves the full mip chain and level-0 payload; `to_bytes()` reuses original compressed bytes when RGBA is unchanged. Two mipmapped corpus files (DXT1 12 mips, uncompressed 11 mips) round-trip byte-identically. BC4/5/cube maps confirmed absent from 7,480 local DDS files.

## 2026-11-23 13:30:00 -0500 - JPG/MP3 semantic decode/encode
- `media_tool.py jpg-decode|jpg-encode` (Pillow) and `mp3-decode|mp3-encode` (ffmpeg) added with corpus round-trip tests on real GTR2 samples. Both produce valid identifiable output; conversion is lossy.

## 2026-11-23 13:00:00 -0500 - Final verification after WAV encoding
- `python3 run_tests.py --mode full`: 47 modules / 315 tests / 761.8 s, 0 failures, 2 skips. Normal: 167 tests / 289.4 s, 0 failures. Quick: 96 tests, 0 failures. Pre-push check PASS.

## 2026-11-23 12:30:00 -0500 - WAV encoding and JCA key auto-detection
- `wav-encode` converts PCM to ADPCM/MP3 via ffmpeg (round-trip verified); `detect_jca_key()` auto-detects the `default` and `volvo` JCA keys from payload magic (12 sampled files across 2 corpora). Added tests.

## 2026-11-23 12:00:00 -0500 - Final verification after media capabilities
- `python3 run_tests.py --mode full`: 47 modules / 313 tests / 840.4 s, 0 failures, 2 skips. Normal: 167 tests / 294.8 s, 0 failures. Quick: 96 tests, 0 failures. Pre-push check PASS.

## 2026-11-23 11:30:00 -0500 - Test tier adjustment
- Moved `test_phs_tool` to Full-only; Normal is 167 tests / 294.8 s within the 300 s budget, Full retains all 313 tests.

## 2026-11-23 11:00:00 -0500 - JCA texture support
- Survey found 33,351 JCA-encrypted DDS and 4,415 JCA-encrypted TGA files across 7 corpora. Generalized `decrypt_jca_bytes()` with `dds-jca`/`tga-jca` identification and `jca-decrypt` CLI; verified on Race07 samples (DDS 4x4, TGA 512x128 32-bit). Added tests.

## 2026-11-23 10:30:00 -0500 - Compressed WAV decode
- `media_tool.py wav-decode` converts ADPCM and MP3-in-WAV payloads to 16-bit PCM via ffmpeg; verified on the corpus IMA-ADPCM sample (78,047 frames) and MP3-in-WAV sample (17,280 frames). Added tests.

## 2026-11-23 10:00:00 -0500 - JCA-encrypted WAV support
- Survey found 4,112 `.wav` files with the JCA `0fb1ffff` header across 3 corpora. Added `media_tool.decrypt_jca_wav()`, `wav-jca` identification, and `wav-decrypt` CLI; default key decrypts Race07 samples to valid 48 kHz 16-bit PCM WAV. Added regression test.

## 2026-11-24 15:35:00 -0500 - Final verification after format surveys
- `python3 run_tests.py --mode full`: 47 modules / 310 tests / 712.0 s, 0 failures, 2 skips. Normal: 170 tests / 287.2 s, 0 failures. Quick: 96 tests, 0 failures. Pre-push check PASS.

## 2026-11-24 15:05:00 -0500 - Final verification after unresolved-field experiments
- `python3 run_tests.py --mode full`: 47 modules / 310 tests / 719.2 s, 0 failures, 2 skips. Normal: 170 tests / 285.5 s, 0 failures. Quick: 96 tests, 0 failures. Pre-push check PASS.

## 2026-11-24 14:35:00 -0500 - Final verification after shared/archive survey
- `python3 run_tests.py --mode full`: 47 modules / 310 tests / 743.7 s, 0 failures, 2 skips. Normal: 170 tests / 287.0 s, 0 failures. Quick: 96 tests, 0 failures. Pre-push check PASS.

## 2026-11-24 14:10:00 -0500 - Full GTL archive survey
- Ran `convert_config_bytes` over all 497 readable `.gtl` archives (26,455 members): 0 exceptions. Config files are loose in GTL, so no archive members matched the validator-checked extensions.

## 2026-11-24 13:45:00 -0500 - Shared-folder teammaps rename
- `convert_tree()` now renames `teammaps.gtl` to `teammaps2.gtr` (matching the GTR2 archive name and the `.trk` MASFile rewrite). The GTL `Locations/shared` folder converts to 7 clean `.gtr` archives with 0 validator problems. Added regression test.

## 2026-11-24 13:20:00 -0500 - Final verification after multi-track validation
- `python3 run_tests.py --mode full`: 47 modules / 309 tests / 735.2 s, 0 failures, 2 skips. Normal: 169 tests / 284.2 s, 0 failures. Quick: 95 tests, 0 failures. Pre-push check PASS.

## 2026-11-24 12:50:00 -0500 - Multi-track end-to-end validation
- Extended `convert_tree` validation to all 7 GTL track folders with GTR2 counterparts (Anderstorp, Donington, Hockenheim, Imola, Magny-Cours, Monza, Spa): every converted subtree validates with 0 problems using same-extension templates. Added regression test; no new failures to triage.

## 2026-11-24 12:25:00 -0500 - Full rewrite integration in convert_tree
- `gtl_to_gtr2.convert_tree()` now applies every corpus-confirmed rewrite (audio paths/road-noise, HDC clutch, tire default, damage constants, plus template-driven key additions) to loose files and archive members. An end-to-end converted Anderstorp subtree with templates validates with 0 problems; 2 new tests.

## 2026-11-24 12:00:00 -0500 - Final verification after NUL parser fix
- `python3 run_tests.py --mode full`: 47 modules / 306 tests / 698.2 s, 0 failures, 2 skips. Normal: 166 tests / 272.0 s, 0 failures. Quick: 92 tests, 0 failures. Pre-push check PASS.

## 2026-11-24 11:35:00 -0500 - NUL-variant FXM parser tightened
- `parse_nul_name_nodes()` now requires +/-1 scale components when selecting among its 40/80/44/76 keyframe-offset candidates, rejecting false name matches inside strings. Corpus result: 0/8,148 nodes flagged (was 6.43%). Added regression test.

## 2026-11-24 11:10:00 -0500 - Final verification after quantization survey
- `python3 run_tests.py --mode full`: 47 modules / 305 tests / 700.5 s, 0 failures, 2 skips. Normal: 166 tests / 265.9 s, 0 failures. Quick: 92 tests, 0 failures. Pre-push check PASS.

## 2026-11-24 10:45:00 -0500 - Final verification after FXM decoder
- `python3 run_tests.py --mode full`: 47 modules / 305 tests / 706.6 s, 0 failures, 2 skips. Normal: 166 tests / 270.7 s, 0 failures. Quick: 92 tests, 0 failures. Pre-push check PASS.

## 2026-11-24 10:20:00 -0500 - FXM semantic decoder added
- `decode_fxm_semantic()` / `fxm_tool.py semantic` normalise both FXM variants into validated node records. Corpus finding: all 148 standard nodes are static (two identical TRS keys); NUL nodes carry one key and suspect records are flagged rather than dropped. Added regression test.

## 2026-11-24 09:55:00 -0500 - Final verification after FXM invariants
- `python3 run_tests.py --mode full`: 47 modules / 304 tests / 704.4 s, 0 failures, 2 skips. Normal: 166 tests / 271.6 s, 0 failures. Quick: 92 tests, 0 failures. Pre-push check PASS.

## 2026-11-24 09:30:00 -0500 - FXM keyframe invariants codified
- `fxm_tool.check_node_consistency()` validates 148/148 standard FXM nodes across 5 corpora: 84-byte keyframe blocks, unit quaternions, +/-1 scale components, and trailer == size_hint-84. Added corpus regression test.

## 2026-11-24 09:00:00 -0500 - Full rF1 validation sweep
- `validate_conversion.py` over all 8,109 old-layout rF1Vanilla GMTs: semantic bridge passes 8,109/8,109 (4,703 multi-object, 3,406 single-object); structural bridge fails all as expected (geometry not rebuilt). No failures to triage.

## 2026-11-24 08:35:00 -0500 - Final verification after NaN fix
- `python3 run_tests.py --mode full`: 47 modules / 303 tests / 702.7 s, 0 failures, 2 skips. Normal: 166 tests / 281.9 s, 0 failures. Quick: 92 tests, 0 failures. Pre-push check PASS.

## 2026-11-24 08:10:00 -0500 - NaN-aware UV validation fix
- `validate_conversion` now treats two NaNs as equal when comparing float lists. STANDS01.GMT's 192 NaN UV pairs are preserved byte-for-byte; the multi-object sample now passes 500/500. Added a focused regression test.

## 2026-11-24 07:45:00 -0500 - Multi-object geometry validation confirmed
- Re-ran `validate_conversion.py` on multi-object rF1 GMTs: 499/500 pass the semantic bridge end-to-end (the sole failure, STANDS01.GMT, is a UV edge case; positions/faces/tail/independent checks pass). Structural-bridge output is correctly reported as non-lossless. Added regression test.

## 2026-11-24 07:20:00 -0500 - Final verification after record-0 fix
- `python3 run_tests.py --mode full`: 47 modules / 301 tests / 704.7 s, 0 failures, 2 skips. Normal: 164 tests / 263.4 s, 0 failures. Quick: 90 tests, 0 failures. Pre-push check PASS.

## 2026-11-24 07:00:00 -0500 - Multi-object GMT record 0 corrected
- Record 0 of multi-object rF1 GMTs now also comes from submesh 0 (e.g. BUILDING43: vc 313→753, ic 0→753) rather than the misleading 8-u32 table. Validated on 4,703/4,703 multi-object GMTs; regression test strengthened.

## 2026-11-24 06:35:00 -0500 - Final verification after multi-object fix
- `python3 run_tests.py --mode full`: 47 modules / 301 tests / 725.0 s, 0 failures, 2 skips. Normal: 164 tests / 269.9 s, 0 failures. Quick: 90 tests, 0 failures. Pre-push check PASS.

## 2026-11-24 06:15:00 -0500 - Multi-object GMT bridge fixed
- `gmt_layout.old_to_new()` now fills all N mesh records of multi-object rF1 GMTs using the N submesh headers (previously only record 0 was populated). Validated on 8,109/8,109 old-layout GMTs for parse, byte round-trip and relayout; added a multi-object coherence test.

## 2026-11-24 05:50:00 -0500 - Final verification after GDB time invariant
- `python3 run_tests.py --mode full`: 47 modules / 300 tests / 727.1 s, 0 failures, 2 skips. Normal: 163 tests / 283.8 s, 0 failures. Quick: 90 tests, 0 failures. Pre-push check PASS.

## 2026-11-24 05:30:00 -0500 - GDB session time invariant added
- `validate_gdb_times()` checks the session-block `racetime == racetimescaled` invariant (85/85 GTR2 GDBs); later event sections may override RaceTime alone, so only the first occurrence is compared. Added test and docs.

## 2026-11-24 05:05:00 -0500 - Final verification after pipeline relayout
- `python3 run_tests.py --mode full`: 47 modules / 299 tests / 754.3 s, 0 failures, 2 skips. Normal: 162 tests / 283.7 s, 0 failures. Quick: 89 tests, 0 failures. Pre-push check PASS.

## 2026-11-24 04:40:00 -0500 - GMT relayout integrated into rF1 pipeline
- `rf1_to_gtr2.py --relayout` rebuilds GMT offsets after mesh edits; uses the semantic bridge for multi-object GMTs (the structural bridge only fills the first of N mesh records) and supports `transform`/`mesh_transform` hooks. `relayout_gmt()` now preserves legacy oversized vertex blobs. 3 pipeline tests + updated relayout tests pass.

## 2026-11-24 04:15:00 -0500 - Final verification after animation validator
- `python3 run_tests.py --mode full`: 47 modules / 297 tests / 824.5 s, 0 failures, 2 skips. Normal: 160 tests / 272.9 s, 0 failures. Quick: 89 tests, 0 failures. Pre-push check PASS.

## 2026-11-24 03:50:00 -0500 - Animation file validator added
- `.ani` motion blocks: all 8 blocks present in 34/34 GTR2 and 24/26 GTL files (two special variant/pitcrew files). `validate_ani()` and `adapt_ani_from_template()` added with 6 same-name corpus pairs; FXM/GTTF cross-variant and heading-correlation experiments documented as negative.

## 2026-11-24 03:30:00 -0500 - Final verification after damage constants
- `python3 run_tests.py --mode full`: 47 modules / 296 tests / 768.1 s, 0 failures, 2 skips. Normal: 159 tests / 283.7 s, 0 failures. Quick: 88 tests, 0 failures. Pre-push check PASS.

## 2026-11-24 03:00:00 -0500 - Damage-model universal constants implemented
- Ten `.dmg` values are single-valued across all 29 GTL and 26 GTR2 files (wheeldetach 20000→18000, front/rear-wing and part collision params, aero min/div, wall skid threshold, wheel params). `rewrite_dmg_constants()` applies 290 replacements across 29/29 GTL files; GTR2 unchanged. Added validator, tests and docs.

## 2026-11-24 02:40:00 -0500 - Final verification after road-noise rewrite
- `python3 run_tests.py --mode full`: 47 modules / 295 tests / 792.1 s, 0 failures, 2 skips. Normal: 158 tests / 271.8 s, 0 failures. Quick: 87 tests, 0 failures. Pre-push check PASS.

## 2026-11-24 02:20:00 -0500 - Audio road-noise value rewrite
- `vs_inside_roadnoise_dry` uses `gtc_road_roll_int.wav` in 30/30 GTL `.aud` files that define it and `road_roll_int.wav` in all 25 GTR2 files. `rewrite_aud_roadnoise()` converts the value; added validator, test and docs.

## 2026-11-24 02:00:00 -0500 - Final verification after clutch rule
- `python3 run_tests.py --mode full`: 47 modules / 294 tests / 819.0 s, 0 failures, 2 skips. Normal: 157 tests / 279 s, 0 failures. Quick: 86 tests, 0 failures. Pre-push check PASS.

## 2026-11-24 01:40:00 -0500 - Test tiers rebalanced again
- Moved `test_race07_complete` and `test_volvo` to Full-only; Normal is 157 tests / 279 s within budget, Full still runs all 294 tests.

## 2026-11-24 01:20:00 -0500 - HDC clutch constant rewrite
- `clutchengagerate` is 0.6 in all 41 GTL `.hdc` files that define it and 0.8 in all 43 GTR2 files that define it (SafetyCar omits it in both). `rewrite_hdc_clutch()` converts the value, preserving comments; added validator, test and docs.

## 2026-11-24 01:00:00 -0500 - Audio sound-path rewrite added
- All 1,374 sound-path values in 31 GTL `.aud` files use the `Cars\` prefix while all 1,094 in 25 GTR2 files use `GTR\`. `rewrite_aud_sound_paths()` converts 1,488 occurrences across 31/31 GTL files; GTR2 files are unchanged. Added validator, test and docs.

## 2026-11-24 00:45:00 -0500 - Final verification after race-config validator
- `python3 run_tests.py --mode full`: 47 modules / 292 tests / 654.5 s, 0 failures, 2 skips. Normal: 164 tests / 254.8 s, 0 failures. Quick: 84 tests, 0 failures. Pre-push check PASS.

## 2026-11-24 00:25:00 -0500 - Race-config validator added
- `validate_rcd()` checks four cold-brain keys universal in all 223 GTR2 `.rcd` files and absent in all 98 GTL ones. Two values are corpus-universal constants (200/120); the other two are supplied via same-name template adaptation (verified on `cunningham.rcd`) or left for manual review. Added test and docs.

## 2026-11-24 00:10:00 -0500 - Final verification after audio validator
- `python3 run_tests.py --mode full`: 47 modules / 291 tests / 688.3 s, 0 failures, 2 skips. Normal: 163 tests / 274 s, 0 failures. Quick: 83 tests, 0 failures. Pre-push check PASS.

## 2026-11-23 23:50:00 -0500 - Audio key validator added
- `validate_aud()` checks 17 mixing/sound keys universal in all 25 GTR2 `.aud` files (15/31 GTL flagged); `adapt_aud_from_template()` copies them from a same-name GTR2 template. Extended the shared key parser to recognise underscore-containing keys. Added test and docs.

## 2026-11-23 23:35:00 -0500 - HDC key validator added
- `validate_hdc()` checks 30 wheel/gear keys universal in all 44 GTR2 `.hdc` files (34/42 GTL flagged); `adapt_hdc_from_template()` copies them from a same-name GTR2 template. Added test and docs.

## 2026-11-23 23:20:00 -0500 - Test tier rebalanced
- Moved the two expensive corpus surveys (`test_copa`, `test_stockcar_extreme`) to Full-only; Normal is back within its 300 s budget (272 s, 161 tests) while Full retains all 289 tests.

## 2026-11-23 23:05:00 -0500 - AIW and tire validators added
- `.aiw`: scrpos/scrori present in all 34 GTR2 AIWs, none of 25 GTL; 6 same-name template adaptations verified. `.tyr`: WetWeather=1 universal across 15 GTR2 files; added to all 26 GTL tire files. Integrated into `validate_gtr2_tree()` with 2 new tests.

## 2026-11-23 22:50:00 -0500 - Final verification after .car adaptation
- `python3 run_tests.py --mode full`: 47 modules / 287 tests / 640.9 s, 0 failures, 2 skips. Normal: 164 tests / 294.5 s, 0 failures. Pre-push check PASS.

## 2026-11-23 22:35:00 -0500 - .car template adaptation added
- `gtl_to_gtr2.adapt_car_from_template()` copies the four universal GTR2-only car keys (driver1, driver2, externaldriverposition, steeringwheelaxis) from a template, preserving all other lines. Verified on the 1 same-name corpus pair (`safetycar.car`) and 10 generic-template cases; 2 new tests.

## 2026-11-23 22:20:00 -0500 - Final Full-suite verification (GTL conversion work)
- `python3 run_tests.py --mode full`: 47 modules / 285 tests / 658.4 s, 0 failures, 2 skips. GTL->GTR2 validators: GTR2 GameData 0 problems; GTL 0/25 .trk, 0/53 .gdb, 0/96 .car pass; GTR2 34/34, 85/85, 145/145 pass. Pre-push check PASS.

## 2026-11-23 22:00:00 -0500 - GDB session-key validation and template adaptation
- Corpus comparison: all 85 GTR2 `.gdb` files contain 15 universal session keys, none of the 53 GTL files do. `gtl_to_gtr2.py` validates this and can copy the keys from a same-name GTR2 template (6 corpus pairs: 11 missing keys -> 0, all other lines byte-identical). Fixed a CRLF-swallowing regex bug. Also added a `.car` key validator: all 145 GTR2 cars carry four universal keys absent from all 96 GTL cars; values are car-specific so only presence is enforced. A full-subtree test inventories the remaining gaps (shared archives outside the subtree and unmatched GDB templates).


## 2026-11-23 21:45:00 -0500 - GTL->GTR2 container/TRK building block
- `gtl_to_gtr2.py` rewrites `.trk` MASFile entries to GTR2 conventions and repacks `.gtl` archives as type-0 `.gtr`; corpus-verified on 25 GTL `.trk` (0→25 valid after conversion) and 34 GTR2 `.trk` (34/34 valid, idempotent), with subtree conversion, a `--validate DIR` GTR2-convention checker (0 problems on real GTR2 GameData, 646 on GTL; MASFile-reference resolution verified 187/187 GTR2 and 106/106 GTL), and 6 unittests. Full pipeline still needs geometry/physics/config work.

## 2026-11-23 21:30:00 -0500 - Final verification after alignment work
- `python3 run_tests.py --mode full`: 46 modules / 275 tests / 667.3 s, 0 failures, 2 skips. Quick: 67 tests. Pre-push check PASS.

## 2026-11-23 21:15:00 -0500 - DSI/GTT post-marker field alignment resolved
- `ghost_align.py` plus helpers in `simbin_events_tool.py` prove the post-marker byte fields of GTR2 `.dsi` and `.gtt` records share one layout: best byte-alignment lag 0 (score 2.938/3.0 vs 0.357 at lag 4) across 68,774 DSI records and 44,602 GTT frames. The 4-byte phase shift is confined to the pre-marker region. Added reproducible script and two unittests.

## 2026-11-23 21:00:00 -0500 - Final verification after relayout work
- `python3 run_tests.py --mode full`: 46 modules / 272 tests / 656.3 s, 0 failures, 2 skips. Normal: 39 modules / 150 tests / 285.6 s, 0 failures. Quick: 67 tests / ~9 s. Pre-push check PASS.

## 2026-11-23 20:30:00 -0500 - GMT relayout implemented and verified
- `gmt_format.relayout_gmt()` rebuilds header/mesh-record offsets after mesh data changes size, packing vertex/extra/stream/index blobs and the material tail contiguously. Self-consistency tests cover all four structural variants, vertex/index growth, and invalid blobs; verified on 400/400 real GTR2 GMTs and 300/300 GTL GMTs. Added to Normal/Full tiers; exposed as `gmt_tool.py relayout <input> <output> [--align N]`; an r6==0 mesh with streams is hardened so the streams survive a relayout/reparse.

## 2026-11-23 20:15:00 -0500 - Final Full-suite verification
- `python3 run_tests.py --mode full`: 45 modules / 268 tests / 593.5 s, 0 failures, 0 errors, 2 skips (external tools absent). Quick: 67 tests / ~10 s. Pre-push check PASS.

## 2026-11-23 20:00:00 -0500 - GTR2 .dsi instructor-line reader
- `simbin_events_tool.read_ghost_line()` decodes the 63-byte `.dsi` ghost polyline (marker at record +0, position floats at +35/+39/+43) across all 55 local files; added `--ghost-line` CLI flag and test.

## 2026-11-23 19:45:00 -0500 - CUBE MTS rig triples shown to form surface patches
- The per-rig u16 triples decode as coherent triangle surfaces (shared table: 79 faces, 68 vertices, 91/146 edges shared twice, Euler chi=1), ruling out arbitrary indices. Exact engine-side role still unknown; added test.

## 2026-11-23 19:30:00 -0500 - FXM variable-record-length hypothesis excluded
- `tests/test_fxm_records.py` proves `size_hint` (94-100) does not encode a variable keyframe length: in a mixed-hint file all nodes retain fixed 84-byte keyframes with zero gaps.

## 2026-11-23 19:15:00 -0500 - GTR1 coverage added as a regression test
- `tests/test_gtr1_coverage.py` asserts every GTR1-magic GMT in `../GTR1Vanilla` decodes (33,477/33,477); runs in Normal and Full modes.

## 2026-11-23 19:00:00 -0500 - GTR1 decoder coverage verified at 100%
- Full scan of `../GTR1Vanilla`: all 33,477 GTR1-magic GMTs decode via the descriptor grid (10,359) or the descriptor-less object-mesh path (23,118); zero undecoded. Task-plan note marked resolved.

## 2026-11-23 18:30:00 -0500 - Test runner gains tier listing and optional coverage
- `run_tests.py --list` prints Quick/Normal/Full tier membership; `--coverage` adds an optional line-coverage report when the `coverage` package is installed (graceful fallback otherwise). Added a self-test for `--list`.

## 2026-11-23 18:00:00 -0500 - GTTF frame stride corrected (252 -> 63 bytes)
- Fixed `simbin_events_tool.find_frame_grid()`: ghost frames are 63 bytes apart, not 252. The old stride grouped four consecutive samples into one; the corrected reader yields 4x as many frames with smooth per-frame position/time deltas (verified across 12 GTT files, ~4.0x frame counts). Independently confirmed by the 7-byte 63-byte-record marker in the reference-only gtr2-agent-tools ghost loader: marker count matches detected frame count in 29/29 GTT files; ~20 Hz sample rate corroborated. Updated docs and tests.

## 2026-11-23 17:30:00 -0500 - NUL-name FXM variant generalized
- `parse_nul_name_nodes()` now tries keyframe offsets (40,80,44,76), covering windshield-wiper files (keyframe at name+80, trailer `(0,0xb8,1)`). All 160/160 LMA files now parse; added test.

## 2026-11-23 17:00:00 -0500 - NUL-name FXM variant decoded
- `fxm_tool.parse_nul_name_nodes()` decodes the `LMA `-magic FXM variant with NUL-terminated node names: single 40-byte TRS key at name+40, 12-byte trailer. Validated 69/79 nodes in FPDRIVER_Vectra-SteerL_01.FXM and 137/160 LMA files; added test and docs.

## 2026-11-23 16:30:00 -0500 - GTR1 descriptor-less variant decoded
- `gmt_semantic.read_gtr1_object_mesh()` decodes the 22,287 GTR1 files lacking the 0x194 grid: 36-byte triangle records at vertex_offset (u16 indices), 32-byte position records at index_offset (4-byte lead), true count from the object table. ARMCOSHAD01.GMT yields 30 positions / 28 valid triangles; 200/200 files validate. Add tests and document.

## 2026-11-23 16:00:00 -0500 - GMT f0 resolved as first-vertex marker
- Proved that all 302 non-zero f0 values across 108,878 sampled GMT vertices occur at vertex index 0 of a mesh — a per-mesh first-vertex marker, not a per-vertex attribute. Add test and document.

## 2026-11-23 15:30:00 -0500 - GTR1 extra bytes decoded as UV
- Confirmed the GTR1 48-byte vertex record's extra 16 bytes are `[0, u, v, 0]` (zero padding + 2D float UV) across 2,215 vertices in 100 files. Added `uv` field and test.

## 2026-11-23 15:00:00 -0500 - CUBE MTS vertices restored
- Decoded the 64-byte descriptor streams: each record's first 16 bytes hold a 3-float local coordinate + u32 pad. Restored `read_geometry()["vertices"]` (1,561 points across 7 descriptors in TIREMANFRONT). All 79/79 rig-table triples validate as triangles with edge median 0.657. Updated tests/docs.

## 2026-11-23 14:30:00 -0500 - CUBE MTS geometry decode corrected
- Corrected the wrong position decode: 36-byte table records contain indices/materials (ASCII `NASCAR_FACE`), not float positions. `read_geometry()` now decodes descriptor-driven float streams and reports `positions_available=False`. `rig_table_triangles()` validates per-rig triples as triangles into stream_a (39/79 finite, edges 0.2..3.0). Updated tests/docs.

## 2026-11-23 14:00:00 -0500 - GTTF slot 9 speed hypothesis excluded
- Tested GTTF frame slot 9's high u16 against speed derived from position/time deltas across six files: |r| < 0.1, so it is not a speed field. Documented as a negative result.

## 2026-11-23 13:30:00 -0500 - Third-party GMT oracle validation
- Executed the GPLv3 Blender GTR2/rF1 importer's pure parsing functions in /tmp (not committed) against a converted GMT: positions and UVs matched our decoder exactly after accounting for Blender's Y/Z swap and V-flip. Independent confirmation of the semantic bridge. Documented in `docs/open-issues-research.md`.

## 2026-11-23 13:00:00 -0500 - GTR1 universal table at 0x11c
- Found a universal rF1-style 8-u32 table at 0x11c in GTR1 GMTs (20,000/20,000 valid); car meshes additionally have the 0x194 descriptor grid. Added `gmt_semantic.read_gtr1_table()` + test; documented the two-variant layout.

## 2026-11-23 12:30:00 -0500 - Residual-field negative results
- Disproved the FXM `key_count`-as-key-count interpretation (3x28 gives 0/148 unit quats; 2x40 gives 148/148). Documented GMT f0, CUBE MTS rig-table, GTTF slot 7/9, GTR1 extra-bytes and 22,287 descriptor-less GTR1 GMTs as unresolved with specific blockers. Added test and research notes.

## 2026-11-23 12:00:00 -0500 - Offline validation + residual fields
- `validate_conversion.py`: offline GMT conversion validation with exact position/UV/face equality, material-tail check and an independent schema-based cross-check; 100/100 converted GMTs pass. GTTF frames now expose heading (-pi..pi) and a small pitch angle. New-layout GMT f7 decoded as per-vertex ARGB colour; GTR1 vertex stride found to be 48 bytes with unit normals on 5,024/5,024 sampled vertices. GTR1 corpus confirmed installed (`../GTR1Vanilla`). Add tests and document.

## 2026-11-23 11:30:00 -0500 - Docs: refresh stale claims
- Reconciled README, FEATURES, CAPABILITIES, DEPENDENCIES, docs/binary-formats.md, docs/file-formats.md and docs/task-plan.md with verified findings: semantic GMT bridge, GTTF frame grid, all four IRSR variants, Bink decode+encode, EA TGQ decode, PHS resolved as PAR2 recovery containers. Task plan now reflects 244 tests and current open items; historical CHANGES entries left intact.

## 2026-11-23 11:00:00 -0500 - PHS review: program-analysis angles
- Checked GTL executables/DLLs for PAR2 vocabulary (no hits), attempted Wine runtime trace (blocked by missing MFC42), compared recovery slices (distinct exponents 0x35/0x3a/0x3b) and entropy vs controls (slice bodies ≈ random, consistent with parity data). Added evidence to `docs/phs-research.md`.

## 2026-11-23 10:30:00 -0500 - PHS identified as PAR2 recovery data
- Parsed the full PAR2-style packet chain: 64-byte header, contiguous lengths, Main packet (slice 384000, file id 2f1fc214...) and FileDesc naming `GTL_Update_0901.exe`. Four PHS files are recovery containers for one update executable; PHYSICS.PHS is an opaque 13KB blob. Updated `phs_tool.py`, tests, and `docs/phs-research.md` evidence table; recommend defer.

## 2026-11-23 10:00:00 -0500 - Task 4: PHS is a mixed container; Speednut checked
- Found plaintext PAR2-style packets and labels in GTL PHS files (`phs_tool.py`, tests). Ran Speednut `mas_extract.exe` under Wine on `Physics2.gtl`: PHS members are byte-identical to `mas_tool.py` extraction, so it does not decrypt them. Revised the "uniformly encrypted PHS" interpretation in docs.

## 2026-11-23 09:30:00 -0500 - Task 4: EA TGQ decoded via ffmpeg
- User identified `SCHl` as an Electronic Arts audio header; ffmpeg probes all 22 F1 2000 `.TGQ` files as TQI video (320x480, 25 fps) + `adpcm_ea` audio and decodes them. Added `media_tool.identify()` support, `tgq-decode` CLI and test; updated docs.

## 2026-11-23 09:00:00 -0500 - Docs: PHS keystream test
- Pairwise XOR of all 5 GTL PHS files retains ~7.99 bits/byte entropy (no shared keystream); no local tool or online source documents the format. PHS remains blocked.

## 2026-11-23 08:30:00 -0500 - Task 4: Bink-1 encoding via libbink
- `media_tool.bink_encode()` / `media_tool.py bink-encode` invoke the external LGPL-2.1 `raynorpat/libbink` `bink_build` tool. Built from source, encoded a decoded real GTR2 BIK: `--verify` passed, ffmpeg decoded the output, and the BIKi header layout matches. Encoding is no longer blocked. Add test and document.

## 2026-11-23 08:00:00 -0500 - Docs: Bink encoder search
- Checked online options for Bink-1 encoding: the announced LGPL `jmarshall23/libbink` repo returns 404; `marcussacana/Bink2` targets Bink 2, not GTR2's Bink 1. Encoding remains blocked without licensed tools.

## 2026-11-23 07:30:00 -0500 - Docs: bounded PHS/.tgq probe results
- Record negative results: PHS has no standard-compression stream (skip 0..64) and no repeating-key XOR signal (IC ~0.0039), and .tgq has no valid zlib stream or ASCII strings in the first 20 KB. Both remain blocked without an external spec.

## 2026-11-23 07:00:00 -0500 - Task 4: MTS records are shared rig tables
- `mts_format.rig_table_signature()` shows the 4.10 36-byte records are shared per rig (4 distinct tables across 22 files: pit crew, R_ARM/R_TGT, L_ARM, JET), revising the earlier "per-asset material ID" interpretation. Add test and document.

## 2026-11-23 06:30:00 -0500 - Task 4: GTTF frame grid decoded
- `simbin_events_tool.find_frame_grid()` / `read_frames()` decode 252-byte GTTF frame records (position + monotonic time); validated on 6 files against lap times. Add test, CLI flag and docs.

## 2026-11-23 06:00:00 -0500 - Task 4: Bink decode via ffmpeg
- `media_tool.bink_decode()` / `media_tool.py bink-decode` decode BIK to PNG via ffmpeg's binkvideo decoder (verified on real GTR2 files); add test and document. Encoding remains proprietary.

## 2026-11-23 05:30:00 -0500 - Task 4: GTR1 descriptor grid decoded
- `gmt_semantic.read_gtr1_descriptors()` decodes GTR1's 64-byte `(vcount,voff,icount,ioff)` grid at 0x194 (valid in 184/300 sampled files); add test and document.

## 2026-11-23 05:00:00 -0500 - Task 4: semantic GMT bridge
- `gmt_semantic.py` decodes both rF1 and GTR2 submeshes (positions, UVs, faces) via per-submesh headers; `gmt_layout.old_to_new_semantic()` rebuilds new-layout geometry preserving the material tail. Validated on 60 real rF1 GMTs (parse, decoded counts, lossless round-trip). Format knowledge from a GPLv3 reference importer, no code copied. Add tests and document.

## 2026-11-23 04:30:00 -0500 - Docs: GTR1 GMT layout scope note
- Record that the GTR1 (2004) GMT magic at 0x04 has no new-layout geometry table in the first 0x400 bytes and needs a dedicated parser; investigated but not pursued (reference corpus only).

## 2026-11-23 04:00:00 -0500 - Task 4: show bone id in FXM CLI
- `fxm_tool.py keys` now prints the decoded name-stable node id; update CLI test.

## 2026-11-23 03:30:00 -0500 - Task 4: new-layout stage-type map
- `gmt_format.build_stage_type_map()` mirrors the RaceGMT stage-type decoder for new-layout GMTs; validated per-format values (L0DIFFUSET0→1, L1BUMPSPECMAPT0→5, L1SPECULART0→4). Add test and document.

## 2026-11-23 03:00:00 -0500 - Task 4: GTR2-IRSR metadata decoded
- `simbin_events_tool.parse_gtr2_irsr_metadata()` decodes GTR2 replays (11-byte prefix, 5-byte field, team/driver Pascal names, car filename); validated 9/9 files. Added `EventFile.team` and CLI output; add test and document.

## 2026-11-23 02:30:00 -0500 - Task 4: rF1-IRSR metadata decoded
- `simbin_events_tool.parse_rf1_metadata()` decodes rFactor-era replays (mod/SCN/AIW strings, fixed 9-byte prefix, driver and vehicle names); validated 5/5 RF1Vanilla files. Branch added to `parse_payload` keyed on `.rfm`; add test and document.

## 2026-11-23 02:00:00 -0500 - Task 4: FXM key_count invariant
- Verify `key_count==3` in all 148 sampled node records (fixed field, distinct from the 2 decoded TRS keys); add corpus assertion and document as unconfirmed-meaning invariant.

## 2026-11-23 01:30:00 -0500 - Task 4: expose RaceGMT materials in CLI
- `race_gmt.py --materials` prints decoded material groups with per-stage type/channel; add CLI test.

## 2026-11-23 01:00:00 -0500 - Task 4: FXM node id decoded
- `fxm_tool.build_node_id_map()` proves size_hint == 84 + trailer (148/148 nodes in 91 files) and that the trailer is a name-stable bone id (all 27 node names have exactly one value). Add test and document.

## 2026-11-23 00:30:00 -0500 - Task 4: RaceGMT texture-channel field decoded
- `race_gmt.group_stages()` / `decode_stage_channels()` decode the u32 at +260 as a per-material texture-channel index; validated across 1,535 material groups (all 1,534 L2 stages use channel 0; L0/L1 in {0,1,3,4,5,6}). Add test and document.

## 2026-11-23 00:00:00 -0500 - Task 4: RaceGMT stage-type enum decoded
- `race_gmt.build_stage_type_map()` decodes the u32 at +256 as a stage-type enum (L0DIFFUSET0→1, L1DIFFUSET0→2, L2*→0, L0CMAPT0→3, L1BUMPSPECMAPT0→5, L1CMAPT0→7); 100% deterministic for 6 well-sampled RaceGMT stage names. Corrected an earlier contaminated probe that mixed in 54k new-layout GMTs; documented per-format type maps. Add test.

## 2026-11-22 23:15:00 -0500 - Task 4: GMT bridge ground-truth search (negative)
- Searched 552 same-name old/new GMT pairs (71 with matching vertex counts); inspected pairs are different meshes, so no vertex mapping can be derived. Documented as a negative result; GMT bridge still needs in-game validation.

## 2026-11-22 22:45:00 -0500 - Task 4: expose MTS decodes in CLI
- `mts_format.py --detail` prints decoded geometry table, submesh count, vertex/normal counts and material records; refresh stale module docstring. Add CLI test.

## 2026-11-22 22:15:00 -0500 - Task 4: GTTF/IRSR metadata framing decoded
- `simbin_events_tool.parse_metadata()` decodes driver/co-driver/car after the TRK/AIW names: GTTF 31/31 files (two Pascal names + car), GTL-IRSR 4/4 (one name + car); other IRSR variants left undecoded. Expose via `EventFile` fields and CLI; add tests and document.

## 2026-11-22 21:45:00 -0500 - Task 4: expose FXM keyframes in CLI
- Add `fxm_tool.py keys` subcommand printing decoded skeleton node TRS keyframes (position/quaternion/scale/norm); add CLI test.

## 2026-11-22 21:15:00 -0500 - Task 4: FXM TRS keyframes decoded
- `fxm_tool.decode_node_keys()` decodes the 84-byte keyframe block as 2 TRS keys (position/quaternion/scale) + 4-byte trailer; validated across all 27 nodes. Add test and document.

## 2026-11-22 20:45:00 -0500 - Task 4: FXM skeleton node table decoded
- `fxm_tool.parse_node_records()` walks the contiguous skeleton-node table anchored on `Bip01`; 27 clean records in FU_PreIdle4-R.FXM (name + 12-byte header + 84 keyframe bytes, stride name+96), replacing a loose regex that produced 3ds Max metadata false positives. Add tests and document. Keyframe float semantics remain unconfirmed.

## 2026-11-22 20:15:00 -0500 - Task 4: material IDs reference external table
- Verify decoded material IDs span 68 distinct values (313..442) with no contiguous table in the mesh file; document that exact semantics require an external material table not present in the corpus. Add negative-result test.

## 2026-11-22 19:45:00 -0500 - Task 4: no index block after normals
- Verify bytes following the validated normal block are float data, not u16 vertex indices; add test and document. Material IDs remain stable but semantically unresolved.

## 2026-11-22 19:15:00 -0500 - Task 4: MTS table fields corrected
- Tighten table validation (v[1]>=0x100, ordered offsets) preserving 200/200 coverage; verify last table u32 is the end of the normal block, not a u16 index array. `read_geometry()` no longer emits bogus indices. Add tests and document.

## 2026-11-22 18:45:00 -0500 - Task 4: CUBE MTS geometry blocks decoded
- `mts_format.read_geometry()` follows validated table offsets; vertex stride 36 bytes and normal stride 16 bytes confirmed in 200/200 sampled files (LIGHTBOX02: 118 vertices / 97 normals). Add tests and document.

## 2026-11-22 18:15:00 -0500 - Task 4: material numbers stable across files
- Verify decoded material numbers are identical for all 79 records of TIREMANFRONT.MTS vs TIREMANBACK.MTS; add test and document as likely asset-level IDs.

## 2026-11-22 17:45:00 -0500 - Task 4: material numeric field decoding
- `mts_format.decode_material_numbers()` splits the 4.10 material packed u32 into two u16 fields; validated across 1,227 records (all <1024). Semantics still unconfirmed; documented.

## 2026-11-22 17:15:00 -0500 - Task 4: alternate CUBE MTS submesh records
- Decode type-B submesh record `(count_a, 0, count_b, offset_b, count_c, offset_c, 0, 0)` at table+48; submesh coverage rises to 198/200 (4.20) and 200/200 (4.10). Add test and document.

## 2026-11-22 16:45:00 -0500 - Task 4: full MTS table header coverage
- `parse_mesh_table()` now returns validated count/offset headers even when submesh records use a different layout; header coverage 200/200 per variant, submesh records 120/200 (4.20) and 74/200 (4.10). Add tests and document.

## 2026-11-22 16:15:00 -0500 - Task 4: CUBE MTS 4.10 material records
- `mts_format.parse_material_records()` resolves 36-byte records marked 128+index with 1.0f field; validated on TIREMANFRONT.MTS and documented.

## 2026-11-22 15:45:00 -0500 - Task 4: RaceGMT stage numeric fields
- `race_gmt.read_material_blocks()` resolves 264-byte stage records; u32 tail at +256 correlates with stage prefix (L0/L1/L2). Add test and document.

## 2026-11-22 15:15:00 -0500 - Task 4: RaceGMT material groups
- Validate material/stage grouping: PEOPLE_STAND_01 has 20 strings = 5 groups of (material + L0/L1/L2 stage names). Add `race_gmt.read_material_strings()` + test.

## 2026-11-22 14:45:00 -0500 - Task 4: RaceGMT interpretation corrected
- Withdraw "triangle soup" claim: 36-byte grid contains mixed data; ASCII material/stage strings found in all 643 RaceGMT files (e.g. L0DIFFUSET0, PESSOAS_E at 0x30AF). Add test; mark `race_gmt.read_positions()` experimental.

## 2026-11-22 14:15:00 -0500 - Task 4: MTS table coverage for 4.10
- Submesh marker differs by version (129 in 4.20, 130 in 4.10); extend `mts_format.parse_mesh_table()` and add corpus test (74/200 sampled 4.10 files parse).

## 2026-11-22 13:45:00 -0500 - Task 4: CUBE MTS geometry table resolved
- Find real CUBE MTS submesh table: 8-u32 count/offset header + 64-byte-spaced submesh records with marker 129. `LIGHTBOX02.MTS` at 0x500 resolves 5 submeshes and valid vertex/normal offsets; 129/300 sampled 4.20 files parse.
- Add `mts_format.parse_mesh_table()` + exact/corpus tests; document in `docs/binary-formats.md`, `CAPABILITIES.md`.

## 2026-11-22 13:15:00 -0500 - Task 4: descriptor tail states
- Enumerate three dominant states of descriptor+164 u32 (0, 0x0B4CE680, 0xFFFFFFFF) across 2,001 descriptors; add `mts_format.descriptor_tail_u32()` + test.

## 2026-11-22 12:45:00 -0500 - Task 4: descriptor packed field decoded
- Descriptor+32 u32 is a packed field: high16 0x4890/0x2890, low16 small values; add `mts_format.descriptor_fields()` + distribution test.
- Pair diffs at +32/+164 did not resolve into vertex/index offsets; documented as unresolved.

## 2026-11-22 12:15:00 -0500 - Task 4: CUBE MTS descriptor grid
- Locate submesh names as anchors: in LIGHTBOX02.MTS names sit at 216/412/608/804 (196-byte stride); dominant spacing in 206/300 sampled files.
- Add `mts_format.submesh_descriptors()` + test; document in `docs/binary-formats.md`.

## 2026-11-22 11:45:00 -0500 - Task 4: MTS float-run hypothesis rejected
- A long plausible-float run in TLRA.MTS was tested and rejected as a normal array (140/814 unit-length triples); add negative-result test and document.

## 2026-11-22 11:15:00 -0500 - Task 4: CUBE MTS 48-byte grid weakened
- Full-payload tracing on the largest same-size pair showed only ~23% of differing bytes align to offsets 36/44 of a 48-byte grid; field values are mixed integer/float. Recorded as a negative-result test and documentation correction.

## 2026-11-22 10:45:00 -0500 - Task 4: RaceGMT triangle soup
- Verify PEOPLE_STAND_01 has 552 triangles / 1,656 vertex slots but only 722 unique positions — shared-vertex triangle soup, no separate index buffer found. Add test and document.

## 2026-11-22 10:15:00 -0500 - GMT family variant detection
- `gmt_tool.detect_variant()` recognises new GTR2/GTL, old rF1, GTR 2004, JCA-encrypted and RaceGMT headers; add `tests/test_gmt_variants.py` with real-corpus samples.

## 2026-11-22 09:45:00 -0500 - Task 4: MTS name correlation confirmed in both variants
- Extend `object_count - submesh_names == 1` test to CUBE MTS 4.10 (130/200 sampled) as well as 4.20; document.

## 2026-11-22 09:15:00 -0500 - Task 4: MTS vertex-triple hypothesis rejected
- Field-level diff across 40 same-size CUBE MTS 4.20 pairs showed all 12 float slots vary, with values >1e5 in sampled records — 48-byte blocks are not simple position triples.
- Add negative-result test and document in `docs/binary-formats.md`.

## 2026-11-22 08:45:00 -0500 - Task 4: CUBE MTS submesh count correlation
- Extract uppercase submesh names from CUBE MTS 4.20 payloads; `object_count - len(names) == 1` in 644/800 sampled files (observed correlation, not proven).
- Add `mts_format.submesh_names()` and test; document in `docs/binary-formats.md`.

## 2026-11-22 08:15:00 -0500 - Task 4: record grid refinements
- Correct earlier 64-byte-section claim: RaceGMT differences all lie on the 36-byte position grid; 64-byte gaps were alternating records.
- Verify CUBE MTS 4.20 differing fields cluster at offsets 36/44 of 48-byte records; add test.

## 2026-11-22 07:45:00 -0500 - Task 4: RaceGMT positions decoded
- Verify 36-byte records are 3×(x,y,z) position triples; `race_gmt.read_positions()` reads 552 records from PEOPLE_STAND_01.
- Document in `docs/binary-formats.md`, `CAPABILITIES.md`; add test.

## 2026-11-22 07:15:00 -0500 - Task 4: record strides found
- Same-size file diffs reveal `RaceGMT\0` record strides of 36 bytes (positions) and 64 bytes (transforms); add `race_gmt.diff_strides()` + test.
- CUBE MTS 4.20 same-size diffs show a dominant 48-byte record stride; add test.
- Document in `docs/binary-formats.md`, `CAPABILITIES.md`.

## 2026-11-22 06:45:00 -0500 - Task 4: partial mesh variant decode
- Verify CUBE MTS 4.10/4.20 share `magic[16] + u32 count + name[8]` header across 4,200+ meshes; add `mts_format.py`.
- Verify `RaceGMT\0` header (name length/name/flags/bounding box) across 643 files; add `race_gmt.py`.
- Cross-comparison found no same-asset pairs, so geometry tables remain undecoded (documented honestly).

## 2026-11-22 06:15:00 -0500 - Status update
- Update `docs/task-plan.md` verification count to 181 tests.

## 2026-11-22 05:45:00 -0500 - Ranked tasks: pipeline text rules, diff harness, diagnostics, CI
- `text_convert.py`: SCN→TRK rewrites + tree-level rF1→GTR2 conversion (AIW, archives, copies).
- `corpus_diff.py`: same-name corpus comparison with optional MAS-member indexing.
- `validate_materials.py`: SimBin material-prefix diagnostic.
- GitHub Actions workflow + installable `hooks/pre-push` running `pre_push_check.py`.
- Task 4 (RaceGMT/CUBE_MTS_4.20 internals) remains blocked: no mesh table found in sampled `RaceGMT\0` files.

## 2026-11-22 05:15:00 -0500 - GTR 2004 corpus added and reviewed
- Add `../GTR1Vanilla/` (previously missing target-format corpus): 430 MAS type-0 archives.
- Identify third GMT magic `c8cfd2d8ced8e6c3d6ded8bdbba6bf90` at 0x04 (33,477 files) plus 3 `OR_GMT_1.00` oddities; not parsed by `gmt_format.py`.
- Add `tests/test_gtr1_vanilla.py`; document in `AGENTS.md`, `docs/binary-formats.md`, `CAPABILITIES.md`.

## 2026-11-22 05:00:00 -0500 - Status check
- Update `docs/task-plan.md` verification count to 173 tests.

## 2026-11-22 04:45:00 -0500 - Document old-tmp-files as legacy scratch
- Add `../old-tmp-files/` to `AGENTS.md` as prior-attempt scratch (same caveats as `legacy/`), explicitly not ruled out as a future lead.
- Note the `gMa1.002f` AIW fixture and GMT/UV probes in `docs/reuse-rfactortools.md` for possible later reuse.

## 2026-11-22 04:30:00 -0500 - gtr2-tools and Speednuts extractor reviewed
- Add `../gtr2-tools/` and `../Speednuts_mas_extract/` as reference-only locations in `AGENTS.md`.
- Mine `AIW Repair Utility v1.0` readme/INI: rFactor→SimBin AIW rules (scale `wp_galpha` 1.0→0.45, delete 12 rFactor-only tags, replace `wp_cheat` with `wp_event=(1.000,0,0)`).
- Implement `simbin_text_tool.aiw_for_simbin()` + CLI `aiw-convert`, with `tests/test_aiw_convert.py`.
- Document in `docs/reuse-rfactortools.md`, `CAPABILITIES.md`, `FEATURES.md`, `README.md`.

## 2026-11-22 04:00:00 -0500 - Licence and pre-push safety checks
- README now states CC BY-NC 4.0 licensing.
- Add `pre_push_check.py`: scans for secrets, PII (home paths/emails, allowlisting `shovas` + noreply email), credentials in remote URLs, oversized/game-data files, untracked files and commit identity mismatches.
- Sanitise the personal home path in `AGENTS.md`; ignore editor swap files in `.gitignore`.
- Add `tests/test_pre_push_check.py`; document in README/AGENTS/FEATURES.

## 2026-11-22 03:30:00 -0500 - Documentation refresh
- README: add agent-driven/AI-generated notice near top, documentation map of all MD files, remove Status section, reframe usage around agent requests.
- Update CAPABILITIES.md, FEATURES.md, DEPENDENCIES.md, AGENTS.md and all `docs/*.md` to match current tools and findings (JCA, layout bridge, prototype pipeline, new corpora, PHS TODO, 166-test verification).

## 2026-11-22 03:00:00 -0500 - Race07Complete corpus reviewed
- Add `../Race07Complete/` (Race 07 + WTCC/STCC/Race On/GTR Evolution DLC, 12G).
- Identify three GMT variants among 66,186 loose files: JCA-encrypted, standard new-layout, and new `RaceGMT\0` header (643 files, header only decoded).
- Verify JCA decryption to standard layout and JCA-encrypted `.gdb/.trk/.scn/.cam`.
- Add `tests/test_race07_complete.py`; document in `AGENTS.md`, `docs/binary-formats.md`.

## 2026-11-22 02:30:00 -0500 - Three more corpora reviewed
- `F1CS2000/`: byte-identical copy of F12000 (570 files), no new formats.
- `GameStockCar/`: 48 MAS type-1 archives (19,995 members), GSC encryption, old-layout GMTs.
- `NascarSimRacing/`: 311 MAS type-3 archives, 26,473 CUBE MTS meshes with new `CUBE_MTS_4.20` magic (25,689 vs 784 `4.10`).
- Add `tests/test_three_corpora.py`; document in `AGENTS.md`, `docs/binary-formats.md`.

## 2026-11-22 02:00:00 -0500 - Wave 2: rF1 pipeline + GTTF/IRSR reader
- Add `rf1_to_gtr2.py`: unpack → ISI decrypt → GMT layout bridge → type-0 repack → validation; verified on a 253-GMT archive.
- Add `simbin_events_tool.py`: GTTF/IRSR magic, version, TRK/AIW filenames, embedded strings across 29 GTT + 9 VCR files.
- Add `tests/test_rf1_pipeline.py`, `tests/test_simbin_events_tool.py`; document in README/CAPABILITIES/binary-formats.

## 2026-11-22 01:30:00 -0500 - Wave 1: text tools, cross-corpus tests, GMT layout bridge
- Add `simbin_text_tool.py` (AIW waypoints/features, SCN/TRK SearchPath/MASFile/SkyBoxI) + tests on real GTR2/GTL files.
- Add `tests/test_carryover.py`: 57 identical GTL/GTR2 GMTs parse and repack.
- Add `tests/test_fxm_crosscorpus.py`: 567 FXM-family files, 54 extension/magic mismatches.
- Cross-check JCA against `Race07Decryptor.exe` via `monodis` IL (confirms magic, header offsets, LE blocks, XOR 0xEB, custom keys, inflate workaround).
- Add `gmt_layout.py` prototype: structural old→new GMT bridge; 6 sampled rF1 GMTs convert to parseable new-layout files. Geometry semantics explicitly unvalidated.

## 2026-11-22 01:00:00 -0500 - Task plan Wave 0: mining + fixtures
- Add `docs/reuse-rfactortools.md`: ready-made parsers and full conversion pipeline in `../rfactortools`; RacerM/GTL2GTR2 tutorial conversion rules (material prefixes, SCN→TRK rewrites, SkyBoxI, DDS-only).
- Add `tests/test_fixtures.py`: 57 identical same-name Anderstorp GMTs, new-layout rF1 GMTs, 5 PHS + DETOMASO edge cases.
- Loose-extension survey documented; verify JCA also encrypts Race07/Volvo `.gdb/.trk/.scn/.cam` (added tests).
- Document missing GTR (2004) corpus and 6 untested ISI signatures as coverage gaps.

## 2026-11-22 00:30:00 -0500 - F1 2001: MAS type-6 support
- Add `../F12001/` as ancestral ISIMotor reference.
- Extend `mas_tool.py` with MAS type 6 (`CUBEMAS4.00`/`CUBEMAS4.01`): 16-byte header + 256-byte records (type/offset/size/zsize/crc/name[236]); reads/writes all 80 archives (16,720 members) with signature preservation. Add `--type 6`.
- Add `tests/test_f12001.py`; document in `AGENTS.md`, `docs/binary-formats.md`, `CAPABILITIES.md`.

## 2026-11-22 00:15:00 -0500 - NASCAR Thunder 2003 corpus added and reviewed
- Add `../NT2003/` as ancestral ISIMotor reference.
- Add `tests/test_nt2003.py`: 179 MAS type-3 archives (19,006 members, 10,397 CUBE MTS meshes), 476 `.hdr`/`.dat` audio pairs, `.veh/.hdv` text, no ISI encryption.
- Document in `AGENTS.md`, `docs/binary-formats.md`.

## 2026-11-22 00:00:00 -0500 - F1 2000: MAS type-2.5 support
- Add `../F12000/` as ancestral ISIMotor reference.
- Extend `mas_tool.py` with MAS type 5 (`CUBEMAS2.50`): 12-byte magic + 256-byte records; reads/writes all 118 archives (30,909 members), decoding plain-zlib and 16-byte-header+zlib members and preserving 319 undecoded ones losslessly. Add `--type 5`.
- Add `tests/test_f12000.py`; document in `AGENTS.md`, `docs/binary-formats.md`, `CAPABILITIES.md`.

## 2026-11-21 23:40:00 -0500 - Remaining new folders reviewed (ascending size)
- `Race07Decryptor/` (65M): .NET 8 win-x64 third-party decryptor, reference only; native `jca_crypt.py` supersedes it.
- `VolvoTheGame/` (504M): 2,026 JCA GMTs need the non-default `volvo` key; decrypt to standard GTR2 GMTs; plain FXM/FXA/LMA.
- `NT2004/` (632M): 136 MAS type-3 archives, 14,250 standard CUBE MTS meshes, `.hdr` audio headers, `.skn` text, `.djs` MP3.
- Add `tests/test_volvo.py`, `tests/test_nt2004.py`; document in `AGENTS.md`, `docs/binary-formats.md`.

## 2026-11-21 23:25:00 -0500 - Native JCA decryption/encryption added
- Add `jca_crypt.py` + GPLv2-attributed `jca_tables.py`: pure-Python Blowfish JCA decrypt/encrypt for all 8 versions and custom game keys.
- Verified byte-for-byte against `wtcced` on real Race 07 GMTs; 200 sampled files decrypt into standard GTR2-layout GMTs parseable by `gmt_format.py`.
- Add `tests/test_jca_crypt.py` (5 tests); document licensing in CAPABILITIES.md.

## 2026-11-21 23:10:00 -0500 - Race 07 opaque GMTs identified as JCA encryption
- Identified the `0fb1ffff` header as SimBin JCA encryption (`raceroom.bms` recognizes it but only points to external `wtcced`).
- Verified real Race 07 GMTs decrypt with GPLv2 `wtcced` (compiled from source with 64-bit type fixes) into standard GTR2-layout GMTs that parse and round-trip with `gmt_format.py`.
- Add optional external-tool cross-check test and JCA header-field test in `tests/test_race07.py`; document procedure and GPLv2 licensing caveat.

## 2026-11-21 22:50:00 -0500 - Race 07 corpus: opaque loose GMTs documented
- Add `../Race07Vanilla/` as SimBin sibling reference.
- Add `tests/test_race07.py`: 2 MAS type-0 archives (5 standard-layout GMTs in `crew.gtr`), 21,687 loose GMTs with opaque `0fb1ffff03000000` header (undecoded), FXM-family extension/magic mismatches.
- Document in `docs/binary-formats.md`.

## 2026-11-21 22:35:00 -0500 - Stock Car Extreme corpus added and reviewed
- Add `../StockCarExtreme/` as GSC-lineage source reference.
- Add `tests/test_stockcar_extreme.py`: 196 MAS type-1 archives, GSC-signature decryption, sampled old-layout GMTs.
- Document in `docs/binary-formats.md`.
- Note: path references updated for the `SportsCarGtUsa` folder rename (separate commit).

## 2026-11-21 22:15:00 -0500 - F1 Challenge 99-02 corpus added and reviewed
- Add `../F1C/` as ancestral ISIMotor reference (direct rFactor predecessor).
- Add `tests/test_f1c.py`: 197 type-3 archives (21,977 members), 13,769 standard CUBE MTS meshes + 1,065 variants, no ISI encryption; member round-trip verified.

## 2026-11-21 22:00:00 -0500 - F1 2002 corpus: MAS type-3 write fix
- Add `../F12002/` as ancestral ISIMotor reference.
- Fix latent `struct.pack` bug in `mas_tool.write_archive()` for type 3; all 63 archives now round-trip at member level.
- Add `tests/test_f12002.py`: 63 type-3 archives (19,235 members), 12,640 standard CUBE_MTS_4.10 meshes + 460 header-variant meshes, no ISI encryption.

## 2026-11-21 21:40:00 -0500 - Automobilista corpus added and reviewed
- Add `../Automobilista/` as late ISIMotor source reference.
- Add `tests/test_ams.py`: 470 MAS type-1 archives; GSC-signature decryption cross-checked against `rfactordec`; sampled GMTs all use old-style (0x1D4/0xA8) layout.
- Document in `docs/binary-formats.md`.

## 2026-11-21 21:20:00 -0500 - Sports Car GT: MAS type-2 support
- Add `../SportsCarGtUsa/` as ancestral ISIMotor reference.
- Extend `mas_tool.py` with signature-less MAS type-2 (8-byte header + 32-byte records): read/write all 61 archives; decode the 16-byte-header + zlib texture variant; preserve 22 undecoded-compression members losslessly. Add `--type 2` to `create`.
- Add `tests/test_scgt.py` (4 tests) and document findings in `docs/binary-formats.md`, `CAPABILITIES.md`.

## 2026-11-21 21:00:00 -0500 - Copa Petrobras de Marcas: MAS type-1X + GSC encryption
- Add `../CopaPetrobrasdeMarcas/` as workspace-root reference.
- Extend `mas_tool.py` with the documented MAS type-1X (Petrobras) signature variant: `read_archive()` recognizes it as type 1, `read_signature()` and `write_archive(signature=...)` preserve it across add/update/delete; `--signature` option on `create`.
- Add `tests/test_mas_tool.py` cases verifying all 50 Copa archives read and signature-preserving member round-trip.
- Add `tests/test_copa.py`: enctype-1 decryption cross-checked against `rfactordec`; all 12,990 GMTs are GSC-signature encrypted with old-style (0x1D4/0xA8) magic.

## 2026-11-21 20:45:00 -0500 - RF1Vanilla corpus: rF1 encryption + GMT layouts
- Add `../RF1Vanilla/` as workspace-root reference (AGENTS.md).
- Add `tests/test_rf1_vanilla.py`: 85 MAS type-1 archives; 9,662 GMTs split 9,630 old-layout (magic at 0x1D4, byte 0xA8) / 32 GTR2-style (0x08, 0xA7); 120 ISI-encrypted GMTs decrypt with skip=4 (90 old + 30 new), cross-checked against `rfactordec`.
- All 32 GTR2-style GMTs parse and round-trip with `gmt_format.py`.
- Document in `docs/gmt-format.md`, `docs/binary-formats.md`.

## 2026-11-21 20:30:00 -0500 - BMW corpus folder rename
- Update path references for workspace-root folder rename `BMW M3 Challenge` -> `BMWM3Challenge` (AGENTS.md, tests, docs).

## 2026-11-21 20:25:00 -0500 - BMW M3 Challenge corpus added and reviewed
- Add `../BMWM3Challenge/` as workspace-root reference (AGENTS.md).
- Add `tests/test_bmw_m3.py`: 17 `.bmw` archives are GMOTORMAS10 type 0 with lossless member round-trip; 976 GMTs all have normal magic; 75 FXM-family files use known magics with 5 extension/magic mismatches.
- Document findings in `docs/binary-formats.md` and `CAPABILITIES.md`.

## 2026-11-21 19:45:00 -0500 - FXM/LMA observed node-name evidence
- Add verifiable assertions for observed node-name strings in `ExtDriver_A.LMA` (lossless round-trip unchanged).

## 2026-11-21 20:05:00 -0500 - JPG/MP3 metadata parsing
- Parse JPG SOF dimensions/bit depth and MP3 frame header metadata in `media_tool.py`.
- Add real-file JPG/MP3 metadata tests.

## 2026-11-22 04:05:00 -0500 - Encryption surface audit
- Document audit result: 0 files in GTR2/GTL installs carry known ISI 16-byte-header signatures; 5 PHS files remain high-entropy/undecrypted with no known ISI signature and no entropy reduction under ISI enctype 0/1.

## 2026-11-22 03:55:00 -0500 - DSI real-file observation test
- Add real-file DSI gzip/SimBin header observation test (all 142 DSI files match gMb1.000f header).

## 2026-11-22 03:45:00 -0500 - MAS GMT magic coverage observation
- Add observed scan test: 26,930/26,931 MAS GMTs have normal magic; only DETOMASO_PANTERA_RAINSCREEN.GMT has non-normal magic.

## 2026-11-22 03:35:00 -0500 - MP3 header observation
- Add observed scan test: 23/24 GTR2/GTL MP3s start with ID3 or MPEG frame sync; 1 known null-padded file.

## 2026-11-22 03:25:00 -0500 - JPG SOF observation
- Add observed scan test: all 93 GTR2/GTL JPGs are baseline SOF0, 8-bit, 3 components.

## 2026-11-22 03:15:00 -0500 - GMT material header invariant refinement
- Extend observed L0-heuristic material header invariants: u32[6..15]==0, [20..23]==1.0f, [28]==1.0f (in addition to [32]==1.0f, [36]==0).

## 2026-11-22 03:05:00 -0500 - BIK magic observation
- Add observed scan test: all 137 GTR2/GTL `.bik` files start with `BIKi`.

## 2026-11-22 02:55:00 -0500 - GMT extra-vertex observation
- Add observed scan test: extra 16-byte vertex raw_u32 == [0, 0xFFFFFFFF, 0, 0] in 11 meshes/2918 verts.

## 2026-11-22 02:45:00 -0500 - GMT stage-3 texture string observation
- Add observed scan test: texture-like strings (.dds/.tga/.bmp) in GMT material stage blocks appear in stage 3 only in scanned samples.

## 2026-11-22 02:35:00 -0500 - BMP format observation
- Add observed scan test: GTR2/GTL BMP files/MAS entries use BI_RGB bpp 8/24/32 in scanned samples.

## 2026-11-22 02:25:00 -0500 - TGA type observation
- Add observed scan test: GTR2/GTL TGA files/MAS entries use image types 2 and 10 only in scanned samples.

## 2026-11-22 02:15:00 -0500 - AIW header observation
- Add observed AIW header/section test: all scanned GTR2/GTL `.aiw` files start with `//[[gMa1.000` and contain `[Features]`.

## 2026-11-22 02:05:00 -0500 - WAV format observation
- Add observed scan test: GTR2/GTL WAV files are PCM (1) or MP3 (0x55) only in scanned installs.

## 2026-11-22 01:55:00 -0500 - DDS MAS pixel-format observation
- Add observed scan test: MAS DDS headers contain only DXT1/DXT3/DXT5 and uncompressed RGB(A) (pf 0x41/0x40) in scanned samples.

## 2026-11-22 01:45:00 -0500 - GMT header name field observation
- Add observed scan test: 0x194..0x1D4 is 64-byte null-terminated ASCII object/name string.

## 2026-11-22 01:35:00 -0500 - GMT mesh table first_record observation
- Add observed scan test: normal-magic GMT mesh table `first_record` is 528 (0x210) in scanned samples.

## 2026-11-22 01:25:00 -0500 - GMT header flags observed mask
- Add observed scan test: normal-magic GMT file flags at offset 4 use only bits in 0x06000020.

## 2026-11-22 01:15:00 -0500 - FXM offset-30 header refinement
- Add observed offset-30 FXA/FXM/LMA invariants: BE u16[1]==257, BE u32[4]==256.

## 2026-11-22 01:05:00 -0500 - FXM offset-19 header refinement
- Refine observed offset-19 FXA/FXM/LMA header: BE u32[3] in {80,184}, BE u32[4]==1.

## 2026-11-22 00:55:00 -0500 - FXM offset-19 header observations
- Add observed scan test: offset-19 FXA/FXM/LMA files have BE u16[1]==257, BE u32[2] in {1,256}, BE u32[5] in {65,66,67,77}.

## 2026-11-22 00:45:00 -0500 - GMT mesh rec[24..26] pattern observations
- Refine observed scan: rec[24..26] only three patterns in 50,054 meshes: (0xFFFFFFFF,0,0), (0,0xFFFFFFFF,0), (0xFFFFFFFF,0,1098907648==18.0f).

## 2026-11-22 00:35:00 -0500 - GMT mesh record field observations
- Add observed scan test: rec[0,9,12-23]==0, rec[24] in {0,0xFFFFFFFF}, material index in bounds in scanned GTR2/GTL samples.

## 2026-11-22 00:25:00 -0500 - GMT index bounds/topology observation
- Add observed scan test: GMT mesh index refs within vertex_count; index_count not always multiple of 3.

## 2026-11-22 00:15:00 -0500 - PHS binary format identified
- Identify 5 GTL `.phs` files in MAS archives as unknown/non-ISI-16byte-header binary; add observation test and docs.

## 2026-11-22 00:05:00 -0500 - GTTF/VCR header field observation
- Add observed GTTF/IRSR header field test (magic, f32 version, TRK/AIW length-prefixed strings).

## 2026-11-21 23:55:00 -0500 - VCR gzip container support
- Recognize VCR as gzip-wrapped SimBin IRSR replay payload; content round-trip via `gzip_simbin_tool.py`.
- Add real-file VCR decompress test.

## 2026-11-21 23:45:00 -0500 - GTT gzip container support
- Recognize GTT as gzip-wrapped SimBin GTTF payload; content round-trip via `gzip_simbin_tool.py`.
- Add real-file GTT decompress/identify test.

## 2026-11-21 23:35:00 -0500 - DDS mipmap identification test
- Add real-file DDS mipmap identification test (reports mipmaps>1).

## 2026-11-21 23:25:00 -0500 - FXM offset-30 source path observation
- Add observed test: most offset-30 FXA/FXM/LMA files contain a source path string within 300 bytes after first string.

## 2026-11-21 23:15:00 -0500 - GMT mesh flag bit observations
- Add observed scan tests: rec[1] bit 0x1/0x4000 always set, bit 0x2 correlates with 48-byte extra vertex block.

## 2026-11-21 23:05:00 -0500 - FXM offset-30 family signature observation
- Add observed scan test: offset-30 FXA/FXM/LMA files have BE[2]==4096, BE[5]==528, first string contains "3D Studio Max".

## 2026-11-21 22:55:00 -0500 - GMT mesh flag bit 0x20 stream2/3 correlation
- Add observed scan test: mesh rec[1] bit 0x20 correlates with stream2/3 presence in scanned GTR2/GTL samples.

## 2026-11-21 22:45:00 -0500 - GMT vertex base f0 observed distribution
- Add observed test: base vertex f0 is zero in vast majority of scanned samples; f7 varies. Semantics unconfirmed.

## 2026-11-21 22:35:00 -0500 - GMT mesh record invariants observed
- Add observed scan test: mesh rec[0]==0 and vertex stride 32/48 in scanned GTR2/GTL samples.

## 2026-11-21 22:25:00 -0500 - GMT stream2/stream3 stride observation
- Add observed test: when present, GMT mesh stream2/3 are 32 bytes/vertex (semantics unconfirmed).

## 2026-11-21 22:15:00 -0500 - WAV MP3-in-WAV lossless handling
- Parse fmt chunk metadata when stdlib `wave` cannot read (e.g. format 0x55 MP3-in-WAV); fall back to lossless byte-copy round-trip.
- Add real-file MP3-in-WAV lossless round-trip test.

## 2026-11-21 22:05:00 -0500 - GMT stage-3 observed param fields
- Add observed stage-3 u32 offset 24/92 distribution test; semantics unconfirmed.

## 2026-11-21 21:55:00 -0500 - GMT common stage shader names observed
- Add observed common stage 0-2 shader name catalog/test for L0-heuristic materials; note stage-3 offset-24 does not cleanly correlate with slot count.

## 2026-11-21 21:45:00 -0500 - GMT stage-3 texture slot pattern observation
- Add observed test for stage-3 texture slot patterns (28,200)/(28,) across L0-heuristic materials.

## 2026-11-21 21:35:00 -0500 - GMT stage-3 texture offset observation
- Add observed test: stage-3 texture strings commonly at offsets 28 and 200 within 264-byte stage block.

## 2026-11-21 21:25:00 -0500 - GMT texture filename stage location observed
- Add observed invariant test: texture filename strings (.DDS/.TGA/.BMP) appear in GMT stage block 3 for sampled L0-heuristic materials.

## 2026-11-21 21:15:00 -0500 - FXM/LMA node prefix correlation
- Add observed 12-byte Bip01 node prefix correlation test in GTR2 LMAs (LE u32 prefix: third==1, second==BE header u32@8; semantics unconfirmed).

## 2026-11-21 21:05:00 -0500 - FXM/LMA layout families observed
- Add `first_string_offset` reporting and observed layout-family test: offset 19 (LMA driver/bone names) vs 30 (FXA/FXM pit/source string).

## 2026-11-21 20:55:00 -0500 - FXM/LMA node extraction and GMT header invariants
- Add heuristic node/bone name extraction to `fxm_tool.py` (`nodes` command, `extract_strings`).
- Add observed GMT material header invariants for L0-heuristic materials (u32[32]==1.0f, u32[36]==0) with scan test.
- Document FXM/LMA header overlap caution and LMA magic observation.

## 2026-11-21 20:45:00 -0500 - GMT stage tail u32 observed fields
- Expose `GmtStage.tail_u32_64/65` (stage byte offsets 256,260) with large-sample name correlation documented as semantics-unconfirmed.

## 2026-11-21 20:35:00 -0500 - GMT material header/stage observed fields
- Expose `GmtMaterial.header_raw` (152 bytes) and add observed numeric field assertions for BUMPER_A material header/stage trailing params (semantics unconfirmed, lossless round-trip preserved).

## 2026-11-21 20:25:00 -0500 - DDS R5G6B5 round-trip test
- Add synthetic R5G6B5 uncompressed DDS round-trip test.

## 2026-11-21 20:15:00 -0500 - DDS 24-bit RGB round-trip test
- Add synthetic R8G8B8 uncompressed DDS round-trip test (mask-based path).

## 2026-11-21 19:55:00 -0500 - DDS uncompressed RGB(A) mask-based support
- Accept uncompressed RGB DDS with DDPF_RGB (with/without alpha) and preserve header masks on write.
- Add X8R8G8B8 synthetic round-trip test.

## 2026-11-21 19:45:00 -0500 - DDS uncompressed A8R8G8B8 decode/encode
- Add uncompressed A8R8G8B8 DDS decode/encode in `media_tool.py`.
- Add synthetic uncompressed DDS round-trip test.

## 2026-11-21 19:35:00 -0500 - DDS DXT3 (BC2) decode/encode
- Add DXT3 (BC2) decode/encode and DDS read/write support in `media_tool.py`.
- Add synthetic DXT3 round-trip test.

## 2026-11-21 19:25:00 -0500 - DDS DXT5 (BC3) decode/encode
- Add DXT5 (BC3) decode/encode and DDS read/write support in `media_tool.py`.
- Add synthetic DXT5 round-trip test.

## 2026-11-21 19:15:00 -0500 - DDS DXT1 (BC1) decode/encode
- Add DXT1 (BC1) decode/encode and DDS read/write in `media_tool.py` (lossy simple encoder).
- Add synthetic DXT1 round-trip test.

## 2026-11-21 19:05:00 -0500 - BMP semantic read/write (BI_RGB 24/32)
- Add semantic BMP read/write for uncompressed BI_RGB 24/32-bit in `media_tool.py`.
- Fix BMP header identification unpack bug.
- Add BMP round-trip test.

## 2026-11-21 18:55:00 -0500 - TGA semantic read/write (type 2/3/10)
- Add TGA semantic read/write in `media_tool.py` for type 2/3 uncompressed and type 10 RLE (pixel-identical round-trip; type 2/3 byte-identical).
- Add synthetic and real-file TGA round-trip tests.

## 2026-11-21 18:45:00 -0500 - DDS header semantic field parsing
- Parse DDS header/pixel-format/caps fields in `media_tool.py`; extend DDS identification test.

## 2026-11-21 18:35:00 -0500 - DETOMASO rainscreen GMT header-repair evidence
- Investigated `DETOMASO_PANTERA_RAINSCREEN.GMT`: not standard ISI 16-byte-header encryption; mangled magic/flags, `mesh_count=0`, contains `RAIN_ANIM` strings.
- Added test showing header repair (normal magic/flags) yields structurally parseable, lossless-round-trippable GMT; semantic correctness unverified.

## 2026-11-21 18:25:00 -0500 - FXM/LMA header BE field observation
- Report BE-interpreted FXM/FXA/LMA header fields in `fxm_tool.py` (observed plausible; semantics unconfirmed).
- Add LMA BE-field assertion in tests.

## 2026-11-21 18:15:00 -0500 - Media identification and WAV semantic round-trip
- Add `media_tool.py`: identifies WAV/DDS/TGA/BMP/JPG/MP3/BIK, parses basic headers, detects BMP-as-TGA quirk, and performs semantic WAV PCM round-trip via stdlib `wave`.
- Add media tool tests.

## 2026-11-21 18:05:00 -0500 - FXM/FXA/LMA magic coverage
- Recognize `LMA ` magic in `fxm_tool.py` (in addition to `FXM `/`FXA `); extension may not match magic.
- Add real LMA header/round-trip test.

## 2026-11-21 17:52:00 -0500 - GMT 48-stride extra vertex decode view
- Decode 48-stride 16-byte extra vertex blocks into `GmtVertexExtra(raw_u32, raw_f32)` while preserving lossless raw round-trip.
- Add assertions in GMT format tests.

## 2026-11-21 17:45:00 -0500 - ISI decrypt/encrypt and end-user docs
- Add pure-Python ISI/rFactor 16-byte-header decrypt/encrypt tool (`isi_crypt.py`) with GMT skip=4 support; verified by round-trip tests and optional cross-check against `rfactordec`.
- Add end-user docs: `README.md`, `FEATURES.md`, `CAPABILITIES.md`, `DEPENDENCIES.md`, `CHANGES.md`.
- Document remaining encrypted-GMT gap: `DETOMASO_PANTERA_RAINSCREEN.GMT` has unknown/non-standard signature layout; `rfactordec -y` produced invalid GMT magic.

## 2026-11-21 17:29:51 -0500 - GMT material/stage ASCII strings
- Extract ASCII strings from GMT material records and 264-byte stage blocks (`GmtStage.strings`).
- Add representative tests asserting observed texture/stage strings on `BMW_M3GTR_BUMPER_A.GMT`, `FUELHOSE.GMT`, `EXT_DRIVER_STYLE01.GMT`, `ANNOUNCERSOUND01.GMT`.
- Commit: `3a97bce`.

## 2026-11-21 17:28:05 -0500 - GMT vertex/stream structured raw views
- Parse 32-byte GMT base vertices into `GmtVertexBase` (`f0,pos.xyz,norm.xyz,f7`, observed layout).
- Capture 48-stride 16-byte extra vertex blocks and rec[7]/rec[8] stream2/3 raw data.
- Add representative round-trip/assertion tests for FUELHOSE, EXT_DRIVER_STYLE01, ANNOUNCERSOUND01.
- Commit: `2abf7c1`.

## 2026-11-21 17:25:57 -0500 - GMT base vertex fields
- Parse observed GMT base vertex fields and preserve lossless round-trip.
- Commit: `84322db`.

## 2026-11-21 17:24:37 -0500 - GMT extra stream offsets
- Expose mesh rec[7]/rec[8] as `stream2_end`/`stream3_end`.
- Add ANNOUNCERSOUND01 regression test.
- Commit: `9ddf9f2`.

## 2026-11-21 17:23:42 -0500 - Encrypted GMT TODO
- Document encrypted GMT experiment: `rfactordec.c -y` attempt on `DETOMASO_PANTERA_RAINSCREEN.GMT` produced invalid GMT magic.
- Commit: `ecdac60`.

## 2026-11-21 17:21:49 -0500 - GMT material stage blocks
- Parse 4x264-byte GMT material stage blocks with names.
- Commit: `d3f9905`.

## 2026-11-21 17:20:23 -0500 - GMT rec[7]/rec[8] note
- Document additional GMT vertex stream offsets.
- Commit: `5ce2884`.

## 2026-11-21 17:17:55 -0500 - Reference docs
- Ignore and document `modding-tools-and-tutorials` as local reference.
- Commit: `f74a4ac`.

## 2026-11-21 17:15:59 -0500 - GMT 48-byte vertex layout
- Decode 48-byte GMT vertex block layout (32-byte base + 16-byte extra) and confirm with tests.
- Commit: `1e7763c`.

## 2026-11-21 17:13:33 -0500 - GMT material L0 heuristic
- Improve GMT material boundary parsing with L0 heuristic; fixes BUMPER_A case.
- Commit: `174cf1b`.

## 2026-11-21 17:10:57 -0500 - Structural GMT parser/writer
- Add `gmt_format.py` structural parser/writer with lossless round-trip behavior.
- Record material/stride findings.
- Commit: `d5bf75f`.

## 2026-11-21 17:03:29 -0500 - Binary formats inventory
- Add `docs/binary-formats.md` with read/write status and limits.
- Commit: `b37455c`.

## 2026-11-21 17:02:02 -0500 - DSI/HAT and FXM/FXA/LMA tools
- Add `gzip_simbin_tool.py` for DSI/HAT gzip containers.
- Add `fxm_tool.py` for FXM/FXA/LMA header identification and lossless round-trip.
- Commit: `01abbb9`.

## 2026-11-21 17:00:48 -0500 - GMT flag distributions
- Record GMT header and mesh flag distributions.
- Commit: `5b05ea7`.

## 2026-11-21 16:55:47 -0500 - GMT material observations
- Note partial GMT material table observations.
- Commit: `3cd6572`.

## 2026-11-21 16:51:18 -0500 - GMT inventory findings
- Document GMT inventory and same-track GTL/GTR2 comparison findings.
- Commit: `5fa093c`.

## 2026-11-21 16:50:00 -0500 - GMT inspection improvements
- Improve GMT inspection and document header/mesh findings.
- Commit: `b630807`.

## 2026-11-21 16:44:37 -0500 - gtr2-agent-tools reference
- Document `gtr2-agent-tools` as reference-only (CC BY-NC 4.0) and record GMT parser clue.
- Commit: `8c3793a`.

## 2026-11-21 16:42:45 -0500 - GMT tool
- Add `gmt_tool.py` for GMT header/mesh inspection and diff.
- Commit: `846b576`.

## 2026-11-21 16:40:26 -0500 - GMT format notes
- Add initial GMT deep-dive notes in `docs/gmt-format.md`.
- Commit: `1a00c4e`.

## 2026-11-21 16:25:00 -0500 - MAS tool
- Add `mas_tool.py` for GMOTORMAS10 MAS create/list/extract/add/update/delete with tests.
- Commit: `846b576`-era work / early repo history (see git log for exact early commit).
