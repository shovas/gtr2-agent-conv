# Changes

Newest-first change log. Timestamps use repository commit dates (ISO 8601, local offset).

## 2026-11-26 22:20:00 -0500 - RaceGMT container validation and CLI
- Full-tier validation of `race_gmt.parse_header()` across all 643 `RaceGMT\0` meshes in Race07Complete (magic, name, constant flags, 12 bounding-box floats); `gmt_tool.py info` now reports these fields instead of meaningless standard-GMT header values. Payload geometry remains undecoded (36-/72-byte index-triple strides in some models, but no universal record layout).

## 2026-11-26 21:20:00 -0500 - HAT fields separated by mutual information
- Showed the HAT u32 carries no grid-position information (MI 7.765 bits vs 7.740 shuffled) while height B carries 4.86 bits; consolidates the u32 negatives with a permutation-controlled test.

## 2026-11-26 20:50:00 -0500 - Guard validator against GTR2 false positives
- Added a corpus regression asserting `validate_gtr2_tree()` reports zero problems on the real GTR2 GameData tree (previously only checked on converted outputs). Full-tier test added.

## 2026-11-26 20:20:00 -0500 - Replay cumulative-wheel trend negative
- Confirmed that cumulative replay u16 totals track cumulative distance only as a shared monotonic trend; the per-frame four-wheel sum is at chance. Consolidated into the existing wheel-speed negative test.

## 2026-11-26 19:50:00 -0500 - f0 preserved cross-game except mesh 0
- Established that f0 markers for submeshes at index >=1 are identical across 2,261/2,589 (87.3%) same-named GTR2/GTL meshes (permutation mean ~5), with only the first marker differing in 1,311 cases. Strengthens byte-for-byte f0 preservation in conversion; the mesh-0 difference has no simple transform (287 distinct XORs). Full-tier test added.

## 2026-11-26 19:20:00 -0500 - HAT grid extent negative
- Tested grid extent as a HAT↔track pairing validator: AIW waypoints fall inside a matching HAT's extent 11/11 times but also inside a mismatched HAT ~10.9/11, so no rule is promoted. Consolidated with the existing HAT negatives.

## 2026-11-26 18:50:00 -0500 - Replay channel CSV export
- Added `simbin_events_tool.py FILE --channels`, which exports per-frame driver-state positions, heading and the verified steering-like/vertical-motion channels as CSV for cross-recording comparison. Full-tier CLI test added.

## 2026-11-26 18:20:00 -0500 - Flag misplaced HAT files in conversion
- `validate_gtr2_tree()` now flags `.hat` files outside `GameData/Locations/HAT_Dedicated`, since GTL/Race07 use different paths and cross-game HAT bodies are not compatible. Full-tier test added.

## 2026-11-26 17:50:00 -0500 - Batch GSC covers four corpora
- Extended `batch_convert.py`'s GSC family from Copa Petrobras to GameStockCar, Stock Car Extreme and Automobilista. Sampled conversions pass 20/20 per corpus with full-tier tests over all four roots.

## 2026-11-26 17:20:00 -0500 - HAT tail 34/77-byte periodicity
- Found strong, cross-track byte-lag periodicity in the HAT trailing stream at strides 34 and 77 (11-16% agreement vs ~1.4% shuffled); no fixed record layout claimed yet. Full-tier test added.

## 2026-11-26 16:50:00 -0500 - GDB class mapping negative
- Established that rF1 GDB `Filter Properties` (track/season descriptors) and SimBin `SpecialClasses` (car-class tags) are semantically different with <10% token overlap; no cross-era class-mapping rule is derivable. Full-tier test added.

## 2026-11-26 16:20:00 -0500 - Hat u32 fractional negative
- Characterized the HAT record u32 as a [0,1] fixed-point-like fraction with simple-fraction modes, but no universal quantization and no correlation with arc length or elevation; no decoder claimed. Full-tier test added.

## 2026-11-26 15:50:00 -0500 - Decode HAT signature as spatial grid
- Decoded the 32-byte HAT layout "signature" as four f64 spatial-grid parameters (origin_x, inv_cell_x, origin_z, inv_cell_z), matching GTR2.exe's 32x32 height-tree hash at RVA 0x45de40. Added `media_tool.hat_grid_params()` / `hat_grid_bucket()` and CLI `grid_params`; verified on 178 files (rF1/SCE use 64x64 grids). Full-tier test added.

## 2026-11-26 15:20:00 -0500 - Guard against cross-game HAT reuse
- Documented and regression-tested that matching HAT layout signatures do not make bodies reusable across games (Brno 40,189 vs 41,530 records; only 3 identical). Conversion must keep HAT files game-specific.

## 2026-11-26 14:50:00 -0500 - Identify hat field B as local elevation
- Established that the .hat record's field B follows local road elevation at the record's (x,z): r=0.65-0.93 across six tracks with shuffled and circular-shift controls at zero; near-exact affine fit on flat Dubai. Supports the "height tree / surface cache" interpretation from GTR2.exe disassembly; no unit mapping claimed. Full-tier test added.

## 2026-11-26 14:20:00 -0500 - Fix hat record count from producer header
- Corrected `media_tool.hat_record_count()`: it now reads the authoritative count declared in the HAT header (body offset 44) instead of a bounded scan that undercounted six GTR2 layouts by stopping at valid zero-valued records. The `hat-layout` CLI also reports all three declared header counts; verified on 178/178 files across nine corpora. Full-tier regression test added.

## 2026-11-26 13:50:00 -0500 - Steering scale negative
- Tested a fixed bicycle-model scale for the replay steering-like channel: median ratios vary by >3x across replays with inconsistent signs, so no universal calibration is claimed. Full-tier test added.

## 2026-11-26 13:20:00 -0500 - GSC validator sample and hat u32 negative
- Verified 150/150 GSC conversions pass the GSC-aware validator (40-member full-tier test added); ruled out LE/BE/byte-swapped/sign-flipped float readings of the .hat record u32.

## 2026-11-26 12:50:00 -0500 - Test tier rebalanced
- Moved two corpus-wide tests (extended AIW galpha, rF1 tree conversion) from quick-tier modules to full tier so quick (30 s) and normal (261 s, 265 tests, 0 failures) stay within their budgets.

## 2026-11-26 12:20:00 -0500 - f0 stage-index negative
- Ruled out f0 bytes as stage-string counts/indices (0.77% hit rate vs 0.78% chance). Full-tier test added.

## 2026-11-26 11:50:00 -0500 - Hat tail float negative
- Showed the trailing stream's float-likeness is entirely explained by its byte histogram (byte-shuffled control matches 48.5% vs 48.8% observed), so no float-record decoder applies. Full-tier test added.

## 2026-11-26 11:20:00 -0500 - Document decoded replay channels
- Refined small_a: raw per-frame elevation delta fits slightly better than per-second velocity; synced FEATURES/CAPABILITIES with the decoded steering-like and vertical-motion channels.

## 2026-11-26 10:50:00 -0500 - Driver u16 wrap modulus negative
- Searched wrap moduli 1024..65536 for a wheel-speed channel in the replay u16s; none produced a consistent speed correlation. Full-tier test added.

## 2026-11-26 10:20:00 -0500 - f0 CRC16 negative
- Ruled out CRC16-CCITT/IBM of material and stage names as f0 bytes (hit rates ~0.6% vs 0.78% chance). Full-tier test added.

## 2026-11-26 09:50:00 -0500 - Driver small_b kinematics negative
- Probed small_b against elevation, speed, heading rate and lateral acceleration (with lags): signs are inconsistent across replays and mean |r|<0.25, so it remains undecoded. Full-tier test added.

## 2026-11-26 09:20:00 -0500 - Small_a gradient calibration caveat
- Tested small_a against AIW-derived road gradient: correlations range from 0.98 (Brno) to 0.00 (Imola), so no universal scale conversion is claimed. Full-tier test added.

## 2026-11-26 08:50:00 -0500 - Driver small_a tracks elevation
- Found a second driver-state channel: small_a correlates with frame-to-frame elevation change in 8/8 replays (mean r=0.641, seeded permutation p<0.001). Full-tier test added.

## 2026-11-26 08:20:00 -0500 - Steering channel primary association
- Refined the replay steering-like channel: heading rate is the primary association (8/8 replays, mean r=-0.171) while lateral acceleration is weaker (7/8, mean -0.108). Full-tier test updated.

## 2026-11-26 07:50:00 -0500 - Full rF1 tree conversion audit
- Audited tree conversion on all 16 rF1 location directories: zero exceptions and zero structural TRK/MASFile violations (remaining gaps are template-only session/AIW keys and shared archives outside the subtree). Quick-tier regression test over two tracks added.

## 2026-11-26 07:20:00 -0500 - Validator source detection guard
- Confirmed the new GSC auto-detection in `validate_conversion` does not misclassify old-layout rF1 GMTs (300/300 correctly detected as plain sources with f0/tail checks enabled); regression assertions added.

## 2026-11-26 06:50:00 -0500 - Expose steering-like replay channel
- `vcr_driver_state()` now exposes the verified `short_pair_difference` channel (shorts[0]-shorts[1]) and the replay CLI reports `first_driver_pair_diff`. Full-tier test added.

## 2026-11-26 06:20:00 -0500 - Driver short pair tracks heading
- Found a consistent steering-like signal in replay driver state: shorts[0]-shorts[1] correlates with heading rate in 8/8 replays (mean r=-0.171, seeded permutation p=0.004). Full-tier test added.

## 2026-11-26 05:50:00 -0500 - Hat field B width negative
- Ruled out .hat field B as AIW track width or groove width (r=0.11/0.24 across 14 layouts, below permutation baselines). Full-tier test added.

## 2026-11-26 05:20:00 -0500 - Hat u32 field negatives
- Ruled out the .hat record u32 as a counter or position hash (correlation with ordinal <0.012; zero U reuse across 93 duplicate points in Brno). Full-tier test added.

## 2026-11-26 04:50:00 -0500 - Hat records are track-space points
- Showed .hat record (A,C) pairs lie near the AIW track polyline: median 18.2 m (Brno) and 6.2 m (Monza) vs 84.7/96.5 m under a C-column shuffle. Full-tier permutation-controlled test added.

## 2026-11-26 04:20:00 -0500 - Validator supports GSC sources
- `validate_conversion.py` now validates ISI-encrypted GSC→GTR2 conversions against decoded geometry, with explicit N/A flags for raw-container checks. Full-tier test added.

## 2026-11-26 03:50:00 -0500 - Replay shift corpus validation
- Verified the replay time editor on all 13 shipped replays for +64 s and -64 s: exact EOF, correct frame-time deltas, unchanged summary duration and valid containers. Full-tier test added.

## 2026-11-26 03:20:00 -0500 - Hat field B weak trend caveat
- Corrected an apparent r=0.66 correlation between .hat field B and AIW waypoint count: duplicate layouts were pseudo-replication. Independent layouts give r=0.495 (p~0.07, GTR2) and r=0.326 (p~0.04, Race07); no decoder claimed. Full-tier test added.

## 2026-11-26 02:50:00 -0500 - f0 material-family association
- Quantified the reverse f0/material association on 16,547 markers: equal f0 values share a material-name 3-char prefix 18.8% vs 3.5% permuted, but exact names only 6.7% — family-level, not an ID. Full-tier test added.

## 2026-11-26 02:20:00 -0500 - Extended AIW corpus validation
- Verified the CRLF-fixed converter on 223 additional rF1-lineage AIWs (Automobilista, Stock Car Extreme, BMW M3 Challenge, Superleague 2009): no key corruption and all galpha values <= 0.45. Full-tier regression test added.

## 2026-11-26 01:50:00 -0500 - Correct SCN to TRK MASFile conventions
- Fixed `text_convert.scn_to_trk()` to emit bare (unquoted) `.gtr` MASFile references and the corpus-universal `Misc.gtr` entry; all 16 GTR2 map archives use `.gtr`. End-to-end Joesville conversion validator problems dropped from 22 to 17 (remaining ones need template data or shared archives). Full-tier regression test added.

## 2026-11-26 01:20:00 -0500 - Fix CRLF handling in TRK/SCN rewrites
- Fixed the same CRLF normalization bug in `text_convert.scn_to_trk()` and `trk_extensions_to_gtr2()`: rewritten lines now keep CRLF endings and trailing comments. Verified on all 25 GTL TRK files (zero mixed-ending outputs); regression tests added.

## 2026-11-26 00:45:00 -0500 - Fix CRLF handling in AIW conversion
- Fixed a corpus-discovered bug in `aiw_for_simbin()`: CRLF line endings previously corrupted keys into `wpwp_galpha` and left commented `wp_galpha` values unscaled. Indentation, comments and line endings are preserved; already-SimBin inputs are left unchanged. Full-tier tests verify all 39 rF1 AIWs convert to galpha <= 0.45.

## 2026-11-26 00:10:00 -0500 - Hat CLI reports record count
- `media_tool.py hat-layout` now reports the verified 16-byte record-table count, distinguishing layouts that share a 32-byte signature (e.g. four Dubai variants). Full-tier test added.

## 2026-12-01 11:20:00 -0500 - Hat trailing stream periodicity
- Measured the .hat trailing stream: byte-lag 8 agreement 7.5-10.7% vs 1.3-1.7% shuffled, with float-exponent bytes dominating; plain 8-byte f32 records excluded. Full-tier test added.

## 2026-12-01 10:50:00 -0500 - Hat records not waypoints
- Ruled out .hat record triples as AIW waypoint or CAM camera positions (zero near matches in Brno/Monza, shuffled control equal); full-tier test added.

## 2026-12-01 10:20:00 -0500 - Hat body record table
- Found a fixed 16-byte record table at .hat body offset 48: `[f32, u32, f32, f32]`, with layout-specific counts (7-61,412) that fingerprint byte-identical bodies under permutation (p<0.001). Full-tier test added; field semantics still undecoded.

## 2026-12-01 09:50:00 -0500 - Hat signature across three games
- Verified the 32-byte .hat layout signature also applies to Race07's Ver 0.08 variant: Race07 Anderstorp matches GTR2 Anderstorp, and the hat-layout CLI works unchanged across GTR2/GTL/Race07. Full-tier test added.

## 2026-12-01 09:20:00 -0500 - Hat layout identification CLI
- Added `media_tool.py hat-layout FILE CORPUS_DIR` to identify a .hat track layout from its verified 32-byte signature, including cross-game GTL/GTR2 matches. Full-tier test added.

## 2026-12-01 08:50:00 -0500 - Driver u16 delta trend negative
- Showed apparent u16-delta/speed correlations are shared slow trends: detrending collapses all four outlier-robust cases to |r|<=0.109. Full-tier regression test added.

## 2026-12-01 08:20:00 -0500 - Batch GSC UV verification
- `batch_convert.py` now verifies byte-exact UV preservation for GSC→GTR2 conversions before writing output (60/60 sampled members); a metamorphic test proves a corrupted UV is rejected.

## 2026-12-01 07:45:00 -0500 - f0 material-string hash negative
- Ruled out f0's two bytes as material/stage string hashes or indices under distribution-preserving controls; full-tier regression test added.

## 2026-12-01 07:10:00 -0500 - Independent cross-check covers all submeshes
- Strengthened `validate_conversion.py`: its schema-only reader now reads every submesh (100/100 agree with gmt_semantic) and the validator compares positions, UVs and exact triangles for all of them; a metamorphic test proves second-submesh corruption is caught.

## 2026-12-01 06:35:00 -0500 - Validator guards f0 preservation
- `validate_conversion.py` now checks exact per-mesh f0 marker preservation in addition to geometry, UVs and material tail; verified on 30 sampled conversions, with a metamorphic test proving f0 corruption is rejected.

## 2026-12-01 06:00:00 -0500 - Cross-game hat signature
- Verified the 32-byte .hat layout signature is identical between GTL and GTR2 for the same layout (p=0.003 under name permutation); bodies still diverge, so no cross-game body conversion. Full-tier test added.

## 2026-12-01 05:25:00 -0500 - Hat ID hash negative
- Ruled out the .hat track ID as a hash of track/asset filenames or file contents; raw-byte matches in media were coincidences under a distribution-preserving control. Full-tier test added.

## 2026-12-01 04:55:00 -0500 - Hat body deterministic per layout
- Extended the .hat finding: bodies are byte-identical after byte 4 within physical layouts (11 files in 5 classes, up to 3.78 MB identical), and body[16:36] is a 20-byte layout signature (17 values). Corrected the earlier "high-entropy random" reading. Full-tier test added.

## 2026-12-01 04:20:00 -0500 - Hat header track identifier
- Found a per-track identifier in the .hat header: bytes 4:16 match in 24/28 within-track pairs vs 1.2 by permutation (p<0.001); the 4 exceptions are different physical layouts. Body after the header remains undecoded. Full-tier test added.

## 2026-12-01 03:45:00 -0500 - Driver u16 units negative
- Cross-checked replay u16s against live per-wheel units: fixed-point temperature and half-float pressure interpretations both fail across cars; full-tier test guards the negative.

## 2026-12-01 03:15:00 -0500 - GTTF units cross-check
- Cross-checked GTTF frame ranges against live shared-memory units: +32/1024 is RPM-shaped (1177-5807, lag-1 0.992 vs shuffled ~0); +16/+8 are normalized controls. Permutation-controlled test added.

## 2026-12-01 02:45:00 -0500 - External tool review documented
- Reviewed the updated ../gtr2-agent-tools repo (commit b1c7f50): recorded its live GTR2 telemetry layout, independent parsers used as regression oracle, Driving School/GTT/HAT findings and CC BY-NC 4.0 reference-only status in docs/tools-reference.md.

## 2026-12-01 02:15:00 -0500 - Replay time-shift CLI
- Added `simbin_events_tool.py FILE --shift SECONDS --out OUT` to write a valid shifted replay container; CLI test added.

## 2026-12-01 01:45:00 -0500 - Archive round-trip independent validation
- Extended the rF1→GTR2 archive round-trip test to validate converted GMTs with the independent reference parser; tests pass.

## 2026-12-01 01:15:00 -0500 - f0 direct-reuse negative
- Ruled out f0 as a directly reused u32 in material records or an ASCII tag; matches were trivial common values. Consolidated negative list updated.

## 2026-12-01 00:45:00 -0500 - Triangle-level independent validation
- Strengthened the independent parser test to compare exact triangle lists: 20/20 converted meshes agree across 17,588 faces.

## 2026-12-01 00:15:00 -0500 - Independent parser validation extended
- Extended the independent gtr2-agent-tools validation to GTR1 conversions as well as GSC; full-tier test passes on both families.

## 2026-11-30 23:45:00 -0500 - f0 filename negative
- Ruled out CRC32/byte-sum of GMT member filename as f0 source (chance-level across 21,481 markers). Added to consolidated f0 negative list.

## 2026-11-30 23:15:00 -0500 - Independent parser validation
- Validated 20/20 real and converted GMTs against the independent gtr2-agent-tools GMT reader (mesh/vertex counts agree); full-tier test added, skipping when the reference tree is absent.

## 2026-11-30 23:15:00 -0500 - Feature docs refreshed
- Updated FEATURES.md replay/container sections to describe the decoded frame stream, participant and time-editing capabilities, and the remaining .hat limitation. Final PHS EXE sweep recorded as blocked.

## 2026-11-30 22:45:00 -0500 - CAM orientation negative
- Recorded weak camera-yaw vs AIW-heading correlation (0.062 vs 0.031 shuffled); no orientation transform claimed. Quick tier: 125 tests, 0 failures, 27.1s.

## 2026-11-30 22:15:00 -0500 - f0 findings consolidated
- Corrected "external authoring identifier" from conclusion to working hypothesis and consolidated all rejected f0 hypotheses in `docs/format-findings.md`; added the object-list-offset negative to the research log.

## 2026-11-30 21:45:00 -0500 - Driver u16 pairing observation
- Verified the four driver-state u16s form wheel-like pairs (rear gap <1% of scale in Monza); no AIW-ordinal or curvature semantics found. Full-tier test added.

## 2026-11-30 21:15:00 -0500 - Hat cipher negative and u16 curvature negative
- Ruled out the three known gMb keys for .hat bodies (entropy rises to ~7.91). Recorded that driver-state u16 fields have no curvature association. Documentation-only.

## 2026-11-30 20:45:00 -0500 - Hat payload characterization
- Characterized .hat bodies as high-entropy (7.4-7.6 bits/byte), non-4-aligned packed data across 36 files; no decoder claimed. Full-tier test added.

## 2026-11-30 20:15:00 -0500 - Archive read cache
- Added a bounded 64MB decompressed-member cache in `mas_tool.read_archive()` keyed by path/mtime/offset. Normal tier 252s / 252 tests / 0 failures (was 263.5s). Invalidation regression test added.

## 2026-11-30 19:45:00 -0500 - gMb container inventory
- Verified byte-identical gzip round-trip for all 197 gMb files (.dsi/.gtt/.hat/.vcr); `.hat` payload remains undecoded (no periodicity). Full-tier test added.

## 2026-11-30 19:15:00 -0500 - Full DSI corpus validation
- Verified all 142 shipped .dsi files parse exactly to EOF (68,916 frames); full-tier test extended.

## 2026-11-30 18:45:00 -0500 - DSI files share replay frame stream
- Verified driving-school .dsi files parse with the replay decoders; their ghost polyline equals the decoded driver-state positions exactly (byte-exact). Full-tier test added.

## 2026-11-30 18:15:00 -0500 - Semantic GMT reader magic fix
- Fixed a parser gap: `find_submeshes()` now recognizes 0x60xx mesh magics (previously returning zero submeshes for BRIDGE1/camera meshes). Zero mismatches across 3,199 GMTs; full-tier test added.

## 2026-11-30 17:45:00 -0500 - Replay CLI covers GTL v1.01
- Extended the `--replay` CLI test to cover GTL v1.01 summaries (10564 frames, exact EOF); no code change needed since the decoder is version-aware.

## 2026-11-30 17:15:00 -0500 - f0 material metadata negative
- Recorded that f0 bytes do not encode material name/stage/string lengths (21,481 markers, all correlations below threshold). F0 remains opaque; preservation is sufficient for conversion.

## 2026-11-30 16:45:00 -0500 - Replay time-shift editor
- Added `simbin_events_tool.shift_replay_times()` to shift frame times and participant windows consistently; spans and sub-records unchanged. Full-tier test added.

## 2026-11-30 16:15:00 -0500 - GTL v1.01 replay decoded
- Resolved the GTL replay variant: v1.01 uses a -1e32 sentinel with zero-prefixed u24 counts and f32 duration. All 13 local replays (9 GTR2 + 4 GTL) now parse exactly to EOF. Full-tier tests updated.

## 2026-11-30 15:45:00 -0500 - GTL replay variant guard
- GTL v1.01 replays declare zero frames; added guards to reject phantom frames. All 9 GTR2 replays still parse exactly. Full-tier test added.

## 2026-11-30 15:15:00 -0500 - Replay remaining fields negative
- Tested u16 and small-f32 driver fields: no consistent semantics across files (fixed-point temperature hypothesis fails on Imola). Recorded as negative; replay CLI now prints first-driver position/angle and raw shorts.

## 2026-11-30 14:45:00 -0500 - Replay driver angle field
- Corrected the angle field label (byte 45, not 41) and validated its association with derived heading (|r| ~0.52 vs 0.05 shuffled). Full-tier test added.

## 2026-11-30 14:15:00 -0500 - Replay driver-state alignment fixed
- Corrected an off-by-one: the f32 block in 53-byte driver bodies starts at byte 29, not 28. `vcr_driver_state()` exposes four u16s plus six f32s; first three are confirmed smooth world positions. Full-tier test added.

## 2026-11-30 13:45:00 -0500 - Replay sub-record tag classification
- Classified sub-record low-byte tags: 0..N-2 driver state, 0x68 marshal, 0xff events (some carry texture names). Added `vcr_record_tag()` and a full-tier test; field-level body decoding remains unclaimed.

## 2026-11-30 13:15:00 -0500 - Replay CLI reporting
- Added `simbin_events_tool.py --replay` to report participants, summary and parsed frame stream; CLI test added. PHS producer/consumer revisited with no new evidence (no GTL.exe archive reference, no 0.9.01 updater found).

## 2026-11-30 12:45:00 -0500 - All GTR2 replay variants parse
- Resolved both replay exceptions: Anderstorp has a second 82-frame segment (203 total), and Dubai uses a Latin-1 accented participant name. All 9 GTR2 replay payloads now parse exactly to EOF; full-tier test updated.

## 2026-11-30 12:15:00 -0500 - Replay frame decoder complete
- Fixed a misread of the packed sub-record size (+1 only in the special branch) and added `parse_vcr_frames()`: 7/9 GTR2 replays parse exactly to payload end, sub-record totals equal count_b, frame time spans equal summary durations, and first frame times equal participant window starts. Full-tier test added.

## 2026-11-30 11:45:00 -0500 - Replay frame layout from reader code
- Disassembled the ghost reader: summary count_a frames, each a 6-byte header (u32 + u16 subcount) followed by u32-headed sub-records with a packed 10-bit size. Recorded as code-level layout; payload alignment remains unresolved. Test extended.

## 2026-11-30 11:15:00 -0500 - ISI cipher performance optimization
- Optimized `isi_crypt.isi_crypt()` with per-block precomputed stream values, removing tens of millions of redundant Python calls. Byte-exact equivalence verified on random vectors and real GSC members; GSC UV test 69s -> 24.6s. Full-tier reference test added.

## 2026-11-30 10:45:00 -0500 - Per-frame replay negative
- Recorded that the post-summary payload has no repeating frame record: variable lag peaks, non-integer count divisions, and a one-off header-like block. No per-frame decoder claimed.

## 2026-11-30 10:15:00 -0500 - Replay post-object summary parser
- Added `parse_replay_summary()` for the 13-byte structure after participant records (marker, two counts, duration); validated on 9 GTR2 replays with a full-tier test. Count semantics remain unclaimed.

## 2026-11-30 09:45:00 -0500 - Replay activity window decoded
- Decoded the object record's trailing f32 pair as an activity window with -1e32 (0xF49DC5AE) as "unbounded", confirmed by EXE comparison code at 0x5269c0 and by all finite windows being ordered. `parse_object_records()` exposes window_start/window_end. Full-tier test updated.

## 2026-11-30 09:15:00 -0500 - Replay trailing-field characterization
- Characterized object-record u32s: second field is the f32 unset sentinel (-1e32) or zero in 35/36 records; first is finite/non-negative but consumer and units remain unknown. Full-tier test added.

## 2026-11-30 08:45:00 -0500 - Replay participant car/skin decoded
- Decoded the object record's 64-byte blocks as .CAR filename (36/36 records) and .BMP skin name; exposed value/trailing fields in `parse_object_records()`. Test extended.

## 2026-11-30 08:15:00 -0500 - Replay object-record parser
- Implemented `simbin_events_tool.parse_object_records()` from the EXE-derived layout; it recovers participant chains (2-6 records) in all nine GTR2 replays vs ~1 for shuffled payloads. Full-tier permutation-controlled test added.

## 2026-11-30 07:45:00 -0500 - Replay object record layout from code
- Disassembled the per-object replay writer/reader: flags byte with top bit at +0xcc, two u8 length-prefixed strings, two 64-byte blocks, two u32 fields. Confirms variable-length object records; test extended.

## 2026-11-30 07:15:00 -0500 - Ghost writer located in GTR2.exe
- Statically identified the GTTF/IRSR writer at RVA 0x52a540 with a 105-object serialization loop, supporting variable-length replay records. Byte-pattern regression test added; no frame layout claimed.

## 2026-11-30 06:45:00 -0500 - Stream parser regression fix
- Scoped the vc*32 single-block stream check to the rec6-only fallback so two-stream meshes with declared blob sizes are preserved verbatim. Caught by `tests.test_gmt_relayout`; 40 module tests and the normal tier pass.

## 2026-11-30 06:30:00 -0500 - Normal-tier performance optimizations
- Optimized three test-suite bottlenecks without weakening assertions: `gmt_semantic.find_submeshes()` now searches the six magic byte patterns (15.7x faster, exact equivalence on 698 samples); `find_frame_grid()` uses the GTTF marker fast path (42s -> 17s module time, equivalent on all 42 event files); `test_gmt_layout` caches its fixture scan. Normal tier now 263.5s / 250 tests / 0 failures, back inside the 300s budget.

## 2026-11-30 06:00:00 -0500 - Tiling ratios in material records
- Found a modest material-record enrichment for UV tiling ratios (0.314 vs 0.160 distribution-preserving baseline) but no fixed material field. Full-tier test added; no decoder claimed.

## 2026-11-30 05:30:00 -0500 - GTL replay coverage
- Verified the four GTL .Vcr replays parse as IRSR v1.01 (vs GTR2 v1.05) and rewrap byte-identically. Full-tier test added.

## 2026-11-30 05:00:00 -0500 - GTTF frame-time editor
- Added `simbin_events_tool.shift_frame_times()`; verified a +64 s shift preserves all other frame fields with only f32 rounding error (≤7.6e-6 s). Full-tier test added.

## 2026-11-30 04:30:00 -0500 - GTTF session-field editor
- Added `simbin_events_tool.set_session_seconds()` to edit the header session f32 in place; verified on 29 ghosts that at most four bytes change and the container rewraps correctly. Full-tier test added.

## 2026-11-30 04:00:00 -0500 - Byte-identical SimBin containers
- Added `gzip_simbin_tool.compress_simbin()` which reproduces shipped GTT/VCR gzip containers byte-for-byte (29 ghosts + 9 replays). Removes the container barrier for a future ghost writer. Full-tier test added.

## 2026-11-30 03:30:00 -0500 - GTTF path f3 vs AIW curvature
- Found f3 tracks AIW-derived curvature (median |r| 0.142 vs 0.068 shuffled) while raw AIW attributes are chance-level. Full-tier permutation-controlled test added.

## 2026-11-30 03:00:00 -0500 - GTTF path f4 vs AIW galpha
- Found path control f4 correlates with AIW waypoint galpha (median |r| 0.276 vs 0.085 shuffled, 27 ghosts). Full-tier permutation-controlled test added; findings docs updated.

## 2026-11-30 02:30:00 -0500 - GTTF tail final-state fields decoded
- Decoded the remaining GTTF tail floats: float 3 ≈ final heading (0.0004 rad), float 4 ≈ final +16, float 2 tracks final slot48_low (|r| 0.993 vs 0.24 shuffled). Full-tier permutation-controlled test added.

## 2026-11-30 02:00:00 -0500 - GTTF tail is a track point
- Identified a 20-byte GTTF tail whose first two floats are a per-track fixed point (median 0.6 within track vs 178 random); full-tier test added. Remaining three floats undecoded.

## 2026-11-30 01:30:00 -0500 - GTTF time field validated
- Proved frame +20 is absolute session seconds: last-minus-first matches every ghost filename lap time (median error 0.0023 s, max 0.034 s, vs 23.59 s shuffled). Full-tier permutation-controlled test added.

## 2026-11-30 01:00:00 -0500 - GTTF vs IRSR header flags
- Documented that GTTF ghosts have a fixed header flag tuple (0,0,1,0) across all 29 files while IRSR replays vary; no flag semantics claimed. Full-tier test added.

## 2026-11-30 00:30:00 -0500 - VCR frame-field negatives
- Recorded that the 20-byte bulk stride has no smooth f32 field, no constant byte offsets, and only mild delta smoothing; replay frame decoding remains blocked. Findings log updated.

## 2026-11-30 00:00:00 -0500 - VCR bulk 20-byte lag excess
- Found a 20-byte autocorrelation excess in replay bulk data (7/9 files, median +0.16 over neighbouring lags); full-tier test added. Frame semantics still undecoded.

## 2026-11-29 23:30:00 -0500 - VCR 86-byte period scoped to header
- Found an 86-byte period via byte-level autocorrelation (0.567 vs 0.127 shuffled), then localized it to the replay header (0.78) rather than bulk frame data (0.04). Corrected the initial too-broad interpretation; full-tier test scoped accordingly.

## 2026-11-29 23:00:00 -0500 - Converted UV range characterization
- Characterized converted UV ranges: source GSC/VRL UVs are much wider than shipped GTR2 UVs (median |u| ~0.99 vs 0.39); values remain finite and bounded. Documented as a visual-correctness caveat with a full-tier guard test.

## 2026-11-29 22:30:00 -0500 - UV tiling ratios in Race07
- Confirmed the integer UV tiling-ratio rule decodes in JCA-decrypted Race07 meshes as well as GTR2; full-tier deterministic-sample test added.

## 2026-11-29 22:00:00 -0500 - GSC UV preservation at scale
- Verified source and converted UV pairs are exactly equal on 150/150 GSC members. Full-tier regression test added; findings doc updated.

## 2026-11-29 21:30:00 -0500 - PHS cipher-header negatives
- Confirmed no ISI/JCA/gMb header in any of the five GTL PHS members at offsets 0..64; exactly one opaque member remains. Full-tier guard test added; no speculative decoder.

## 2026-11-29 21:00:00 -0500 - CAM pass-through and f0 CRC negative
- Verified the rF1→GTR2 pipeline leaves CAM files byte-identical (50/50), consistent with the cross-generation CAM/AIW convention. Recorded that f0 is not a CRC of geometry bytes. Full-tier pass-through test added.

## 2026-11-29 20:30:00 -0500 - Unified GTR2 UV reader
- Added `gmt_format.read_mesh_uvs()` returning UV pairs from both single-block and two-stream GTR2 meshes; verified identical to the semantic reader on 800/800 sampled meshes. Full-tier test added.

## 2026-11-29 20:00:00 -0500 - CAM inversion is cross-generation
- Corrected the earlier implication that CAM negation is GTR2-specific: rF1 (594/684) and GTL (246/274) show the same inverted CAM-vs-AIW convention. No negation should be added by an rF1→GTR2 converter. Full-tier test added.

## 2026-11-29 19:30:00 -0500 - CAM activation points confirm inversion
- Confirmed the CAM/AIW coordinate inversion at point level: negating ActivationLocation puts cameras 4.4x nearer to AIW waypoints (25.2 vs 110.2 units; 80% of 422 cameras). Full-tier test added.

## 2026-11-29 19:00:00 -0500 - CAM/AIW coordinate inversion verified
- Confirmed empirically that GTR2 camera positions are inverted relative to AIW waypoints (x opposite-sign in 90% of 30 matched tracks vs 53.5% shuffled, r -0.842). Full-tier permutation-controlled test added.

## 2026-11-29 18:30:00 -0500 - UV tiling ratios are material properties
- Found meshes sharing a material share UV tiling ratios (91.6% of 487 groups vs 4.8% shuffled). Full-tier permutation-controlled test added; findings docs updated.

## 2026-11-29 18:00:00 -0500 - UV parser fallback fix
- Fixed an overly broad single-block UV fallback that exposed misaligned streams on some meshes; the parser now requires exact vc*32 length. Scoped the stream column-7 invariant to two-stream meshes. All 35 gmt_format module tests and 5 affected full-tier tests pass.

## 2026-11-29 17:30:00 -0500 - Template-free GMT container
- Added `gmt_format.build_synthetic_gmt()` to build a structurally valid GTR2 GMT without a game-data template. Parses, round-trips and passes material validation; full-tier test added. No materials/textures are included, so it is a fallback/test container only.

## 2026-11-29 17:00:00 -0500 - f0 stage-index negative
- Recorded that f0 bytes are not material-stage indices (3,935 matches vs 3,937 shuffled); full-tier guard test added.

## 2026-11-29 16:30:00 -0500 - GTR2 UV tiling ratios
- Found that many GTR2 UV streams encode constant integer tiling ratios (columns 4/6 vs column 2; 915/1,980 meshes vs 0/500 column-shuffled). Added `gmt_format.uv_tiling_factors()`, a full-tier test, and findings docs.

## 2026-11-29 16:00:00 -0500 - GTTF control complementarity caveat
- Found path-record f3/f4 only loosely complementary (sum 0.85, r -0.136 vs 0.009 shuffled) versus near-exact at frame level; documented as a caveat with a full-tier test.

## 2026-11-29 15:30:00 -0500 - UV layout flag rule
- Found a perfect structural rule: mesh flag bit 0x20 selects the two-stream UV layout (40,327/40,327 meshes agree). Verified all converter outputs are consistent. Full-tier test added; findings docs updated.

## 2026-11-29 15:00:00 -0500 - GTTF byte 31 further negatives
- Recorded that gear bands explain only 2.8% of byte +31 variance and that acceleration/heading-rate/speed-change correlations are at baseline; encoding remains unresolved. Findings log updated.

## 2026-11-29 14:30:00 -0500 - GTL mesh layout confirmed
- Verified all 2,529 sampled GTL archive GMTs use the new layout, confirming GTL→GTR2 needs no mesh relayout. Full-tier test added. Note: the fresh full-suite run exceeded the 60-minute shell timeout and produced no result; it predates recent commits.

## 2026-11-29 14:00:00 -0500 - f0 material-index artefact
- Recorded that the apparent f0-high/material-index link (13.3% vs 4.2% shuffled) is a mesh-0 artefact (44.9% for mesh 0, 0.5–2.1% later). Full-tier guard test added; findings docs updated.

## 2026-11-29 13:30:00 -0500 - VCR frame layout negative
- Recorded that no fixed-stride monotonic time field exists in .Vcr payloads (strides 20..2040 scanned), so replay frame decoding remains blocked. Findings log updated.

## 2026-11-29 13:00:00 -0500 - VCR replay header coverage
- Verified all nine shipped .Vcr replays parse as IRSR with the existing reader (driver/car/session fields); frame grid remains undetected and is documented as a distinct format. Full-tier test added.

## 2026-11-29 12:30:00 -0500 - f0 scope boundary recorded
- Recorded that GTR2/GTL f0 marker semantics do not apply to JCA-decrypted Volvo/Race07 GMTs (their rec[4] holds float-shaped data). No code change; findings docs updated.

## 2026-11-29 12:00:00 -0500 - UV inspection CLI
- Added `gmt_tool.py uv FILE` to report UV block size, signature, decoded-triple status and sample UV pairs; regression test added.

## 2026-11-29 11:30:00 -0500 - Cross-game UV layout confirmation
- Confirmed the GTR2 UV block layout in JCA-decrypted Volvo and Race07 GMTs (300/300 each with UV blocks; 86%/88% matching dominant signatures vs 0% shuffled). Full-tier test added.

## 2026-11-29 11:00:00 -0500 - Batch UV coverage verified
- Stress-tested 300 conversions (100 per family) with 100% success: VRL and GSC outputs all carry UV blocks; GTR1 UVs appear on all 213 descriptor-based meshes and none of the 187 descriptor-less ones. Full-tier invariant test added.

## 2026-11-29 10:30:00 -0500 - VRL UV transfer implemented
- VRL conversions now transfer per-corner UVs by expanding shared vertices at seams and rebasing triangle indices. 25/25 sampled conversions round-trip UVs exactly (shuffled UVs fail >90%); verification and docs updated.

## 2026-11-29 10:00:00 -0500 - VRL UV transfer gap documented
- Recorded why VRL UVs are still not transferred: coordinates are per-corner (only 36/300 files even match vertex count, none with identity indices), so correct transfer needs vertex splitting and index rebasing. No speculative decoder shipped.

## 2026-11-29 09:30:00 -0500 - GTR1 UV transfer enabled
- Identified GTR1 vertex fields 9/10 as UVs (fields 8/11 always zero in 20,017 samples) and enabled their transfer into GTR2 UV blocks; 30/30 sampled conversions reproduce UVs exactly. Full-tier test added.

## 2026-11-29 09:00:00 -0500 - Single-block UV round-trip guarantee
- Verified repacking preserves vertex and UV bytes on 563 real GTR2 single-block meshes; full-tier regression test added.

## 2026-11-29 08:30:00 -0500 - GTR2 stream3/f0 sparsity artefact
- Recorded a negative: stream3 column 0 and f0 both appear only at vertex 0, so their apparent per-vertex correlation of 1.0 is a sparsity artefact. Full-tier test added; methodology note in findings docs.

## 2026-11-29 08:00:00 -0500 - GTR2 two-stream UV duplication
- Found that GTR2 two-stream meshes duplicate one UV-like pair (96% per-vertex agreement, 1.0 vs 0.023 shuffled; stream3 tail always zero). Added `gmt_format.stream_cross_agreement()`, a full-tier test, and findings docs updates.

## 2026-11-29 07:30:00 -0500 - GTTF byte 31 not an RPM code
- Recorded a negative: the +31 byte is not a deterministic monotonic engine-RPM code (rank |rho| 0.311 vs 0.096 permuted; both byte clusters occur at similar RPM). Findings log updated.

## 2026-11-29 07:00:00 -0500 - GTTF byte 31 engine link
- Found GTTF byte +31 tracks engine speed (median |r| 0.263 vs 0.021 permuted; 0.198 after removing clamps), strengthening the case that it is track/vehicle state rather than a packing exponent. Full-tier test added; findings docs updated.

## 2026-11-29 06:30:00 -0500 - GTR2 UV block layouts + converter fix
- Fixed a conversion-fidelity bug: converted GMTs wrote UVs at +8/+12 behind a 4-byte count lead, while real GTR2 uses a lead-free vc*32 block with UVs at +4/+8. Parser now exposes both single-block and two-stream layouts; converted UV blocks match real GTR2 exactly and offline UV validation passes again. Full-tier test added.

## 2026-11-29 06:00:00 -0500 - GMT inspect CLI shows new findings
- `gmt_tool.py info --meshes` now reports f0 byte pairs, consecutive-pair flags, and extra-stream column signatures / decoded triples. Regression test added.

## 2026-11-29 05:30:00 -0500 - GTR2 stream column invariant
- Verified that stream column 7 repeats column 1 in 99.73% of 2,601 GTR2 meshes (exceptions are TRACKnn meshes). Added `gmt_format.stream_column_signature()` and a full-tier test; findings docs updated.

## 2026-11-29 05:00:00 -0500 - GSC conversion round-trip guarantee
- Verified that repacking 40 converted GSC→GTR2 GMTs preserves vertex and stream bytes exactly; full-tier regression test added.

## 2026-11-29 04:30:00 -0500 - GTR2 extra vertex stream structure
- Located a UV-candidate stream in GTR2 GMTs: meshes with extra 32-byte-per-vertex streams reduce to three distinct values in 46.7% of cases (vs 0% shuffled). Added `gmt_format.decode_stream_records()` and a full-tier test; semantics remain unassigned.

## 2026-11-29 03:30:00 -0500 - f0 byte-pair structure
- Resolved f0's "near-equal halves" to a concrete byte-pair rule: for even low bytes, the upper byte is low+1 in 60.3% of markers vs 0.8% shuffled. Added `gmt_format.f0_byte_pair()`, a full-tier regression test, and updated findings docs.

## 2026-11-29 04:00:00 -0500 - Full suite result
- Full-tier run on an earlier HEAD completed: 591 tests, 0 failures, 0 errors, 2 skipped (3289 s).

## 2026-11-29 03:00:00 -0500 - GSC conversion index integrity
- Validated 56,273 converted triangles (40 meshes): no out-of-range indices or degenerate faces. Full-tier regression test added; findings doc updated.

## 2026-11-29 02:30:00 -0500 - Debug artifact sweep negative
- Searched all ISIMotor installs for PDBs/debug symbols: only RSDS references (GTR2 PDB path/GUID) with no PDB files, no COFF symbols, and no useful RTTI. Full-tier regression test added; findings docs updated.

## 2026-11-29 02:00:00 -0500 - GTTF +36 exponent link
- Found slot +36's quantization exponent tracks path f4 (median r 0.274 vs 0.016 permuted, positive in all 29 ghosts); exact units unresolved. Full-tier test added; findings docs updated.

## 2026-11-29 01:30:00 -0500 - Dedicated EXE serializer negative
- Searched GTR2Dedicated.exe for GTTF frame serialization: same pointer-table structure as GTR2.exe, no 63-byte read sites. Full-tier negative test added; findings docs updated.

## 2026-11-29 01:00:00 -0500 - GSC decode CLI
- Added `gmt_tool.py decode-gsc` to decrypt and convert an encrypted GSC GMT member to GTR2 layout with validation; regression test added.

## 2026-11-29 00:30:00 -0500 - GTTF complementary path controls
- Verified path f3/f4 are complementary (median r -0.59 vs -0.001 permuted; median sum 1.0; f3 zero in 77% of frames). Full-tier test added; findings docs updated.

## 2026-11-29 00:00:00 -0500 - GTTF marker prefix validator
- Verified bytes +24..+30 are the fixed marker 01 00 00 34 00 20 00 across all 44,631 frames; full-tier validator added and findings docs updated.

## 2026-11-28 23:30:00 -0500 - GTTF byte 31 path elevation
- Found the varying byte at GTTF frame +31 tracks path y (median |r| 0.164 vs 0.020 permuted), replacing the earlier "exponent artifact" interpretation. Full-tier test added; findings docs updated.

## 2026-11-28 23:00:00 -0500 - GTTF path f4 curvature link
- Found path f4 tracks curvature (median |r| 0.072 vs 0.020 permuted, positive in 23/29); documented as an association without pedal semantics. Full-tier test added.

## 2026-11-28 22:30:00 -0500 - GTTF path f3 curvature link
- Found path f3 tracks racing-line curvature (median |r| 0.060 vs 0.019 permuted), supporting a brake-like interpretation. Full-tier test added; findings docs updated.

## 2026-11-28 22:00:00 -0500 - mesh-0 f0 vs member size
- Verified mesh-0 f0 half-sum tracks GMT member size (r 0.159 vs 0.009 permuted); full-tier test added and findings docs updated.

## 2026-11-28 21:30:00 -0500 - GTTF +48 low vs path f3
- After removing clamped frames, slot +48's low half still tracks path f3 (median |r| 0.101 vs 0.022 permuted). Full-tier permutation-controlled test added.

## 2026-11-28 21:00:00 -0500 - GTTF time vs path x
- A frame/path field matrix confirmed y/z/heading mappings and found frame time tracks path x (median |r| 0.568 vs 0.017 permuted), identifying x as longitudinal progress. Full-tier test added.

## 2026-11-28 20:30:00 -0500 - GTTF heading from path records
- Found ghost +12 heading matches the matched path record's heading with median coherence 0.992 vs 0.024 permuted across 29 ghosts. Full-tier permutation-controlled test added.

## 2026-11-28 20:00:00 -0500 - GTTF path count ratio
- Verified frame/path-record count ratio is bounded (median 2.44, range 1.93–3.49) across 29 ghosts; full-tier validator added.

## 2026-11-28 19:30:00 -0500 - f0 invariant warnings
- `gmt_tool.py f0` now warns on unexpected mesh-0 near-equal markers and large later-mesh half-deltas; regression test added.

## 2026-11-28 19:00:00 -0500 - GTTF +16 engine coupling
- Found frame +16's unclamped values couple weakly to engine +32 (median |r| 0.152 vs 0.020 permuted), unlike the +8/+16 clamp artifact. Full-tier permutation-controlled test added.

## 2026-11-28 18:30:00 -0500 - GTR2 UV block negative
- Documented that sampled GTR2 meshes lack a 16-byte extra UV vertex block, so converted UVs cannot be validated with current parser; full-tier regression test added.

## 2026-11-28 18:00:00 -0500 - Full suite regression evidence
- A full-tier run completed: **574 tests, 0 failures, 0 errors, 2 skipped, 3009 s** across 54 modules. Caveat: the run was started at the commit `b7fa803`-era tree; subsequent commits (f0/GTTF invariance work) have only quick-tier and targeted full-tier regression evidence, not a fresh full rerun.


## 2026-11-28 17:45:00 -0500 - mesh-0 f0 vs mesh count
- Verified mesh-0 f0 half-sum tracks GMT mesh count (r≈0.13 vs 0.009 permuted); full-tier distribution-preserving test added.

## 2026-11-28 17:15:00 -0500 - f0 CLI report
- Added `gmt_tool.py f0 FILE` to report per-mesh marker halves, deltas and near-equal counts; regression test added.

## 2026-11-28 16:45:00 -0500 - f0 mesh-0 distinctness
- Found mesh 0's f0 halves/delta structurally distinct (median delta 314 vs 1 for later meshes; permutation baseline 0.1). Full-tier regression test added.

## 2026-11-28 16:15:00 -0500 - f0 index terminology clarified
- Verified material_index equals mesh ordinal in 99.97% of meshes; f0 invariants are with respect to mesh position in the GMT. Regression test added.

## 2026-11-28 15:45:00 -0500 - f0 half-sum invariant
- Verified f0's paired-half mean inversely tracks material index (r -0.264 vs 0.006 permuted); full-tier distribution-preserving test added.

## 2026-11-28 15:15:00 -0500 - f0 paired-ID sign invariant
- Found f0 half-difference sign family-stable (53.4% vs 18.4% permuted) and skewed negative for material-index-0 meshes (−0.325 vs 0.007). Full-tier distribution-preserving test added.

## 2026-11-28 14:45:00 -0500 - GSC material preservation
- Verified converted GSC meshes keep a parseable material library with named materials (40/40); full-tier regression test added.

## 2026-11-28 14:15:00 -0500 - f0 index-0 threshold
- Found a sharp f0 half-delta threshold: index-0 meshes have 13.8% near-equal halves vs 61.5% for higher material indices. Full-tier distribution-preserving permutation test added.

## 2026-11-28 13:45:00 -0500 - f0 half-delta invariant
- Found f0's paired-half delta inversely tracks local material index (r -0.21 vs 0.004 permuted) in multi-material meshes. Full-tier permutation-controlled regression test added.

## 2026-11-28 13:15:00 -0500 - GTTF slot 44 packed signal
- Decoded remaining GTTF slots as signed 16-bit halves: slot +44 tracks path_f4 (median |r| 0.071 vs 0.013 permuted); others at chance. Full-tier permutation-controlled test added.

## 2026-11-28 12:45:00 -0500 - f0 material index baseline corrected
- A f0/material-index association was traced to a flawed permutation baseline (uniform instead of index-distribution-preserving); corrected baseline shows no signal. Probe discarded.

## 2026-11-28 12:15:00 -0500 - GTTF +8/+16 correlation corrected
- Re-examined the +8/+16 steering correlation: median |r| 0.675 across all frames collapses to 0.146 when +16's clamped frames are removed. Earlier "steering coupling" and sign-vs-heading claims are marked superseded; regression test now asserts the artifact.

## 2026-11-28 11:45:00 -0500 - GTTF path heading validation
- Path-record heading follows atan2(dx,dz) using its own x/z fields (median coherence 0.973 vs 0.086 permuted), independently confirming reconstructed world x. Full-tier regression test added.

## 2026-11-28 11:15:00 -0500 - f0 split accessors
- Added `gmt_format.split_f0()` and `gmt_tool.py info --meshes` f0 reporting; regression test added.

## 2026-11-28 10:45:00 -0500 - GTTF CLI fields
- The `--frames` CLI now reports reconstructed world position, engine speed, slot-48 channels and path control values; regression test added.

## 2026-11-28 10:15:00 -0500 - f0 halves family-stable
- Both f0 halves repeat across cross-corpus material families (16.3% / 17.3% vs 0.2% / 0.5% permuted), supporting paired authoring IDs. Full-tier permutation-controlled test added.

## 2026-11-28 09:45:00 -0500 - f0 shader registry negative
- Showed f0 halves cannot index the 94 shipped .psh/.vsh shaders (f0 spans >1,000 values) and stage-name hashes match at chance. Full-tier regression test added.

## 2026-11-28 09:15:00 -0500 - f0 packed halves
- Found f0's two u16 halves are nearly equal in 49.2% of 20,005 markers (vs 1.4% permuted; <=4 in 74.8%), indicating two closely related identifiers rather than one arbitrary number. Full-tier permutation-controlled test added.

## 2026-11-28 08:45:00 -0500 - GTTF +48 accessors
- Added `frame_slot48()` / frame fields `slot48_low` and `slot48_high` so the two packed signed channels are available to downstream tooling; regression test added.

## 2026-11-28 08:15:00 -0500 - GTTF +48 high half engine
- Found the high signed 16-bit half of slot +48 tracks engine +32 (median |r| 0.122 vs 0.021 permuted); +48 now reads as two packed signed control channels. Full-tier permutation-controlled test added.

## 2026-11-28 07:45:00 -0500 - path_f4 gear trend
- path_f4 decreases with gear index (median r -0.200 vs -0.005 permuted), supporting a throttle/demand interpretation on the reference racing line; path_f3 is not a brake flag. Full-tier permutation-controlled test added.

## 2026-11-28 07:15:00 -0500 - GTTF path control channels
- Exposed 24-byte racing-line record fields f3/f4 as frame attributes; f4 tracks engine +32 (|r| 0.502 vs 0.020 permuted), f3 tracks steering +8 (0.097 vs 0.015). Full-tier permutation-controlled test added.

## 2026-11-28 06:45:00 -0500 - GMT winding convention verified
- Verified that GSC, rF1 and GTR2 meshes all share inverted face winding vs stored normals (reversed agreement 1.0); conversion correctly preserves index order. Full-tier regression test added.

## 2026-11-28 06:15:00 -0500 - GTTF +36 AIW negative
- Slot +36 shows no relation to AIW waypoint galpha/width/index (median |r| ~0.01); session-time values remain an inference. Full-tier regression test added.

## 2026-11-28 05:45:00 -0500 - f0 archive scope negative
- Archive stem + material name set explains f0 in only 16.2% of groups (vs 28.7% for name set alone); f0 is not archive-scoped. Full-tier regression test added.

## 2026-11-28 05:15:00 -0500 - f0 shader-index hypothesis negated
- Disassembled GTR2.exe shader lookup helpers (fcn.005e54e0/005e55e0): they use a 1/2/3/99 stage-type enum, not f0; f0 has 4,364 distinct values in 20,005 samples. Full-tier regression test added.

## 2026-11-28 04:45:00 -0500 - GTTF +48 signed half
- Decoded slot +48 as two signed 16-bit fields: the low half tracks steering +8 at median |r| 0.503 vs 0.021 permuted (~24x). Units/sign remain unknown; full-tier permutation-controlled test added.

## 2026-11-28 04:15:00 -0500 - GSC EXE static trace blocked
- Documented that GSC-family EXEs are packer stubs (or retain loader strings without code xrefs), so static mesh-loader tracing is blocked; skip=4 validation remains empirical. Full-tier regression test added.

## 2026-11-28 03:45:00 -0500 - GTTF remaining slots study
- Permutation-controlled study of +40/+44/+48/+52/+56/+60 vs reconstructed speed/steering/engine: only +48 shows above-chance coupling to +8 (median |r| 0.193 vs 0.018 permuted); others at chance. Full-tier regression test added.

## 2026-11-28 03:15:00 -0500 - PHS runtime consumer negative
- Searched all 29 shipped GTL/GTR2 EXEs and DLLs (including unpacked GTL.exe) for PHS/PHYSICS strings in ASCII and UTF-16: zero matches. No runtime consumer found; full-tier regression test added.

## 2026-11-28 02:45:00 -0500 - f0 material association quantified
- Traced GTR2.exe GMT loader/shader fixup without finding an f0 assignment path; quantified f0 association with material identity (P(f0 equal|raw material equal)=0.347 vs 0.036 otherwise). Full-tier regression test added.

## 2026-11-28 02:15:00 -0500 - GTTF gear bands and +36 negative
- Using reconstructed world speeds, +32/speed clusters near F550 gear-ratio bands derived from .grb/.hdc/.tyr (p≈0.01 vs random bands); +36 is not path curvature (|r|<0.01). Two full-tier tests added.

## 2026-11-28 01:45:00 -0500 - GTTF heading convention resolved
- With world x reconstructed, ghost heading aligns with AIW x/z tangents as `atan2(dx,dz)` (median coherence 0.858 vs 0.404 previously). Full-tier regression test added.

## 2026-11-28 01:15:00 -0500 - GTTF missing x reconstructed
- Found the missing world x in the 24-byte pre-frame racing-line records (6th f32). `read_frames()` now exposes `x`/`world_position`; reconstructed speeds are plausible in all 29 ghosts (median 30 m/s vs 0.1 m/s before). Full-tier regression test added.

## 2026-11-28 00:45:00 -0500 - GSC conversion preserves vertex attributes
- `gmt_layout.old_to_new_semantic()` now copies original 32-byte vertex records instead of rebuilding them, so converted GTR2 meshes keep source f0 markers, normals and f7 colours. Normal-tier regression test added.

## 2026-11-28 00:15:00 -0500 - GTTF header fields from GTR2.exe code
- Recovered the GTTF/IRSR header field order from the unpacked `GTR2.exe` reader (`u8,u8,f32,u8,u32`) and exposed it on `EventFile`; the f32 is 10h/12h/13h in seconds across all 42 local event files. Full-tier regression test added.

## 2026-11-27 23:45:00 -0500 - Batch GSC conversion
- Added a `gsc` family to `batch_convert.py`: encrypted GSC MAS members are decoded and converted to verified GTR2 GMTs (8/8 in the full-tier regression run).

## 2026-11-27 23:30:00 -0500 - GSC to GTR2 mesh conversion
- Added `gmt_layout.gsc_member_to_gtr2()` and a `--gsc` CLI mode: encrypted GSC GMT members convert directly to GTR2-layout meshes with geometry preserved (150/150 sampled members, plus a 4-game normal-tier test).

## 2026-11-27 23:00:00 -0500 - GSC GMT geometry solved (ISI skip=4)
- **Major fix:** the long-standing "region-specific mask" blocker was caused by decrypting ISI-encrypted GSC GMT members with `skip=1`. With the correct `skip=4`, `gmt_semantic.decode_gsc_member()` yields full geometry (positions, indices, faces) on **150/150** sampled members across Automobilista, StockCarExtreme, GameStockCar and Copa Petrobras de Marcas. Added full-tier regression test and corrected the documentation; `decode_gsc_xor_gmt()` is retained only as a historical artifact path.

## 2026-11-26 16:30:00 -0500 - AIW Features capacity negative
- Documented that AIW `[Features]` numbers are capacity defaults rather than section counts (startinggrid 104 vs GRID 36 typical); full-tier corpus-fact regression test added.

## 2026-11-27 22:00:00 -0500 - GTTF heading vs AIW chain tangents
- Found above-chance alignment of ghost +12 with AIW pointer-chain tangents in the mapped y/z plane (median best coherence 0.404 vs ~0.05 permuted) across 27 ghosts; convention varies by track. Permutation-controlled full-tier test added.

## 2026-11-27 21:00:00 -0500 - GSC mask not metadata-derived
- Tested 120 masked GSC GMTs against member size/zsize/flags and compressed-byte CRCs/Adler/sums: all matches at permutation baseline. Full-tier regression test added.

## 2026-11-27 20:00:00 -0500 - GSC mask not name-derived
- Tested 120 masked GSC GMTs: magic/submesh XOR keys match member-basename hashes/length/first/last bytes only at chance level. Full-tier regression test added.

## 2026-11-27 19:00:00 -0500 - f0 raw-record hashes negative
- CRC32/Adler/FNV/MD5 over raw material and stage records match f0 halfwords only at chance level across 20,005 meshes. Full-tier regression test added.

## 2026-11-27 18:00:00 -0500 - f0 set-hash negative
- Tested sorted-concatenation CRC32/Adler/MD5 and XOR/sum of per-name CRC16 on 20,000 meshes: at most 4 matches to f0 halfwords, at chance level. The material-name group signal is not a simple set hash. Full-tier regression test added.

## 2026-11-27 17:00:00 -0500 - f0 material-name group signal
- Permutation-controlled test over 74,547 meshes found same-f0 meshes share rare normalized material/stage name hashes 60× above baseline (8.06% vs 0.13%), though no simple hash reproduces the halfwords. f0 groups by material identity; encoding still unknown. Full-tier regression test added.

## 2026-11-27 16:00:00 -0500 - GTTF +28 progress negative
- Matched ghost frames to AIW waypoints in the mapped y/z frame: slot +28 shows median |r| 0.035–0.08 with waypoint index/chain rank/lap distance. It is not lap progress. Full-tier regression test added.

## 2026-11-27 15:00:00 -0500 - GTTF +32 peak-power RPM negative
- Tested +32 ceilings against .eng peak-power RPM (6500 F550 / 8250 BMW): raw ratios 903.7 vs 768.1 differ by 15%, so no common engine-table RPM band explains the ceiling. Full-tier regression test added.

## 2026-11-27 14:00:00 -0500 - f0 counts/bbox negative
- Across 8,003 markers, f0 halfwords matching material/stage counts or bounding-box-derived values (1019) equal permutation chance (1057); no GMT-internal field explains the family-invariant marker. Full-tier regression test added.

## 2026-11-27 13:00:00 -0500 - SCE bounds vs GTR2 targets negative
- Cross-checked SCE embedded physics bounds with GTR2 `.hdc`/`.tyr` validators: 16/19 shared HDV keys and 11/15 shared TBC keys have incompatible ranges; adapter must rescale/use templates. Full-tier regression test added.

## 2026-11-27 12:00:00 -0500 - GTTF heading vs DSI tangent negative
- Recomputed DSI tangents in the mapped y/z frame: best per-file coherence with ghost +12 is only 0.318 median across 27 tracks, with no dominant convention. Full-tier regression test added.

## 2026-11-27 11:00:00 -0500 - GTTF +16 steering-rate negative
- Tested the +16 derivative across all 31 ghosts: median |correlation| 0.011 with +8 and 0.054 with heading rate — no steering-rate relationship. Full-tier regression test added.

## 2026-11-27 10:00:00 -0500 - GTTF +16 pedal comparison negative
- F550/M3 setups provide no 0..1 throttle/brake pedal ranges (only a blip value and mechanical settings), and +16 is negative in all 31 ghosts — not an unsigned pedal signal. Full-tier regression test added.

## 2026-11-27 09:00:00 -0500 - GTTF +16 steer-lock negative
- Both F550 and M3 .hdc setups imply a 15° (0.262 rad) steer lock; all 31 ghosts exceed it and 27 hit exactly 1.0, so +16 is not a raw steer angle. Full-tier regression test added.

## 2026-11-27 08:00:00 -0500 - GSC GMT alignment approach blocked
- Found zero same-name+same-size GMT pairs among 25,210 plain GTR2/GTL and 29,033 GSC members, so masked GSC meshes cannot be byte-aligned with plain counterparts to derive the bulk region mask. Full-tier regression test added.

## 2026-11-27 07:00:00 -0500 - GTTF steering vs DSI curvature
- Correlated ghost +16 with DSI instructor-line curvature across 27 matched tracks: median r −0.171, median |r| 0.241, 17/27 above 0.2 — modest curvature relationship supporting steering semantics, exact units/sign unresolved. Full-tier regression test added.

## 2026-11-27 06:00:00 -0500 - f0 stage-type matches refuted
- Showed that f0 halfwords matching stage types (478/3006) is a small-integer artifact: permutation baseline 434 vs 440 observed. No stage-derived f0 semantics; full-tier regression test added.

## 2026-11-27 05:00:00 -0500 - GTTF steering-sign vs heading trend
- Found the ± sign of the +8/+16 relation tracks net ghost heading trend (median 7.9 rad positive vs 4.74 rad negative; per-file r=0.583), while AIW waypoint order does not explain it. Full-tier regression test added; exact sign convention unresolved.

## 2026-11-27 04:00:00 -0500 - GTTF +8 tracks steering
- Detrended +8 and +16 on z/speed across 29 ghosts: median |correlation| 0.585 (24/29 >0.3), sign variable by track. +8 is steering/lateral-control-related; exact units/sign unresolved. Full-tier regression test added.

## 2026-11-27 03:00:00 -0500 - GTTF missing-x reconstruction negative
- Matched 773 Anderstorp ghost frames to DSI centerline points by y/z: +8 spans 1.56 m vs DSI x 685 m, with correlations −0.049 (x), 0.03 (z), −0.053 partial. No x reconstruction from +8; full-tier regression test added.

## 2026-11-27 02:00:00 -0500 - GTTF axes +0/+1 map to AIW y/z
- Matched 27 GTR2 ghosts to AIW waypoints: ghost +0 reproduces AIW y endpoints within 0.4 m median (27/27 within 10 m), +1 reproduces z within 6.6 m median (21/27 within 10 m). AIW x has no counterpart in the frame; full-tier regression test added.

## 2026-11-27 01:00:00 -0500 - GTTF frame +8 bounded field
- Verified frame +8 has a tightly bounded span (~1.66 m median) that does not match AIW elevation or lap progress, moderately smooth (lag-1 ~0.5); lateral-offset interpretation remains a hypothesis pending a coordinate transform. Full-tier regression test added.

## 2026-11-27 00:00:00 -0500 - GTL PHS reconstruction infeasible
- Enumerated PAR2 packets in all five PHS members: only three RecvSlic bodies (384,004 bytes each, exponents 53/58/59, slice size 384,000) versus ~160 slices needed for the 61 MB updater (~1.9% coverage) with exponents 0–52 absent; reconstruction is infeasible from local data. Regression test added.

## 2026-11-26 23:30:00 -0500 - GTTF position transform negative
- Fitted axis/scale/offset transforms of ghost positions to AIW waypoints (best median NN 10.3 m, no convincing fit) and found all 31 ghosts have one axis <2.71 m and one >307 m while AIW spans x≈685/y≈2/z≈395 m: ghost triples are track-local, not world XYZ. Full-tier regression test added.

## 2026-11-26 23:00:00 -0500 - GTTF position-scale blocker
- Found that position-derived speeds from GTTF frames are implausibly low in all 31 files (median of medians 0.53 m/s; all <2 m/s), so gear-ratio/wheel-speed cross-checks and AIW world-waypoint alignment cannot be performed from the +0/+4/+8 floats without a correct transform. Full-tier regression test added.

## 2026-11-26 22:00:00 -0500 - f0 material-derived hypotheses negated
- Tested 3,006 f0 markers against material offsets, stage-string offsets, name CRCs/sums and first-u16 words: only 2 chance matches (0.07%). f0 is family-invariant but not a direct GMT material offset/hash; full-tier regression test added.

## 2026-11-26 21:00:00 -0500 - f0 cross-corpus invariant
- Compared 703 identically named mesh families across GTR2Steam/GTLSteam/BMWM3Challenge: 42.4% share byte-identical f0 marker lists (vs 1.1% random), often differing only in mesh-0's marker. Added full-tier regression test; halfword encoding still unresolved.

## 2026-11-26 20:00:00 -0500 - GTR2 f0 LOD-family invariant
- Full-corpus sweep (500 GTR2/GTL meshes) found 29.7% of multi-mesh LOD families share identical f0 marker lists vs 0% random baseline; exact material-index matches remain <25%. Added full-tier regression test; encoding still unresolved.

## 2026-11-26 19:00:00 -0500 - GTTF heading vs AIW negative
- Cross-checked ghost `+12` heading against nearest AIW next-waypoint directions in all 29 GTR2 ghosts (3,606 samples): no coherent relation (R=0.026, median error 1.606 rad ≈ chance). Corrected the earlier single-sample cross-validation claim; full-tier regression test added.

## 2026-11-26 18:00:00 -0500 - GTTF /1024 scale negated
- Cross-checked the GTTF +32 ceilings with `.eng` rev limits: F550 7400 rpm vs BMW M3 8500 rpm give inconsistent raw/rev-limit factors (793.8 vs 745.5). The naive /1024 = RPM scale is negated; the signal stays engine-speed-like with unknown car-dependent normalization. Full-tier regression test and doc corrections.

## 2026-11-26 17:00:00 -0500 - SCE embedded numeric validators
- Derived 245 numeric bounds from the 131 embedded StockCarExtreme vehicle configs and added `validate_sce_embedded_config()` with family-specific sentinel keys; all 131 files pass. Full-tier regression test.

## 2026-11-26 16:00:00 -0500 - SCE embedded reference/vocabulary checks
- Parsed all 70 `.scn` files decoded from `StockCarExtreme/GSC.exe`: 543 MAS references all resolve (65 only via the EXE-embedded `AdPackStockcar.MAS`, with two capitalisations). Documented 131 embedded vehicle configs with family-specific vocabularies; added quick/full-tier regression tests.

## 2026-11-26 15:00:00 -0500 - StockCarExtreme EXE cipher solved
- Found the SCE `.keyMan` key schedule (type-1 resource *i* uses key `i + 11`; 204/204 valid LZMA headers) and added it to `gsc_exe_tool.py`; 207/218 SCE EXE resources now extract (`bolognahistoric.scn` → 212,880-byte `CUBEASF`). The prior "blocked" conclusion came from rejecting the valid LZMA props byte `0x5D`. Quick/full-tier regression tests.

## 2026-11-26 14:00:00 -0500 - GSC GMT decoder geometry caveat
- Corrected an overstatement: the XOR-masked GMT decoder restores file/submesh *structure* only — 0/150 sampled decodes had both plausible positions and faces. Added geometry-quality regression negative and updated decoder docs; no geometry should be used from these files without `read_gsc_geometry()` gating.

## 2026-11-26 13:00:00 -0500 - GTTF slots 48/52/56/60 negatives
- Verified sentinel-like full-range u32 values with no car-specific ceiling across all 31 files for slots +48/+52/+56/+60; +52's zero/sign clusters cover only ~17% of frames. Regression test added; no semantics promoted.

## 2026-11-26 12:00:00 -0500 - GTTF slot +44 car-independence
- Verified no car-specific ceiling or calibrated byte pattern in slot +44 across 31 files (all raw maxima >4.2B; byte44==byte46 fraction ~0.83 for both Ferrari and BMW); regression test added. No semantic promoted.

## 2026-11-26 11:00:00 -0500 - GTTF slot +7 car-independence
- Verified that slot +7's varying byte +31 has the same mode (0x40/0x41) and median (~64) for Ferrari F550 and BMW M3 files, with no car-specific invariant; regression test added. The exponent-artifact interpretation is corroborated; no semantic promoted.

## 2026-11-26 10:00:00 -0500 - GTTF slot +40 negative
- Verified across all 31 GTT files that slot +40 is not a counter or stable state (monotonic fraction ~0.56, time correlation ~0.025, cluster flips ~27% of frames); added raw accessor and regression test. No semantic promoted.

## 2026-11-26 09:00:00 -0500 - GTTF slot +36 quantized-float shape
- Verified that slot +36 is an exact quantized-float lattice (low 16 bits zero; mantissa high bits 8 or 12) in 98.5% of 47,239 frames, with a car-specific exponent shift; added detector and regression test. Physical semantics remain unresolved and earlier kinematic negatives stand.

## 2026-11-26 08:00:00 -0500 - GTTF slot +32 engine-speed evidence
- Found a car-specific ceiling in GTTF frame slot +32 (5,873,841 in 21/29 Ferrari F550 files, ~6.19M in BMW M3 files) with gear-shift-like drops; exposed as `frame_rpm()` / `read_frames()['rpm']` (≈5736/6190 at /1024). Ceiling and drops are regression-tested across all 31 GTT files; the interpretation remains labelled a hypothesis pending runtime confirmation.

## 2026-11-26 07:00:00 -0500 - Partial decoder for XOR-masked GSC GMTs
- Added `gmt_semantic.decode_gsc_xor_gmt()`: a magic-derived whole-file XOR mask now decodes 32/60 (Copa), 32/60 (GSC), 35/60 (SCE) and 39/60 (AMS) masked GMTs to real submesh geometry; region-specific-mask files remain blocked. Quick-tier regression test across four corpora.

## 2026-11-26 06:00:00 -0500 - Opaque GSC GMT headers are XOR-masked
- Refined the long-standing GMT blocker: 188/200 sampled opaque GSC GMTs carry the old-layout magic XORed with a constant byte; region-specific masks also reveal a `0x20004011` submesh header and a readable name/table in `PURCHASED.GMT`. Added deterministic detectors and a quick-tier regression test. No decoder is promoted — the mask schedule is still unknown.

## 2026-11-26 05:00:00 -0500 - Embedded physics numeric validators
- Added `validate_embedded_marcas_config()` with 174 corpus-derived numeric bounds and sentinel keys; all 17 EXE-embedded vehicle configs pass. Cross-check with GTR2 `.hdc`/`.tyr` bounds found incompatible ranges for 13/19 and 8/15 shared fields, documenting why direct name-based field copying cannot work. Quick-tier regression test.

## 2026-11-26 04:00:00 -0500 - Embedded vehicle physics corpus
- Decoded all 17 vehicle config resources embedded in `Marcas.exe` (`.hdv/.gen/.tbc/.pm/.sfx`), none of which have loose copies; documented their stable key vocabularies and added a quick-tier regression test.

## 2026-11-26 03:00:00 -0500 - Embedded SCN reference invariant
- Verified that all 6 `.scn` scripts embedded in `Marcas.exe` parse with the existing parser and contain 45 MAS references; the only references missing from loose game files point to `AdPackStockCar.MAS`, which exists solely as an EXE-embedded resource. Quick-tier regression test added.

## 2026-11-26 02:00:00 -0500 - GSC EXE embedded resources decoded
- Added `gsc_exe_tool.py` to list/extract resources embedded in GSC-family EXEs (`AXS.GS.0`): `.keyMan` GUID keys, Blowfish-CBC decryption, LZMA/LZ4 decompression. Verified against QuickBMS: 34/35 Marcas files and 626/627 AMS files byte-identical; StockCarExtreme's variant remains unsupported by both tools. New quick-tier and full-tier tests; mirror script documented in `docs/tools-reference.md`.

## 2026-11-26 01:00:00 -0500 - Decrypted config invariants
- Surveyed all 26 distinct decrypted gM configs and added `validate_decrypted_gm_config()`: 8 rFactor setups share 15 universal keys with tight gear/aero bounds; 18 GTR-family configs have per-family vocabularies and 24 bounded chassis/brake fields. Full-tier regression test, targeted run 1 s.

## 2026-11-26 00:30:00 -0500 - Full tool-mirror accounting; JCA cross-check
- Completed a full accounting of `../aluigi-mirror-261124/`: 4,405 files / 189.7 MiB indexed in `docs/aluigi-mirror-manifest.tsv` and 461 ZIPs in `docs/aluigi-mirror-archives.tsv`; HTML tool descriptions and techniques documented in `docs/tools-reference.md`. Cross-checked `jca_crypt.py`/`jca_tables.py` against wtcced 0.3.5 (magic, XOR byte, keys, version mapping, 3,090 identical Blowfish constants) with a regression test.

## 2026-11-25 23:30:00 -0500 - Encrypted ISI configs decrypted; tool mirrors indexed
- **Solved the encrypted `.svm` and gMb1.002f backlog**: added `isi_gm_crypt.py` implementing the rfactorgmdec stream cipher with documented game keynums; all 10 encrypted `.svm` files and all 18 gMb1.002f configs now decode to 100% printable text. Full-tier regression test over every encrypted file.
- Indexed `../aluigi-mirror-261124/` (202M/4,405 files), `../quickbms-mirror/` (99M/1,025 files) and `../gtl-tools/` in new `docs/tools-reference.md`, plus `DEPENDENCIES.md`/`AGENTS.md`/`docs/corpus-reference.md`. Confirmed GTL's gMb 'Encryptomatic' cipher is distinct from rfactorgmdec and does not decrypt our files (nor vice versa).

## 2026-11-26 16:00:00 -0500 - AIW TELEPORT validator
- Added `simbin_text_tool.validate_aiw_teleport()` covering index uniqueness, contiguous main runs, and optional pit-box indices >=100 across 447 AIWs. Full-tier regression test added.

## 2026-11-26 15:30:00 -0500 - AIW GRID/PITS validator
- Added `simbin_text_tool.validate_aiw_grid_pits()` with GRID index/position parity and 2×/3× garage-to-pit ratios across 465 AIWs; documented single Brianza TeamIndex exception. Full-tier regression test added.

## 2026-11-26 15:00:00 -0500 - GDB texture-reference negative
- Documented that 252 GTR2/GTL/Race07 event GDB files contain no sky/texture/image references (Weather is a numeric 0–4 index). Full-tier corpus-fact regression test added.

## 2026-11-26 14:30:00 -0500 - GDB race-setting bounds
- Added `simbin_text_tool.validate_gdb_numeric()` with 17 corpus-observed race-setting bounds across 252 GTR2/GTL/Race07 event files. Full-tier regression test added.

## 2026-11-26 14:00:00 -0500 - TRK view-field validator
- Added `simbin_text_tool.validate_trk_view_fields()` with FOV/clip/color/size bounds and TRUE/FALSE Clear validation across 152 GTR2/GTL/Race07 track scripts. Full-tier regression test added.

## 2026-11-26 13:30:00 -0500 - ANM bone-name negative
- Documented that 13,005 ANM bone names across 904 archived animations resolve to mesh member names only twice (chance level); full-tier corpus-fact regression test added.

## 2026-11-26 13:00:00 -0500 - TDF surface bounds
- Added `simbin_text_tool.validate_tdf_numeric()` with 17 surface grip/bump bounds from 203 local `.tdf` files. Full-tier regression test added.

## 2026-11-26 12:30:00 -0500 - CAM numeric bounds
- Added `simbin_text_tool.validate_cam_numeric()` with 14 corpus-observed field bounds across 258 GTR2/GTL/Race07 `.cam` files. Full-tier regression test added.

## 2026-11-26 12:00:00 -0500 - RCD numeric bounds
- Added `simbin_text_tool.validate_rcd_numeric()` with 19 driver-stat bounds over 3,310 local `.rcd` files; widened envelopes to include generated/modded values. Full-tier regression test added.

## 2026-11-26 11:30:00 -0500 - CAM ControlPoint negative
- Added `parse_cam_control_points()` and documented that 290 ControlPoint coordinates in GTR2/GTL/Race07 CAM files are camera-path spline nodes, not AIW waypoint references. Full-tier corpus-fact regression test added.

## 2026-11-26 11:00:00 -0500 - GEN mesh-config validator
- Added `simbin_text_tool.validate_gen_numeric()` for LOD distance ranges and ReflectPlane unit/zero-fourth invariants across 272 rF1-era `.gen` files; documented that SimBin installs ship none. Full-tier regression test added.

## 2026-11-26 10:30:00 -0500 - VEH key/eyepoint validator
- Added `simbin_text_tool.validate_veh_numeric()` covering seven universal keys and Eyepoint vector bounds across 371 rF1-era `.veh` files. Full-tier regression test added.

## 2026-11-26 10:00:00 -0500 - WAV chunk validator
- Added `media_tool.wav_chunks()` and `validate_wav_chunks()` for fmt-first, single-data, known-trailing-chunk validation across four corpora; handled odd-sized final chunks without pad byte and `cue ` chunks. Full-tier regression test added.

## 2026-11-26 09:30:00 -0500 - AIW event/checkpoint validator
- Added WP_EVENT first-component parsing and `validate_aiw_event()` covering 198,932 SimBin event records and WP_SCORE checkpoints across 465 AIWs; documented garbage bit patterns in the other event fields. Full-tier regression test added.

## 2026-11-26 09:00:00 -0500 - AIW path/perp validator
- Added WP_PATH parsing and `validate_aiw_path_perp()` with corpus-observed bounds and unit-or-zero perpendicular invariant across 465 AIWs; one legacy outlier documented. Full-tier regression test added.

## 2026-11-26 08:30:00 -0500 - AIW dwidth/groove validator
- Added WP_DWIDTH/WP_GROOVE_LAT parsing and `validate_aiw_dwidth_groove()` with corpus-observed bounds; one corrupt StockCarExtreme file exempted. Full-tier regression test over 465 AIWs.

## 2026-11-26 08:00:00 -0500 - AIW width/groove validator
- Added WP_WIDTH/WP_GALPHA parsing to `parse_aiw()` and `validate_aiw_width_galpha()` with corpus-observed bounds; documented packed legacy GALPHA values in rF1Vanilla/F1 2002 as an explicit exception. Full-tier regression test over 465 AIWs.

## 2026-11-26 07:30:00 -0500 - HED head-physics validator
- Added `simbin_text_tool.validate_hed_numeric()` covering vector ordering and component bounds for the two shipped GTR2/GTL `.hed` files. Full-tier regression test added.

## 2026-11-26 07:00:00 -0500 - ENG/GRB bounds and AUD envelope fix
- Added `validate_eng_numeric()` (12 fields, 66 GTR2/GTL `.eng` files) and `validate_grb_numeric()` (ratio/bevel, 60 `.grb` files). Widened `AUD_NUMERIC_BOUNDS` to the full corpus envelope after Full v114 exposed modded `.aud` values outside the initial four-corpus ranges. Full-tier tests green.

## 2026-11-26 06:30:00 -0500 - HDC numeric bounds
- Added `simbin_text_tool.validate_hdc_numeric()` with 20 corpus-observed chassis/suspension/brake field bounds from 86 GTR2/GTL `.hdc` files. Full-tier regression test added.

## 2026-11-26 06:00:00 -0500 - TYR numeric bounds
- Added `simbin_text_tool.validate_tyr_numeric()` with 18 corpus-observed field bounds from 41 GTR2/GTL tire files; documented near-zero non-zero constants and added a full-tier regression test.

## 2026-11-26 05:30:00 -0500 - AUD numeric event bounds
- Extended `validate_aud_map()` with `AUD_NUMERIC_BOUNDS` for 20 high-frequency numeric keys, derived from all 202 GTR2/GTL/Race07/Volvo `.aud` maps. Full-tier regression test added.

## 2026-11-26 05:00:00 -0500 - SVM numeric bounds
- Added `simbin_text_tool.validate_svm_numeric()` with corpus-observed inclusive bounds for 11 high-frequency setup keys; verified on all 21,183 plain `.svm` files with encrypted payloads skipped. Full-tier regression test added.

## 2026-11-26 04:30:00 -0500 - TRK/CAM namespace negative
- Documented that TRK `View=`/`Instance=` names never match `.cam` camera names across 152 track scripts (288 and 135,196 references respectively). Full-tier corpus-fact regression test added.

## 2026-11-26 04:00:00 -0500 - AIW camera-reference negative
- Documented that no AIW in the eight validated corpora (465 files) contains ControlPoint/camera references; camera data is in .cam/.trk formats. Full-tier corpus-fact regression test added.

## 2026-11-26 03:30:00 -0500 - GDB terrain data references
- Added `parse_gdb_terrain_refs()` and a full-tier test: 26/26 RF1Vanilla `TerrainDataFile` references resolve to local `.tdf` files; F1C/F12002/NT2003 contain no such keys.

## 2026-11-26 03:00:00 -0500 - WAV header validator
- Added `media_tool.wav_header()` and `validate_wav_header()` with JCA key support (Volvo requires `volvo`). Corpus-verified PCM consistency across four installs; documented MPEG-in-WAVE (0x55) files as out of scope. Full-tier regression test added.

## 2026-11-26 02:30:00 -0500 - SCR actor references and GTL.exe RE
- Added `parse_scr_move()` and a full-tier test: 1,177/1,177 SCR actor refs and 1,160/1,160 Parent refs resolve; animation tokens are internal mesh sequences, not `.anm` files. Documented a GTL.exe reverse-engineering pass: no PHS strings, no PHS extension dispatch, and all inline byte hits are coincidences — no PHS-specific loader exists in the binaries.

## 2026-11-26 02:00:00 -0500 - rF1 GDB format boundary
- Documented that rF1-era GDBs have no SimBin class-filter sections; their 154 `Filter Properties` tokens do not match `.veh`/`.hdv` class tags. Full-tier corpus-fact test added; no cross-era class validator promoted.

## 2026-11-26 01:30:00 -0500 - GDB SpecialClasses resolution
- Added `parse_gdb_class_blocks()` and a full-tier test: 112/117 SpecialClasses keys resolve to local `.car` tags; five misses confined to one Race07 DLC event file. Documented alongside the existing GDB filter-class check.

## 2026-11-26 01:00:00 -0500 - GDB filter class resolution
- Added `parse_gdb_filter_tags()` and `car_class_tags()` with a full-tier test: 163/166 event filter tags resolve to local `.car` class declarations across 252 GTR2/GTL/Race07 GDB files. Three missing class tags documented as content gaps.

## 2026-11-26 00:30:00 -0500 - SCN reference resolution
- Corpus-verified 131/132 `.scn` MASFile references resolving across four rF1-era corpora and documented 13/83 SearchPath resolution (stale NT2003 Season03 paths). Full-tier regression test added.

## 2026-11-26 00:00:00 -0500 - TRK reference resolution
- Added `simbin_text_tool.parse_trk_refs()` and a full-tier test: 293/293 MASFile and 140,120/140,123 MeshFile references resolve across 152 GTR2/GTL/Race07 track scripts; three missing Race07 crowd-mesh references documented.

## 2026-11-25 23:30:00 -0500 - AIW lap-distance coherence
- Added `score_distance` parsing for `WP_SCORE` and `simbin_text_tool.aiw_lap_distance_coherence()`. Corpus-verified on 464 AIWs: 99.86% of adjacent class-0 lap-distance pairs are non-decreasing within contiguous runs; full-tier regression test. Documented as calibrated evidence rather than a strict ordering rule.

## 2026-11-25 23:00:00 -0500 - CAM radius invariant
- Extended `simbin_text_tool.validate_cam()` to require positive-integer `ActivationRadius`, corpus-verified on 1,153 GTR2/GTL/Race07 cameras. Documented that radius is not a camera-centred trigger sphere (only 1% within radius); full-tier regression test added.

## 2026-11-25 22:30:00 -0500 - Scene script reference probe
- Corpus-verified 1,127/1,321 rF1-era `.scr` Mesh references (85.3%) resolving to archive members across seven corpora, with missing pit-crew wheel variants documented. GTR2/GTL/Race07Complete have no `.cin`/`.scr` files. Full-tier regression test added.

## 2026-11-25 22:00:00 -0500 - Full-corpus batch conversion
- Ran `batch_convert.py --limit 0` over both source corpora: 48,108 verified GMTs written (13,292/13,293 VRL; 34,816/36,128 GTR1). Fixed VRL vertex-map inclusive boundary (max == M) and decoded GTR1 descriptor indices as triangle strips, then documented all remaining skips as degenerate/placeholder content (`TB*.GMT`, one `FNCE02.VRL`, 3 source-less meshes). Full-tier suite still green.

## 2026-11-25 21:30:00 -0500 - Descriptor-less GTR1 conversion fallback
- Extended `gtr1_to_gmt.geometry_from_gtr1()` to convert descriptor-less shadow/LOD meshes via their object-mesh streams (NaN sentinel position components zeroed to preserve topology). Batch conversion at 100 members per family now writes 200/200 verified GMTs with zero skips; full-tier regression test added.

## 2026-11-25 21:00:00 -0500 - Batch mesh archive conversion
- Added `batch_convert.py`: walks SCGT/GTR1 archives, converts all decodable meshes with the dedicated converters, re-parses and material-checks every output, and writes only verified GMTs to an explicit output directory. `--limit` supports bounded runs; full-tier regression test over 8 members per family.

## 2026-11-25 20:30:00 -0500 - SCGT text .ani parser
- Added `simbin_text_tool.parse_ani_text()` and `validate_ani_text()` for SCGT's CRLF text animation-rule format (distinct from binary ANM). Corpus-verified on the single shipped `.ani` member: 12 rule blocks with matching frame counts, in-range sequences, positive rates and known methods. Full-tier regression test added.

## 2026-11-25 20:00:00 -0500 - SCGT .prt validator
- Added `simbin_text_tool.validate_prt()` with a full-tier regression test over all 5 Sports Car GT `.prt` members (CRLF ASCII, balanced braces, key/value lines). Documented that none of their 977 ObjFile object names resolve to shipped content.

## 2026-11-25 19:30:00 -0500 - GTR2 f0 per-mesh marker
- Characterized GTR2 base-vertex f0 as a per-mesh marker: across 15.6M vertices, 71,547 nonzero values occur exactly once per mesh, always on vertex 0. Added `gmt_format.mesh_marker()` and a full-tier regression test; the packed halfword semantics remain unresolved (ruled out as material index, mesh ordinal, UV or color).

## 2026-11-25 19:00:00 -0500 - GTR2 vertex color field decoded
- Identified GTR2 base-vertex f7 as a packed color word (alpha 255, grayscale in 11,841/11,841 sampled vertices across 40 meshes) and added `gmt_format.unpack_vertex_color()` with a full-tier regression test. Confirmed f7 is not a packed UV pair; f0 remains unresolved.

## 2026-11-25 18:30:00 -0500 - Converter output material validation
- Both VRL→GMT and GTR1→GMT round-trip tests now also run `validate_materials.check_gmt()` on converted output (clean). Documented that `validate_conversion.independent_read()` targets the old-layout submesh format and does not apply to new-layout GTR2 output.

## 2026-11-25 18:00:00 -0500 - GTR1 to GTR2 GMT conversion
- Added `gtr1_to_gmt.py`, built on the shared `vrl_to_gmt.build_gmt()` writer: merges GTR1 third-magic descriptor submeshes into one GTR2 mesh with corpus-verified positions/normals and rebased triangles. Output is re-parsed and verified; full-tier round-trip test over 25 GTR1 GMTs. UV-like fields remain untransferred.

## 2026-11-25 17:30:00 -0500 - VRL to GTR2 GMT conversion
- Added `vrl_to_gmt.py`: converts decoded SCGT `.vrl` meshes to GTR2-layout GMTs using an in-memory real GTR2 GMT as a structural template. Positions from VRL 16-byte records (4th field zero in 300/300 files), normals computed from triangulated geometry, indices as u16. Output is re-parsed and verified; full-tier round-trip test over 25 VRL meshes. UV-like coordinates are not transferred because packed UV field semantics remain unconfirmed.

## 2026-11-25 17:00:00 -0500 - More rF1-era reference non-applicability
- Documented that LexusIsfTrackTime and SimuladorTopRace2009 have no `.aud`/`.car` files (media-only archives, loose WAVs, encrypted TR2009 configs). Extended the full-tier corpus-fact test to cover four installs.

## 2026-11-25 16:30:00 -0500 - NASCAR-era reference non-applicability
- Documented that NascarSimRacing and NT2003 have no `.aud`/`.car` files (audio is loose WAV plus `.djs`; configs are `.veh`/`.hdv`). Added a full-tier corpus-fact test; no reference validator applies.

## 2026-11-25 16:00:00 -0500 - Superleague reference non-applicability
- Documented that Superleague Formula 2009 has no `.aud`/`.car` files: 101 loose WAVs plus 5 MP3s, and opaque `gMb1.002f` encrypted vehicle configs. Added a full-tier corpus-fact test; no reference validator applies.

## 2026-11-25 15:30:00 -0500 - TC2000 reference-resolution non-applicability
- Documented that TC2000 has no `.aud`/`.car` files: its 34 MAS archives hold 189 MP3 audio members and its configs are opaque `gMb1.002f` encrypted files. Added a full-tier corpus-fact test; no reference validator applies.

## 2026-11-25 15:00:00 -0500 - BMW M3 Challenge reference resolution
- Corpus-verified 186/190 `.aud` WAV refs (four `raex.wav` references absent) and 51/51 `.car` config refs in BMW M3 Challenge; its 17 `.bmw` archives hold only media. Full-tier regression test added.

## 2026-11-25 14:30:00 -0500 - AIW validation across eight corpora
- Extended AIW pointer/path validation to RF1Vanilla, Automobilista, StockCarExtreme and F1 2002: 457,832 waypoints across 465 files now pass. Documented a third stricter-validator exception (`Lienz_24H.AIW`, non-unit `wp_perp`) and that F1 Challenge ships no AIWs. Full-tier regression test updated.

## 2026-11-25 14:00:00 -0500 - AIW pointer validator extended
- Extended `validate_aiw_pointers()` to GTR2Steam and Race07Complete: corpus-verified on 201,855 waypoints across 193 AIWs. Pointer -1 is treated as a documented "no link" sentinel (7 occurrences confined to addon track `Hill.AIW`); two malformed addon tracks remain flagged by the stricter waypoint validator. Full-tier regression test updated.

## 2026-11-25 13:30:00 -0500 - AIW waypoint pointer validator
- Added `simbin_text_tool.validate_aiw_pointers()` and `wp_path` parsing. Corpus-verified on 64,766 waypoints across 66 Race07Vanilla/GTLSteam AIWs: previous/next pointers always in range, third pointer -1 or in range, and all `wp_path` offsets finite with |value| < 100. Full-tier regression test added.

## 2026-11-25 13:00:00 -0500 - Race07Vanilla reference resolution
- Corpus-verified all 43 JCA-wrapped `.aud` files have 4,783/4,830 WAV refs (99.0%) resolving locally (47 missing Caterham basenames), and all 335 JCA-wrapped `.car` files have 262/262 config refs resolving. Full-tier regression test added.

## 2026-11-25 12:30:00 -0500 - Volvo .car/.aud reference resolution
- Corpus-verified all VolvoTheGame configs decrypt with the non-default `volvo` JCA key: 453/483 `.aud` WAV refs (93.8%) resolve, with 10 missing C30 audio basenames; 16/16 `.car` `Include=..\*.inccar` references resolve. Full-tier regression test added.

## 2026-11-25 12:00:00 -0500 - Race07Complete .car reference resolution
- Corpus-verified all 823 Race07Complete `.car` files (621 JCA-encrypted) with 262/262 HDVehicle/Graphics/Sounds/Camera references resolving locally. Documented that the 114 `.gdb` files have no active path references. Full-tier regression tests added.

## 2026-11-25 11:30:00 -0500 - Race07Complete .aud reference resolution
- Corpus-verified all 137 Race07Complete `.aud` files (101 JCA-encrypted) parse cleanly and 7,147/7,264 WAV references (98.4%) resolve locally; 43 missing basenames are DLC/shared-file gaps. Full-tier regression test added.

## 2026-11-25 11:00:00 -0500 - Opaque GSC GMT header marker
- Added `gmt_semantic.opaque_gsc_flags()` with a corpus-verified header marker at +4 (`0x04000020`, `0x20` or `0` in 782/800 opaque GSC GMTs) and a full-tier regression test. Documented that member lengths show no fixed-record alignment, so no size-based framing decoder follows.

## 2026-11-25 10:30:00 -0500 - GTR1 triangle-coherence probe
- Added `gmt_semantic.gtr1_triangle_coherence()` with corpus-calibrated evidence that GTR1 vertex fields 1–3 are spatially coherent (adjacent/random distance median 0.439 across 400 descriptors vs 0.803 for fields 9–11). Full-tier regression test added; semantics remain an inference rather than a strict position label.

## 2026-11-25 10:00:00 -0500 - VRL UV-like coordinate score
- Added `simbin_text_tool.vrl_uv_quad_score()` with corpus-calibrated evidence that decoded `.vrl` coordinate arrays behave as per-corner texture coordinates (quad-corner reuse 0.753 vs 0.271 shuffled baseline across 1,046 files). Full-tier regression test added; semantics remain an inference rather than a strict decoder claim.

## 2026-11-25 09:40:00 -0500 - GTR1 vertex normals identified
- Corpus-confirmed vertex fields 4–6 of GTR1 third-magic GMTs as unit normals (20,164/20,164 finite records) and exposed them as `normals` in `read_gtr1_geometry()`, with a unit-length validator check and full-tier regression test. Remaining vertex fields are still unclassified.

## 2026-11-25 09:20:00 -0500 - GTR1 descriptor geometry decoder
- Added `gmt_semantic.read_gtr1_geometry()` and `validate_gtr1_geometry()`: decodes GTR1 third-magic GMT descriptor vertex records and u16 index lists. Corpus-verified on 600 descriptors (indices in range) and 4,467 sampled vertex records (fields 0–3/8–11 finite and bounded); full-tier regression test. Vertex field semantics remain unconfirmed.

## 2026-11-25 09:00:00 -0500 - SimBin encrypted-config family identified
- Added `media_tool.gmb_encrypted_config()` to identify `gMb1.00xx` encrypted-config headers and flag high-entropy payloads; corpus-verified on 19 `gMb1.002f` files across TC2000/TR2009/Superleague with a full-tier regression test. Documented fresh TR2009 `.hdv` negatives (header field is not an ISI signature; raw ISI/JCA, compression and known-plaintext keystreams all fail). No decoder promoted.

## 2026-11-25 08:40:00 -0500 - HDR pair bounds validator
- Added `media_tool.validate_hdr_dat_pair()` enforcing corpus-verified bounds on all 1,982 NASCAR `.hdr`/`.dat` pairs (header alignment/size, block count fits payload) with a full-tier regression test. Documented that the remaining header fields are category flags, not data offsets (only 1.8% chance-level sync hits; 789/829 nonzero +12 values out of bounds).

## 2026-11-25 08:20:00 -0500 - SCGT .vrl flag and group blocks decoded
- Extended `simbin_text_tool.read_vrl()` with the 13 consecutive N*4 blocks: eight zero blocks, one constant-15 block, two zero blocks, a sorted vertex map (< M) and small per-vertex group IDs (<256). Corpus-verified on 3,000/3,000 members with two documented `CONE10.VRL` exceptions; full-tier regression test added.

## 2026-11-25 08:00:00 -0500 - SCGT .vrl index and coordinate arrays decoded
- Extended `simbin_text_tool.read_vrl()` to expose the M u32 vertex-index buffer and two M-float coordinate arrays. Corpus-verified: indices below vertex count and coordinates finite/bounded on 3,000/3,000 members; full-tier regression test. Corrected the earlier note that these sections were "not vertex indices" — that conclusion came from sampling the preceding N*4 flags block.

## 2026-11-25 07:45:00 -0500 - SCGT .vrl header/vertex decoder
- Added `simbin_text_tool.read_vrl()`: decodes the corpus-verified 24-u32 header table and N x 16-byte vertex block of Sports Car GT `.vrl` meshes. Verified arithmetic on 4,000/4,000 files and plausible vertices on 2,000/2,000; full-tier regression test. Section payloads are documented as undecoded (426/2,000 files have out-of-range u32 values, not vertex indices).

## 2026-11-25 07:30:00 -0500 - SCGT .vrl structural validator
- Added `simbin_text_tool.validate_vrl()` with corpus-verified invariants for 1,500 Sports Car GT `.vrl` members: 60-byte zero header and valid first u32 offset at +60. Deeper mesh tables remain undocumented. Full-tier regression test added.

## 2026-11-25 07:15:00 -0500 - ANM keyframe validator
- Added `anm_format.validate_anm()` with corpus-verified invariants: per-bone monotonic key times (excluding the trailing time=0 sentinel) and unit quaternions, 0 problems across 236 F1C/F12002 files. Full-tier regression test added.

## 2026-11-25 07:00:00 -0500 - Full GSC GMT survey complete
- Completed the incremental `gsc_survey.py` survey over all 29,033 GMT members in 352 MAS archives from the four GSC corpora: 29,022 GSC-signature, 1,096 decodable (3.8%), 1,003 with submeshes, 904 finite / 414 plausible. Cache reached full coverage over 15 bounded runs with 100% cached-hit reuse.

## 2026-11-25 06:45:00 -0500 - Incremental GSC classification cache
- Added lazy MAS member reads (`read_member`, `read_archive(read_data=False)`) and `gsc_survey.py` with a persistent archive+member classification cache in gitignored `.cache/`. Quick/normal/full modes bound runtime; verified 200→400→2,260 cache growth with 100% cached-hit reuse. Added a regression test.

## 2026-11-25 06:30:00 -0500 - GSC geometry validated at scale
- Applied `is_gsc_decodable()` + `read_gsc_geometry()` across 1,969 GMT members in 155 archives from Automobilista/StockCarExtreme/GameStockCar/Copa: 53 decodable (2.7%), 48 finite / 22 plausible, 76 UV==vertex submeshes, 62 in-range face sets — all invariants held. Full-corpus scan of huge archives is time-limited; small/medium archives covered.

## 2026-11-25 06:15:00 -0500 - GTR1 descriptor corpus validation
- Corpus-verified 132 GTR1 third-magic GMT descriptors across 60 files have plausible counts/offsets; full-tier regression test added. Also recorded the PHS sibling-XOR negative (no PAR2 magic or entropy reduction).

## 2026-11-25 06:00:00 -0500 - GSC geometry invariants validated
- Corpus-validated decoded GSC GMT geometry: UV count equals vertex count (23/23 submeshes) and all face indices are in range (15/15). Quality flags separate plausible from degenerate geometry. Full-tier regression test added.

## 2026-11-25 05:45:00 -0500 - GSC GMT geometry decoder
- Added `gmt_semantic.read_gsc_geometry()` for the ~5% decodable GSC GMTs: extracts vertices/UVs/faces from the 0x2e4 old-layout submesh headers with a quality flag. Corpus-verified on 18 files (16 finite, 11 plausible, 12 with faces). Full-tier regression test added.

## 2026-11-25 05:30:00 -0500 - GSC GMT decodability pre-filter
- Added `gmt_semantic.is_gsc_decodable()` using the 0x1D4 near-magic to pre-filter ISI-decrypted GSC GMTs before full submesh scans: 100% recall, 99.5% specificity on a 200-file four-corpus sample. Full-tier regression test added.

## 2026-11-25 05:15:00 -0500 - .car reference resolution verified
- Extended reference-resolution checks to `.car` configs: GTL 288/288 HDVehicle/Graphics/Sounds references resolve; GTR2 419/435 (16 alternate livery `.cas` files absent by design). Full-tier regression test added.

## 2026-11-25 05:00:00 -0500 - .aud WAV reference resolution verified
- Corpus-verified that all WAV path references in vanilla GTR2/GTL `.aud` files resolve to local WAV basenames (1,094/1,094 and 1,374/1,374); Race07/Race07Vanilla 98%, Volvo 85%. Full-tier regression test added.

## 2026-11-25 04:45:00 -0500 - GTTF steering field decoded
- Breakthrough: GTTF frame offset +16 is **steering**, not pitch — bounded [-1,1] in all 29 files (matching `mUnfilteredSteering` from ccgepmonitor/rF2 runtime headers) and correlated with heading rate in most files (median r=0.628). `read_frames()` now exposes `steering` (legacy `pitch` alias preserved). Added a corpus regression test.

## 2026-11-25 04:30:00 -0500 - Lexus config corpus validation
- Corpus-verified LexusIsfTrackTime configs: 11 `.veh` (27 universal keys), 5 `.scn`, 5 `.cam` all parse with existing rules; full-tier regression test added.

## 2026-11-25 04:15:00 -0500 - RaceRoom FXM corpus validation
- Corpus-verified all 91 RaceRoom `.fxm`/`.fxa`/`.lma` files decode with existing parsers and the 1/3 `key_count` invariant (3,114 nodes). Added a full-tier regression test.

## 2026-11-25 04:00:00 -0500 - Split corpus-deep test module
- Split the 19-test / ~120 s full-only `test_corpus_deep.py` into two modules for balance; all 19 tests pass. Full tier is now 52 modules / 423 tests.

## 2026-11-25 03:45:00 -0500 - .rfm mod descriptor parser
- Added `parse_rfm()`/`validate_rfm()` for all 10 rF1 mod descriptors (37 universal keys, 0 problems) and `rfactor-rfm` identification. Full-tier regression test added.

## 2026-11-25 03:30:00 -0500 - RaceRoom shader decryption and identification
- Added `media_tool.decrypt_jca_shader()` and `shader-jca` identification for all 226 RaceRoom `.vsh`/`.gfx`/`.psh` files (JCA v1, volvo key); these decrypt to ISI HLSL/PS1.1 source with no `=` so the text detector misses them. Full-tier corpus regression test added.

## 2026-11-25 03:15:00 -0500 - .rcs control sets and UTF-16 .dic fix
- Added `parse_rcs()`/`validate_rcs()` for 36 RaceRoom control-set configs (5 universal keys) and fixed `identify()` misclassifying UTF-16LE `.dic` files as MP3 (ff fe BOM matched an MP3 sync) — now `utf16-text`. Added a full-tier regression test.

## 2026-11-25 03:00:00 -0500 - .tdf terrain config parser
- Added `simbin_text_tool.parse_tdf()`/`validate_tdf()` for all 57 rF1 terrain-definition files: 12 universal keys and 3 sections (trackvars/feedback/loose), 0 validation problems. `media_tool.identify()` reports `rfactor-tdf`. Added a full-tier regression test.

## 2026-11-25 02:45:00 -0500 - TC2000/Superleague rF1 config validators
- Added `validate_rf1_config()` with corpus-verified universal key sets shared across TC2000 and Superleague: `.gdb` 28 keys, `.cam` 10, `.aiw` 70 (plus 7 universal sections). 0 validation problems across 95 files; full-tier regression test added.

## 2026-11-25 02:30:00 -0500 - TC2000/Superleague config family validators
- Added `validate_veh_core()` / `validate_svm_tc2000()` corpus-verified key sets: TC2000 `.veh` 26/26 keys universal (36 files), Superleague `.veh` 22 universal (19 files), TC2000 `.svm` 15 universal 6-speed keys (12 files), all 0 validation problems. Added a full-tier regression test.

## 2026-11-25 02:00:00 -0500 - Superleague IRSR prefix variant
- Extended `parse_rf1_metadata()` to accept the `ffff` prefix variant found in 5/6 Superleague Formula 2009 `.Vcr` replays; all 6 now parse driver and car names. Added a full-tier corpus regression test.

## 2026-11-25 01:45:00 -0500 - Expanded corpus review and test fixes
- Reviewed five new ISIMotor-era folders (RaceRoomTheGame 1/2, LexusIsfTrackTime, TC2000, SimuladorTopRace2009) plus SuperleagueFormula2009; documented in `AGENTS.md`/`docs/corpus-reference.md`. Added `volvo`-key JCA detection for RaceRoom GMTs (`gmt-jca`), a 12-key "talent" `.rcd` family, and relaxed exact-count corpus assertions to withstand expanded corpora. Normal suite: 220 tests, 0 failures.

## 2026-11-25 01:30:00 -0500 - rF1 .svm setup detector
- Added `gtl_to_gtr2.validate_svm_setup()` / `rf1_svm_paths()` to flag unconverted rF1-style car setups in GTR2 trees. Corpus-verified 10/70 vanilla GTR2 setups still carry `gMa1.000f` headers, so it is a diagnostic rather than a hard error. Added a regression test; all 31 converter tests pass.

## 2026-11-25 01:00:00 -0500 - .dmg damage parser
- Added `simbin_text_tool.parse_dmg()` / `validate_dmg()` for all 200 damage configs (plain + JCA-decrypted): 43 universal keys out of 102 distinct, 0 validation problems. Added a full-tier corpus test; Quick remains 57.1 s.

## 2026-11-25 00:30:00 -0500 - Structured .aud sound-map parser
- Added `simbin_text_tool.parse_aud()` / `validate_aud_map()` for all 364 `.aud` files (plain + JCA-decrypted): 80,821 mappings, 193 keys split into 139 path-valued and 34 numeric-valued with 0 mixed keys, and all path values using backslashes. Added 2 regression tests (corpus full-tier); all 32 simbin-text/corpus-deep tests pass.

## 2026-11-24 23:59:59 -0500 - .cin/.scr script parsers
- Added `simbin_text_tool.parse_cin()`/`validate_cin()` (409 files, 5,798 events) and `parse_scr()`/`validate_scr()` (123 files, 1,998 actors). Corpus-verified Probability=1.00/Iterations=1 in every cinematic event and closed Type vocabulary; 0 validation problems. Added 3 regression tests (corpus check full-tier); all 29 simbin-text/corpus-deep tests pass.

## 2026-11-24 23:59:45 -0500 - .hdc parser reuse confirmed
- Corpus-verified that all 472 `.hdc` handling files (incl. JCA-wrapped) use the `.hdv` section/key structure and parse with `parse_hdv()` (835 keys, 18 sections). Added a full-tier corpus test. Also recorded GTTF byte-31 event/smoothing negatives and the `.aud` vocabulary survey.

## 2026-11-24 23:59:30 -0500 - .eng engine-file parser
- Added `simbin_text_tool.parse_eng()` / `validate_eng()` for all 333 `.eng` files: 28 universal keys and strictly increasing RPMTorque RPM values in every file (12,771 points, 0 validation problems). Added 2 regression tests (corpus full-tier); all 25 simbin-text/corpus-deep tests pass.

## 2026-11-24 23:59:00 -0500 - .grb gearbox-ratio parser
- Added `simbin_text_tool.parse_grb()` / `validate_grb()` for all 248 `.grb` files (incl. 77 JCA-wrapped). Corpus-verified the ratio semantics as **b/a** (driven/driving teeth) against 214+ inline decimal comments, with 6,929 gear entries and 0 validation problems. Added 2 regression tests (corpus check full-tier only); all 23 simbin-text/corpus-deep tests pass.

## 2026-11-24 23:45:00 -0500 - .rcd race-config parser
- Added `simbin_text_tool.parse_rcd()` / `validate_rcd()`: all 5,047 `.rcd` files classify into driver (3,038), event (1,830), NASCAR driver (178) and fueluse (1) families with 0 validation problems. Added 2 regression tests; all 21 simbin-text/corpus-deep tests pass, Quick stays at 56.1 s.

## 2026-11-24 23:30:00 -0500 - .skn skin parser and final tier rebalance
- Added `simbin_text_tool.parse_skn()` / `validate_skn()` for all 262 skin descriptors (788 layers, 786 words, 262 stamps, 0 validation problems). Moved the 3.9 s `.svm` key-subset check to full-only `tests/test_corpus_deep.py`, keeping Quick at 57.0 s (142 tests). All 19 corpus-deep/simbin-text tests pass.

## 2026-11-24 23:00:00 -0500 - .hed head-physics parser
- Added `simbin_text_tool.parse_hed()` / `validate_hed()` for all 88 `.hed` files (incl. 56 JCA-wrapped via `decrypt_jca_text()`). Corpus-verified 11 universal keys and a fixed 5-spring order (Sliding×3, FreeDamping×2) with 0 validation problems; FreeDamping legitimately omits SpringDir. Added 2 regression tests; all 15 simbin text tests pass.

## 2026-11-24 22:30:00 -0500 - Second test-tier rebalance
- Moved the 172-file `.sp` corpus check to full-only `tests/test_corpus_deep.py`, keeping Quick at 59.6 s (≤60 s budget, 140 tests). Full tier remains 51 modules / 396 tests; all tests pass.

## 2026-11-24 22:00:00 -0500 - .sp naming-convention invariants
- Corpus-verified 9 universal body names and 6 universal bar names across all 172 `.sp` files; added them to `validate_sp()` (still 0 problems corpus-wide). Also recorded negative results for `.hdr` index-table semantics and GTTF slot +36 quantisation. All 14 simbin text tests pass.

## 2026-11-24 21:30:00 -0500 - .cas parser reuse confirmed
- Corpus-verified that all 417 plain `.cas` car-graphics descriptors parse with `parse_scn()` (378 with MASFile references), sharing the `.gen`/`.trk` key family. Added a regression test; all 14 simbin text tests pass.

## 2026-11-24 21:00:00 -0500 - .inccar parser reuse confirmed
- Corpus-verified that all 42 plain `.inccar` vehicle-include configs use the `.veh` key=value syntax and are fully parsed by `parse_veh()` (100 keys, 17 near-universal). Added a regression test; all 13 simbin text tests pass.

## 2026-11-24 20:30:00 -0500 - rFactor .sp suspension-geometry parser
- Added `simbin_text_tool.parse_sp()` / `validate_sp()` for 172 plain `.sp` files: 1,872 bodies, 3,320 bars, 688 joints. Corpus-verified field presence and referential integrity — all 8,016 body references resolve, 0 validation problems. Added 2 regression tests; all 12 simbin text tests pass.

## 2026-11-24 20:00:00 -0500 - Test-tier rebalance
- Moved the 21.5 s ANM full-corpus decode-rate check into a new full-only `tests/test_corpus_deep.py`, restoring the Quick tier to 58.7 s (≤60 s budget, 137 tests). Full tier is now 51 modules / 392 tests; all tests pass.

## 2026-11-24 19:30:00 -0500 - Aud key coverage confirmed on encrypted corpus
- All 17 GTR2-only `.aud` keys used by `validate_aud()` are present in every corpus, including 101 decrypted JCA Race07 and 9 Volvo files — no audio-key addition is needed for Race07 sources. Documented as a no-gap confirmation.

## 2026-11-24 19:00:00 -0500 - Config text identification
- `media_tool.identify()` now labels plain `.rcd/.gdb/.car/.aiw/.cam/.hed/.dmg/.grb` configs by distinctive key signatures; JCA-wrapped variants stay `text-jca`. Added a corpus regression test; all 63 media tests pass.

## 2026-11-24 18:30:00 -0500 - MAS archive identification
- `media_tool.identify()` now reports MAS archives by content magic (1,090 `.mas`, all `.gtr`/`.gtl`/`.bmw`) with variant metadata; 25 signature-less type-2 archives stay unknown. Added a corpus regression test; all 62 media tests pass.

## 2026-11-24 18:00:00 -0500 - rFactor text-config identification
- `media_tool.identify()` now labels plain `.cas` (417), `.sp` (172) and `.inccar` (39) text configs; their JCA-wrapped counterparts (147/93/119) all decrypt to key=value text and remain `text-jca`. Added a corpus regression test; all 61 media tests pass.

## 2026-11-24 17:30:00 -0500 - GMT variant identification
- `media_tool.identify()` now reports plain GMT (ISI magic at +8), `gmt-gtr1` (third magic at +4), `racegmt` (`RaceGMT\0`) and JCA-wrapped GMT by content; corpus survey found 21,180 plain + 45,359 JCA + 643 RaceGMT loose files. Added a regression test; all 60 media tests pass.

## 2026-11-24 17:00:00 -0500 - rFactor .set camera/scene parser
- Added `simbin_text_tool.parse_set()` for the 22 CUBEASF `.set` descriptors. Corpus-verified: every file has one `mainview` View and one `FDirect01` Directional Light with `AmbientColor`; 5 have Instance/SearchPath sections. The parser handles multiple key=value pairs per line and dotted filenames. Added 2 regression tests; all 10 simbin text tests pass.

## 2026-11-24 16:30:00 -0500 - GIF identification
- `media_tool.identify()` now reports 479 genuine GIF87a/GIF89a files as `gif` with dimensions; JPEG/PNG masquerading as `.gif` are already identified by content. Added corpus assertions; all 59 media tests pass.

## 2026-11-24 16:00:00 -0500 - PNG and .veh identification
- `media_tool.identify()` now reports PNG files (1,640 local, with IHDR metadata) and `.veh` descriptors (2,763) by format; prior sampled survey had shown both classes unidentified. Added a corpus regression test; all 59 media tests pass.

## 2026-11-24 15:30:00 -0500 - SVM section-name invariant
- Corpus verification extended: the 15 `.svm` section names are identical between rF1 (517 files) and GTR2 (20,614 files) setups, so rF1→GTR2 setup conversion needs no section renaming — only the header and optional GTR2-only keys differ. Added test assertions.

## 2026-11-24 15:00:00 -0500 - Scene script identification
- `media_tool.identify()` now labels 123 `.scr` and 409 `.cin` rFactor scene/cinematic scripts; 14 `.djs` files were confirmed as raw MP3. Added a corpus regression test; all 58 media tests pass.

## 2026-11-24 14:30:00 -0500 - rFactor .gen identification
- `media_tool.identify()` now labels all 294 `.gen` vehicle-graphics descriptors and they all parse with `simbin_text_tool.parse_scn()`. Added a corpus regression test; all 57 media tests pass.

## 2026-11-24 14:00:00 -0500 - rFactor .hdv parser
- Added `simbin_text_tool.parse_hdv()` for rFactor high-detail vehicle physics. Corpus-verified on 156 files: 17 sections / 496 keys, with nine sections and 81 keys universal. Values are de-commented and quoted strings preserved; added 2 regression tests. All 8 simbin text tests pass.

## 2026-11-24 13:30:00 -0500 - rFactor .veh parser
- Added `simbin_text_tool.parse_veh()` for rFactor vehicle descriptors. Corpus-verified on 2,763 files / 57 keys: `Graphics` is universal and six identifier keys appear in all but 2 files. Added a regression test; all 6 simbin text tests pass.

## 2026-11-24 13:00:00 -0500 - CUBEASF family identification
- `media_tool.identify()` now recognises plain CUBEASF scene files (`.scn/.clf/.set/.trk`) as `cubeasf`; all 69 `.clf` and 417 `.scn` files parse with `simbin_text_tool.parse_scn()`. Added a corpus regression test; all 56 media tests pass.

## 2026-11-24 12:30:00 -0500 - SVM setup identification and key-subset rule
- All 10 encrypted `.svm` setups share an 8-byte payload magic (`5b 79 6d 98 7f 80 a9 e0`) and resist standard decompression and ISI-crypt — recorded as an undecoded variant. Added `.svm` variant identification (all 21,141 local setups classified) and `simbin_text_tool.parse_svm()`. Corpus-verified that rF1 setup keys (77) are a strict subset of GTR2 keys (86), so no rF1-only setup key requires remapping; only `car`/`createdby` are near-universal GTR2 additions. Added 2 regression tests; all 60 media/text tests pass.

## 2026-11-24 12:00:00 -0500 - Gzip .hat track-data reader
- Added `media_tool.hat_decompress()`, `hat-gzip` identification and a `hat-decompress` CLI command. All 188 local `.hat` files are valid gzip streams; GTR2/GTL use a `gMb1.000f/1.002f` header and Race07 a bare `Ver 0.08` header. Added a corpus regression test; all 54 media tests pass.

## 2026-11-24 11:30:00 -0500 - NASCAR-era .hdr/.dat audio decoder
- Added `media_tool.hdr_dat_mp3()` and the `hdr-dat-decode` CLI command: the small `.hdr` is an index and its companion `.dat` is a plain MP3 stream, decodable to PCM WAV via the existing ffmpeg path. Corpus-verified on 1,982 pairs (476 NT2003 + 1,506 NascarSimRacing); the `.hdr` block count is exact for all 476 NT2003 pairs. `identify()` now reports such headers as `hdr-dat`. Added 2 regression tests; all 53 media tests pass.

## 2026-11-24 11:00:00 -0500 - ANM corpus coverage verified
- Surveyed all 2,436 archived `.anm` members across 21 `../` game folders: **2,435 decode**, with the sole exception (F12001 `CATSTEER.ANM`) carrying a genuinely degenerate quaternion that the decoder correctly rejects. Corrected the stale "single-bone only / 673 multi-bone unsupported" docstring, clarified that +28 is the bone count (version at +16 is always 1), and added a 7-corpus regression test. All 4 ANM tests pass.

## 2026-11-24 10:30:00 -0500 - Fix stale BC write-back test expectations
- Full v19 (tree `0707d88`) found 2 failures: the BC6H/BC7 DDS tests still asserted that `to_bytes()` raises, but the new byte-exact BC write-back makes it succeed. Updated both tests to assert byte-exact round-trip (including the DX10 header); all 21 BC tests pass.

## 2026-11-24 10:00:00 -0500 - Tree validator decrypts JCA configs
- `validate_gtr2_tree()` now decrypts JCA-wrapped config files before applying all per-format validators. On a Race07 subtree this removed 9 false validation problems and exposed genuine GTL-style DMG values in encrypted files. Added a corpus regression test; all 30 converter tests pass.

## 2026-11-24 09:30:00 -0500 - Conversion-rule scoping on encrypted configs
- Corpus-verified that the HDC clutch rewrite (0.6→0.8) is GTL-specific: decrypted JCA Race07/Volvo HDCs use 0.9/1.2, so applying it there would be wrong. TYR `WetWeather=1` is universal across all corpora including decrypted JCA files. Documented as rule-scoping evidence (no code change).

## 2026-11-24 09:00:00 -0500 - Identify JCA-wrapped text configs
- `media_tool.identify()` now recognises JCA-wrapped text configs (`.car/.gdb/.cam/.scn/.aud/...`) as `text-jca` with line counts, instead of the generic `jca` label; media payloads still report `dds-jca`/`wav-jca`/`tga-jca`. Added a corpus regression test; all 51 media tests pass.

## 2026-11-24 08:30:00 -0500 - Byte-exact BC DDS write-back
- `DdsImage.to_bytes()` now round-trips BC4/BC5/BC6H/BC7 DDS files byte-exactly by reusing original level-0 blocks, mip chains and the 20-byte DX10 header when RGBA is unchanged; edited images are rejected rather than silently mis-encoded. Added a 7-format synthetic regression test; all 50 media tests pass. Full v18 on the prior tree: 368 tests, 0 failures.

## 2026-11-24 08:00:00 -0500 - GDB invariant re-verified on encrypted corpus
- The existing `validate_gdb_times()` session invariant (racetime == racetimescaled) holds on all 89 decrypted JCA `.gdb` files (80 Race07Complete + 9 Volvo) as well as plain GTL/GTR2 files; 4 plain Race07 files differ legitimately via later event sections. Added a corpus regression test. All 29 converter tests pass.

## 2026-11-24 07:30:00 -0500 - JCA-wrapped text configs across the corpus
- Surveyed all text config formats: JCA-encrypted variants are common in Race07/Volvo (`.car` 68.7%, `.cam` 64.9%, `.aud` 62.4%, `.gdb` 44%, `.scn` 92.5%, plus `.hdc/.eng/.tyr/.trk/.dmg/.hed/.grb`), while `.aiw/.rcd/.txt/.ini/.svm` are always plain. Added `media_tool.decrypt_jca_text()` (key trial + text validation) and wired it into `text_convert.py` for `.aiw`/`.scn`; `gtl_to_gtr2.aud_plain()` now reuses it. Added a corpus regression test for encrypted `.scn`; all 32 text/converter tests pass.

## 2026-11-24 07:00:00 -0500 - JCA-encrypted .aud conversion support
- Found 153 JCA-wrapped `.aud` files (Race07/Volvo) whose decrypted key sets are a strict subset of plain-text audio maps. `gtl_to_gtr2.aud_plain()` now decrypts them transparently before the sound-path, road-noise and key rules run, converting them to plain GTR2 text. Added a corpus regression test; all 28 converter tests pass. Full v17 on the prior tree: 367 tests, 0 failures.

## 2026-11-24 06:30:00 -0500 - FXM key_count semantics resolved
- Corpus-verified that FXM `key_count` encodes the keyframe component count: **3** for every TRS node (46,242 across standard/length-prefixed/trailing-name/single-key layouts) and **1** for marker=2 rotation tracks (10,596), i.e. position/quaternion/scale vs quaternion alone. NUL-named nodes have no key_count field. Added `file_key_count` to the semantic output and a corpus regression test; all 17 FXM tests pass. Full v16 on the prior tree: 366 tests, 0 failures.

## 2026-11-24 06:00:00 -0500 - SCGT AMBC.BMP decoded
- Solved the 2 long-standing undecoded Sports Car GT members: they are not LZSS-compressed but a 16-byte header (32x8) plus 768 bytes of raw RGB. Their archive records store 5 bytes fewer than declared, with the remainder in the inter-member gap; `reconstruct_type2_member()` recovers the full 784 bytes and `scgt_raw_texture_to_bmp()` emits a valid, coherent 822-byte BMP. Added a corpus regression test; all 5 SCGT tests pass.

## 2026-11-24 05:30:00 -0500 - AIW wp_perp unit-vector rule verified
- Corpus-verified another Turbo Basic hint: `wp_perp` is a normalized, track-parallel vector. All 29,028 track/pit waypoints across 6 corpora have unit norm within 1%; grid/pitbox waypoints carry a zero vector in 1,591/1,682 cases. Added `perp` parsing, a validator rule, and corpus assertions; all 9 AIW/CAM tests pass.

## 2026-11-24 05:00:00 -0500 - AIW wp_score checkpoint rule verified
- Corpus-verified from the Turbo Basic source hints that `wp_score`'s first field is a checkpoint in 0..2 on all 30,710 local waypoints (10,983 / 9,135 / 10,592); added it to `validate_aiw_waypoints()`. `wp_event` showed no strict rule (first field 1.0 or 1.1 only) and was not promoted.

## 2026-11-24 04:30:00 -0500 - AIW wp_bitfields rule verified
- Corpus-verified a second waypoint rule from the Turbo Basic source hints: `wp_bitfields` is 0 for track/pit waypoints and 1 for grid/pitbox waypoints, holding on all 30,710 local waypoints with zero exceptions. Added it to `validate_aiw_waypoints()` and extended the regression tests.

## 2026-11-24 04:00:00 -0500 - CAM deactivation invariant
- Corpus-confirmed the camera deactivation encoding: an FLT_MAX `ActivationLocation` triplet holds exactly when `ActivationRadius=1` (23/23 local cameras, and no other camera has radius 1). The Turbo Basic reference documents a 99999 sentinel that does not occur locally; both are accepted by the new `validate_cam()`. Added a corpus regression test. Also recorded the excluded GTTF shared-memory-header hypothesis.

## 2026-11-24 03:30:00 -0500 - CAM flags corpus check
- Extended the CAM parser with Flags1/Flags2, MovementRate, ShakeRate and ShakeMagnitude. Corpus-verified that Flags2 is 0 in all 1,604 cameras, while the documented Flags1 movement/shaking bits only partially correlate with non-zero rates — recorded as observations, not enforced rules. Added a regression test.

## 2026-11-24 03:00:00 -0500 - CAM file reader and negated-coordinate rule
- Added `parse_cam()` / `cam` CLI using CAM field names documented in the vendored Turbo Basic source of the guitarmaen editor. Corpus-verified that CAM X/Z are negated relative to AIW waypoint coords on **8/8 paired tracks** (negation reduces mean nearest-waypoint distance by 1.4x-5.7x); exposed as `Camera.aiw_position()`. Added 2 regression tests, including a full corpus check.

## 2026-11-24 02:30:00 -0500 - AIW waypoint WP_PTRS semantics verified
- Corpus-verified the `WP_PTRS` waypoint-class rules from the newly added `../guitarmaen-aiw-cam-editor-gtr2-qt` reference: the 4th field buckets into 0=track (22,523), 1=pit (6,505), 2..105=grid (1,212) and ≥106=pitbox (470), and equals `wp_branchID` on **30,710/30,710** waypoints across 26 AIW files. Added `Waypoint.kind()`, `validate_aiw_waypoints()`, CLI output, and 2 regression tests.

## 2026-11-24 02:00:00 -0500 - SCGT compressed BMP: RLE8 rejected
- Tried a Microsoft RLE8 BMP token decoder on the 2 undecoded `AMBC.BMP` members in `../SportsCarGtUsa`: it terminated early with only 32 of the expected 256 indices. Recorded as another rejected hypothesis; the members remain preserved losslessly.

## 2026-11-24 01:30:00 -0500 - Fifth FXM variant: single-key wipers
- Decoded the final large FXM gap: marker=0 (FXA, 28-byte tail) and marker=1 (FXM, 40-byte tail) single-validated-key nodes with trailing names. Recovers 115 files / 280 nodes; 1,111 of 1,115 files now decode (28,422 nodes total), leaving 4 BMW E30 wiper files. Added a regression test; all 16 FXM tests pass.

## 2026-11-24 01:00:00 -0500 - Fourth FXM variant: trailing names
- Decoded the trailing-name FXM layout (`marker=1, size_hint, key_count=3, 2 TRS keys, name_len, name`) used by cockpit-wiper and driver animation files where the name follows the keyframes. Strict unit-quaternion/scale validation recovers 44 files (previously zero-node); 119 files remain unresolved, mostly `.fxa` wipers with non-unit scale keys. Added a regression test; all 15 FXM tests pass.

## 2026-11-24 00:30:00 -0500 - FXM zero-node corpus survey
- Surveyed all 1,115 FXM/FXA/LMA files: 952 decode at least one node (25,432 nodes total), 163 remain zero-node. The remainder is dominated by cockpit-wiper `*_cpitwiper.fxm/.fxa` files with NUL-terminated names and an unresolved frame layout; no speculative decoder was added. Documented as a bounded gap.

## 2026-11-24 00:00:00 -0500 - FXM rotation-track variant decoded
- Decoded the marker=2 length-prefixed FXM node variant: `frames` keyframes of `(float time, quaternion xyzw)`, with `size_hint == 8 + 20*frames`. Corpus-verified on 532 tracks / 12,955 keys in 26 GTR2 and Race 07 files (unit quaternions, finite times). `decode_fxm_semantic()` now reports them with `kind="rotation"`; added a regression test. Full v8 on the previous tree: 356 tests, 0 failures.

## 2026-11-23 23:30:00 -0500 - Third FXM node variant decoded
- Found a length-prefixed FXM node dialect in 22 GTR2 pit-animation files that the `Bip01\x01` anchor missed entirely (0 nodes decoded). `fxm_tool.parse_length_prefixed_nodes()` now decodes 1–4 TRS nodes per file with validated unit quaternions and identity scale; `decode_fxm_semantic()` reports variant `length-prefixed`. Added a regression test; all 14 existing FXM tests still pass.

## 2026-11-23 23:00:00 -0500 - MAS-archived cube maps verified
- Extended the cube-map survey to DDS members inside MAS archives: 40 archives / 1,872 DDS members revealed 27 cube maps (DXT1/DXT5, up to 9 mips) previously missed by loose-file scans. All 27 round-trip byte-identically; added a fast regression test using `showroom.mas`. Also documented that JCA re-encryption is semantically but not byte-exact.

## 2026-11-23 22:30:00 -0500 - Byte-exact DDS header and BMP row padding
- A mixed-format round-trip audit found two remaining same-length byte mismatches: DDS files with a zero linear-size field (header rewritten) and BMP files with non-zero row padding (padding zeroed). Both are now preserved; a 338-file mixed audit (DDS/TGA/BMP/WAV) shows zero mismatches for all supported variants. Added two regression tests.

## 2026-11-23 22:00:00 -0500 - Complete JCA cube-map scan
- Optimized the encrypted-DDS scan using the uncompressed size stored in the JCA header: 33,351 files filtered to 266 candidates, revealing **88 JCA cube maps** (vs 3 in the earlier partial scan). All 88 round-trip byte-identically, including DXT5 and 2 mipmapped samples. Added a mipmapped-cube regression test and corrected the corpus count.

## 2026-11-23 21:30:00 -0500 - BC7 DDS decode
- Added `bc7_format.py`, decoding all 8 BC7 modes from mechanically generated Khronos BPTC tables; `media_tool.py` reads DX10 BC7 (DXGI 97/98/99) DDS files. Verified against an independent spec transcription on 8,000 random blocks (1,000 per mode) and 8 synthetic tests. Confirmed the spec's rotation-channel convention against Microsoft's BC7 mode reference. No local BC7 samples exist.

## 2026-11-23 21:00:00 -0500 - Complete BC6H mode coverage
- `bc6h_format.py` now decodes all 14 valid BC6H modes (including delta-transformed endpoints) in UF16 and SF16, with tables generated mechanically from the spec-derived reference source. Verified against an independent spec port on 8,400 random blocks (14 modes × 2 variants, 300 each); 13 tests pass. BC7 remains the only unimplemented BCn format.

## 2026-11-23 20:30:00 -0500 - Byte-lossless BMP round-trip
- 24/32-bit BMP round-trips now preserve the original 54-byte header and trailing padding bytes instead of rebuilding a canonical header and dropping the tail. 29/29 supported corpus samples are byte-identical; added a regression test.

## 2026-11-23 20:00:00 -0500 - Byte-lossless WAV round-trip
- `wav_roundtrip()` no longer rewrites WAV files through stdlib `wave`, which silently dropped `LIST`/`PAD`/`fact` chunks and rewrote WAVEFORMATEX headers. All 30 sampled corpus files (24 with extra chunks) now round-trip byte-identically. Added a regression test.

## 2026-11-23 19:30:00 -0500 - Preserve TGA v2.0 footer
- `read_tga()`/`write_tga()` now preserve the optional 26-byte `TRUEVISION-XFILE.` footer instead of silently dropping it. 2,311 corpus TGA files carry one; a real 92 KB sample now round-trips byte-identically. Added a regression test.

## 2026-11-23 19:00:00 -0500 - Signed BC6H (SF16) decode
- `bc6h_format.py` now decodes signed BC6H (DXGI `BC6H_SF16`) alongside UF16 for the same two non-transformed modes; `media_tool.py` reads DXGI 96 DDS files. Fixed a Python sign-extension bug found during verification. Matched a corrected independent spec reference on 4,000/4,000 random signed blocks; 3 new tests.

## 2026-11-23 18:30:00 -0500 - Cube-map DDS round-trip
- `media_tool.py` now detects `DDSCAPS2_CUBEMAP`, decodes all six faces separately and reassembles them on write. All 24 plain local cube-map DDS files (previously silently downgraded to a single face) round-trip byte-identically, as do 3 JCA-encrypted cube maps including a DXT5 sample. Also fixed level-0 size accounting for DXT4. Added corpus regression tests.

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
