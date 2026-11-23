# Task plan status

Plan order: quickest wins first (Wave 0 → 3). Evidence for each item is in the
named tests/docs/tools.

## Wave 0 — complete
| # | Task | Status | Evidence |
|---:|---|---|---|
| 1 | Mine `../rfactortools` | done | `docs/reuse-rfactortools.md` |
| 2 | Mine tutorials | done | `docs/reuse-rfactortools.md` (RacerM rules, GTL2GTR2 readme) |
| 3 | Validation fixtures | done | `tests/test_fixtures.py` (57 identical, new-layout rF1, 5 PHS + DETOMASO) |
| 4 | Loose-extension survey | done | `docs/binary-formats.md`; JCA text-file tests in `tests/test_race07.py`, `tests/test_volvo.py` |
| 5 | Doc gaps | done | `CAPABILITIES.md` (missing GTR 2004, 6 untested ISI signatures) |

## Wave 1 — complete
| # | Task | Status | Evidence |
|---:|---|---|---|
| 6 | AIW/SCN semantics | done | `simbin_text_tool.py`, `tests/test_simbin_text_tool.py` |
| 7 | JCA cross-check vs third-party tool | done | `monodis` IL confirms magic/offsets/LE/XOR 0xEB/keys; `docs/reuse-rfactortools.md` |
| 8 | FXM cross-corpus | done | `tests/test_fxm_crosscorpus.py` (567 files, 54 mismatches) |
| 9 | 57-pair carry-over test | done | `tests/test_carryover.py` |
| 10 | GMT layout bridge | done (partial) | `gmt_layout.py` structural + semantic bridges, `gmt_semantic.py`, `tests/test_gmt_layout.py`, `tests/test_gmt_semantic.py`; geometry preserved structurally, in-game unvalidated |

## Wave 2 — complete
| # | Task | Status | Evidence |
|---:|---|---|---|
| 11 | rF1→GTR2 pipeline | done (prototype) | `rf1_to_gtr2.py`, `tests/test_rf1_pipeline.py` (253 GMTs) |
| 12 | GTTF/VCR reader | done (partial) | `simbin_events_tool.py`, `tests/test_simbin_events_tool.py`; metadata framing (all 4 variants) + 63-byte frame grid decoded |
| 13 | Bink decode/encode | done (external tools) | ffmpeg decode + LGPL `raynorpat/libbink` encoder via `media_tool.py`; validated round-trip on real BIK |
| 14 | PHS identity | done (resolved) | PAR2-style recovery containers for `GTL_Update_0901.exe`; `phs_tool.py`, `docs/phs-research.md` |
| 15 | EA TGQ decode | done (external tool) | ffmpeg decodes all 22 `.TGQ` files (TQI video + `adpcm_ea`); `media_tool.py tgq-decode` |

## Wave 3 — blocked by external input
| # | Task | Blocker | Evidence of attempt |
|---|---|---|---|
| 16 | In-game validation | Requires running GTR2 with converted content | Converter output validates structurally only |
| 17 | Residual field semantics | Authoritative spec or runtime-validated reference | GTTF frame fields beyond position/time, FXM key_count meaning, new-layout GMT f0/f7/extra streams, CUBE MTS per-rig table, `PHYSICS.PHS` opaque blob |
| 18 | GTR (2004) full layout | done (structural) | `gmt_semantic.read_gtr1_descriptors()` + `read_gtr1_object_mesh()` decode all 33,477 GTR1 GMTs in `../GTR1Vanilla`: 10,359 descriptor-based + 23,118 descriptor-less, 0 undecoded; 48-byte vertices incl. UV and f0/f7 markers decoded. In-game validation still needs GTR2 runtime (task 16). |
| 19 | PHS runtime consumer | Wine trace blocked by missing MFC42.dll | No `.phs`/PAR2 strings in GTL executables; `docs/phs-research.md` |

## PHS — resolved

The five GTL `.phs` members were investigated and resolved: four are PAR2-style
recovery containers for `GTL_Update_0901.exe` (verified packet chain, Main metadata
with slice size 384000 and file id `2f1fc214...`, and a FileDesc packet naming the
file); `PHYSICS.PHS` is a 13 KB opaque blob with no PAR2 packets. They are not
encrypted physics data. `phs_tool.py`, `tests/test_phs_tool.py` and
`docs/phs-research.md` hold the evidence table, ranked hypotheses and the
recommendation to defer. Speednut's `mas_extract.exe` under Wine produces
byte-identical members, so it does not decrypt PHS. A Wine runtime consumer trace
was blocked by a missing `MFC42.DLL`.

## Final verification
```
python3 run_tests.py --mode quick    -> 67 tests, ~9 s, 0 failures
python3 run_tests.py --mode normal   -> 150 tests, ~305 s, 0 failures
python3 run_tests.py --mode full     -> 273 tests, ~620 s, 0 failures (2 skipped)
python3 pre_push_check.py            -> PASS
git status --short                    -> clean
```

## Later work (post-plan)
- Quick/Normal/Full test execution modes (`run_tests.py`) with deterministic progressive tiers.
- Offline unresolved-field RE documented in `docs/open-issues-research.md`: FXM key_count, GTTF slots 7/9 and PHYSICS.PHS have multiple independent negative results; remaining confirmation needs a spec or runtime.
- All original Wave 0-2 tasks and the binary-format decodes (GMT/MAS/MTS/FXM/GTTF/GTR1/Bink/TGQ) are complete and pushed.
