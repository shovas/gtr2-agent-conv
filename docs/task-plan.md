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
| 12 | GTTF/VCR reader | done (partial) | `simbin_events_tool.py`, `tests/test_simbin_events_tool.py`; metadata framing (driver/co-driver/car) now decoded |

## Wave 3 — blocked by external input
| # | Task | Blocker | Evidence of attempt |
|---:|---|---|---|
| 13 | In-game validation | Requires running GTR2 with converted content | Converter output validates structurally only |
| 14 | Bink decode/encode | done (external tools) | ffmpeg decode + LGPL `raynorpat/libbink` encoder via `media_tool.py`; validated round-trip on real BIK |
| 15 | PHS cipher | No spec; not ISI, not JCA (all keys tried), no standard compression | 5 files, entropy ~7.95, `docs/binary-formats.md` |
| 16 | GTTF frame records, CUBE MTS material IDs, `.tgq` | Authoritative spec or runtime-validated reference | Observations only in `docs/binary-formats.md`; FXM skeleton/TRS keyframes and GTTF/IRSR metadata framing were decoded (`fxm_tool.py keys`, `simbin_events_tool.py`) |
| 17 | GTR (2004) corpus | Not installed locally | `CAPABILITIES.md` coverage gaps |

## TODO — PHS identity hypothesis

The 5 GTL `.phs` files (PHYSICS/CARS/DRIVERS/AI/TRACKS, ~7.95 bits/byte
entropy) are physics/AI data — confirmed distinct from the plain-text `.psh`
pixel shaders. Because they are ISIMotor content, they may be the same binary
format under a different name in other ISIMotor games (e.g. rFactor/GSC/AMS
physics blobs such as `.hdv`, `.veh`, `.rcd`, `.gen`, or the Reiza `.cch`).
Investigate whether a known ISI physics container or cipher applies:
- compare PHS against `Physics2.gtl` content in GTR2/GTL mods and other game corpora;
- check `../rfactortools` and `../quickbms_scripts` for physics-container parsers;
- test whether the 5 files are a packed table of known `.hdv/.veh/.rcd` records.

No cipher or spec found so far; this is an explicit follow-up, not a claim.

## Final verification
```
python3 -m unittest discover -s tests -v   -> 223 tests OK (skipped=1)
git status --short                          -> clean

Additional corpora reviewed after the plan was written (F1CS2000, GameStockCar,
NascarSimRacing, Race07Complete) are recorded in `AGENTS.md` and
`docs/binary-formats.md`; no new plan tasks arose from them.
```
