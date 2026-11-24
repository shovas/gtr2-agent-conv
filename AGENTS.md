# AGENTS.md

## Project scope
- New project: conversion scripts from ISIMotor-lineage sim games (rFactor, Race 07, GSC 2013/GSCE, BMW M3 Challenge, Automobilista 1, etc.) to **GTR2**.
- Repo is an agent-driven research project (see `README.md`); keep commands/tooling lightweight and document them here as they are added.

## Commands
- Tests: `python3 run_tests.py --mode quick|normal|full` (default `normal`; progressive coverage, budget + timing report; `--list` shows tiers, `--coverage` adds optional line coverage). Plain full suite: `python3 -m unittest discover -s tests -v`.
- Pre-push safety/privacy check: `python3 pre_push_check.py` (must pass before pushing; allowlists `shovas` and its noreply email)
- Tools: `mas_tool.py`, `isi_crypt.py`, `jca_crypt.py`, `gmt_tool.py`/`gmt_format.py`, `gmt_layout.py`/`gmt_semantic.py`, `mts_format.py`, `race_gmt.py`, `phs_tool.py`, `rf1_to_gtr2.py`/`gtl_to_gtr2.py`, `text_convert.py`, `simbin_text_tool.py`, `simbin_events_tool.py`, `ghost_align.py`, `gzip_simbin_tool.py`, `fxm_tool.py`, `media_tool.py`, `anm_format.py`, `validate_conversion.py`, `corpus_diff.py`, `validate_materials.py`. See `FEATURES.md` for usage.

## Key locations
All `../` game installs below are **read-only references** — do not copy game data into this repo.
- `../rfactortools/` - inspiration/reference repo (rFactor -> GSC2013 tools, Python package). Read before implementing conversions; reuse patterns where they fit GTR2.
- `../GTR2Steam/` - local GTR2 Steam install (1.6G). **Target-format reference**: real `GameData` layout, `.car/.hdc/.eng/.tyr/.aud/.gdb/.trk`, and `.gtr` GMOTORMAS10 archives.
- `../BMWM3Challenge/` - local BMW M3 Challenge install (369M, moved from in-project to workspace root). **ISIMotor source reference**: 17 `.bmw` GMOTORMAS10 archives (readable by `mas_tool.py`), loose `.gmt/.fxm/.fxa/.lma/.car/.hdc/.eng/.tyr/.trk/.aiw` and media.
- `../GTLSteam/` - local GT Legends Steam install (1.8G). **ISIMotor source reference**: `.CAR` (uppercase) files, `.gtl` GMOTORMAS10 archives, GTL-era GDB/classes.
- `../RF1Vanilla/` - local rFactor 1 vanilla install (1.5G). **ISIMotor source reference**: 85 MAS type-1 `.mas` archives, 9,662 GMTs (9,630 old-layout magic at 0x1D4 + 32 GTR2-style at 0x08), 120 ISI-encrypted GMTs decryptable with `isi_crypt.py` (skip=4).
- `../CopaPetrobrasdeMarcas/` - local Copa Petrobras de Marcas install (2.2G). **ISIMotor source reference**: 50 MAS type-1X `.mas` archives (Petrobras signature variant, supported by `mas_tool.py`), 13,679 Game-Stock-Car-signature encrypted members decryptable with `isi_crypt.py` enctype 1.
- `../SportsCarGtUsa/` - local Sports Car GT (1999, ISI) install (338M). **Ancestral ISIMotor reference**: 61 signature-less MAS type-2 `.mas` archives (16,070 members; `mas_tool.py` reads/writes them), `.vrl` track meshes, 16-byte-header+zlib textures.
- `../Automobilista/` - local Automobilista (Reiza, 2016) install (35G). **Late ISIMotor source reference**: 470 MAS type-1 archives (111,943 members), 91,974 old-layout GMTs (91,962 GSC-encrypted), same structural gap as rF1/Copa.
- `../F12002/` - local F1 2002 (ISI, 2002) install (600M). **Ancestral ISIMotor reference**: 63 MAS type-3 (`CUBEMAS4.10`) archives (19,235 members), 13,100 CUBE MTS meshes (12,640 standard magic), no ISI encryption.
- `../F1C/` - local F1 Challenge 99-02 (ISI, 2003) install (591M). **Ancestral ISIMotor reference**: 197 MAS type-3 archives (21,977 members), 14,834 CUBE MTS meshes (13,769 standard magic), `.anm` animations (unparsed), no ISI encryption. Direct rFactor predecessor.
- `../F1CS2000/` - local F1 Championship Season 2000 (ISI, 2000) install (471M). Byte-identical copy of `../F12000` (all 570 files); no new format work needed.
- `../GameStockCar/` - local Game Stock Car (Reiza, ISIMotor) install (2.1G). 48 MAS type-1 archives (19,995 members), 19,987 GSC-signature encrypted members, old-layout GMTs.
- `../NascarSimRacing/` - local NASCAR SimRacing (ISI, 2005) install (1.9G). 311 MAS type-3 archives (36,716 members), 26,473 CUBE MTS meshes with a new `CUBE_MTS_4.20` magic variant (25,689 vs 784 `4.10`).
- `../StockCarExtreme/` - local Stock Car Extreme (Reiza, GSC-based) install (16G). **ISIMotor source reference**: 196 MAS type-1 archives (71,814 members), 62,522 GSC-signature encrypted members, 60,841 old-layout GMTs.
- `../Race07Decryptor/` - self-contained .NET 8 win-x64 console app (`Race07Decryptor.exe`, 65M) with Blowfish/JCA decryption but no source or format spec. Reference only; our native `jca_crypt.py` supersedes it.
- `../VolvoTheGame/` - local Volvo (SimBin, ISIMotor) install (504M). 2,026 loose GMTs use JCA with the non-default `volvo` key (`jca_crypt.CUSTOM_KEYS["volvo"]`), decrypting to standard GTR2-layout GMTs.
- `../F12001/` - local F1 2001 (ISI, 2001) install (453M). **Ancestral ISIMotor reference**: 80 MAS type-6 archives (`CUBEMAS4.00`/`CUBEMAS4.01`, 16,720 members; `mas_tool.py` type 6 reads/writes them with signature preservation), CUBE MTS meshes.
- `../NT2003/` - local NASCAR Thunder 2003 (ISI, 2002) install (722M). **Ancestral ISIMotor reference**: 179 MAS type-3 archives (19,006 members, 10,397 CUBE MTS meshes), 476 `.hdr`/`.dat` audio pairs, `.veh/.hdv` text. No ISI encryption.
- `../F12000/` - local F1 2000 (ISI, 2000) install (471M). **Ancestral ISIMotor reference**: 118 MAS type-2.5 (`CUBEMAS2.50`) archives (30,909 members; `mas_tool.py` type 5 reads/writes them), `.scn/.aiw/.veh/.tgq` files.
- `../NT2004/` - local NASCAR Thunder 2004 (ISI, 2003) install (632M). Ancestral reference: 136 MAS type-3 archives (20,414 members, 14,250 standard CUBE MTS), `.hdr` audio headers, `.skn` text skins, `.djs` MP3 audio.
- `../GTR1Vanilla/` - local GTR – FIA GT Racing Game (2004) install (1.2G, 3,613 files). **Previously missing target-format corpus**: 430 MAS type-0 `.gtr` archives; 33,477 GMTs use a third magic `c8cfd2d8ced8e6c3d6ded8bdbba6bf90` at 0x04 (not parsed by `gmt_format.py`), 3 use `OR_GMT_1.00`. No ISI encryption.
- `../gtr2-tools/` - third-party GTR2 tool collection (592M, 2,431 files). **Reference only**: `GTR2.Tools.Bundle.Vol.1` includes the freeware `AIW Repair Utility v1.0` whose readme/INI files document rFactor→SimBin AIW rules (scale `wp_galpha` by 0.45, drop 12 rFactor-only tags, replace `wp_cheat` with `wp_event=(1.000,0,0)`); `ccgepmonitor-main` and `gtr2-memory-operations-tool-wpf` are C# runtime/memory tools (in-memory structures, not file formats); several third-party tools with unclear licences. Do not copy code/binaries.
- `../Speednuts_mas_extract/` - single 264K Windows console `mas_extract.exe` (C compiled) for GTR2/GTL/rFactor MAS unpacking (`GMOTORMAS10`, `CUBEMAS4.10`). Reference only; our `mas_tool.py` covers more variants.
- `../Race07Complete/` - local Race 07 complete/DLC install (12G, 122k files; WTCC/STCC/Race On/GTR Evolution content). 66,186 loose GMTs in three variants: JCA-encrypted, standard new-layout, and a new `RaceGMT\0` header (643 files). 2 MAS type-0 archives.
- `../Race07Vanilla/` - local Race 07 (SimBin, 2007) install (2.7G). **Sibling of GTL/GTR2**: 21,687 loose GMTs use SimBin JCA encryption (magic `0fb1ffff`), decrypted natively by `jca_crypt.py` to standard GTR2-layout GMTs; 2 small MAS type-0 `.gtr` archives hold 5 already-plain GMTs.
- `../legacy/` - prior attempt artifacts moved from `tools.unsorted`. Contains ad-hoc probe/phase scripts and small sample fixtures (`aiw_*`, `Brianza_*`). Treat as reference, not authoritative; not part of this repo.
- `../old-tmp-files/` - another prior-attempt scratch folder (68 files, 49M): 59 ad-hoc probe scripts, GUI screenshots, Linux tooling (Wine/rar), and a `gMa1.002f` AIW fixture (`Brianza_Full.aiw`). Same caveats as `legacy/` (dead hardcoded paths, imports modules absent from the current `../rfactortools`). Documented as legacy scratch, **not ruled out**: the AIW fixture and GMT/UV probe scripts may become useful for future field-level investigation; revisit rather than delete.
- `../hand_selected/` - hand-picked artifacts recovered from `tools.unsorted.irrelevant`. Small samples: `audtest/default.aud`, `gtr1_sniffnnbe5l6i/.../Mesh.gtr`, `xval_r7/*.car`, `xval_test` (`.gtr/.GMT/.TGA/.JPG`). Large generated output trees are present locally for reference but are outside this repo.
- `../quickbms_scripts/` - large QuickBMS script collection (2745 files). **Format reference**; most relevant is `mas.bms` (GMOTORMAS10/CUBEMAS4/ISI MAS types). Use as spec cross-check; prefer native Python in `rfactortools`/this project for pipeline integration.
- `../MAS2Extract/` - small C# GPLv3 tool for **rFactor 2 MAS2** (`GMOTOR_MAS_2.90`) extraction/deciphering. Useful as rF2-format reference, but not GMOTORMAS10/GTR2/GTL.
- `../gtr2-agent-tools/` - GTR2 driving/UI automation toolkit (CC BY-NC 4.0). **Reference only** for format parsers in `scripts/gtr2_driving/`: `mas.py`, `gmt.py` (mesh table at 0x16C), `trackmap.py` (AIW), `cargears.py` (HDC/ENG/GRB), `pitzones.py` (TRK+MAS). Check license before reusing code.
- `../modding-tools-and-tutorials/` - local third-party modding tools/tutorials collection (131M, gitignored; moved from in-project to workspace root). **Reference only**; includes `GTL2GTR2 Converter v0.9.0.1` (simple ext/TRK-MAS rename only, no AIW/GDB fixes), RacerM rFactor->GTR2 track notes, GMT/hex-editing tutorial hints. Do not commit binaries.
- `../guitarmaen-aiw-cam-editor-gtr2-qt/` - Qt5/C++ AIW/CAM/GDB editor for GTR2-style games (9.6M, 73 files; **no license file — reference only, do not copy code or binaries**). Its `AGENTS.md` documents verified AIW/CAM semantics: files are CRLF+ASCII (confirmed on all 3 local GTR2 AIWs), `WP_PTRS.d` classifies WPs (0=track, 1=pit, 2..105=grid, ≥106=pitbox; `ptrs_a`/`ptrs_b` = prev/next), 4 paths per WP (0=fast, 1=wet, 2=left, 3=right; multipath measured from Path0, not pos), and CAM positions are negated vs AIW coords. `original-guitarmaen-aiw-cam-editor-main/` vendors the Turbo Basic source (`rF_AIW_CAM_422.x`, ~9.6k lines) plus help files — the authoritative reference for AIW/CAM defaults and field meanings. Our `simbin_text_tool.py` currently implements only the rF1→SimBin text rules, not waypoint/path internals.
- `../rFactorSharedMemoryMap/` - GPLv2 rF1 telemetry shared-memory plugin (308K, 40 files). **Reference only** (no code copying): `Include/rfSharedStruct.hpp` documents runtime field units/ranges (yaw/pitch/roll rad, +x pitches up/+y yaws right/+z rolls right, speed m/s, gear −1/0/1+, unfilteredThrottle 0..1, unfilteredSteering −1..1). Useful cross-check for telemetry field semantics; does not describe file formats.
- `../rF2SharedMemoryMapPlugin/` - GPLv3 rF2 internals shared-memory plugin (3.1M, 71 files). **Reference only**: `Include/rF2State.h` documents rF2 runtime telemetry fields/ranges (mEngineRPM, mFilteredThrottle 0..1, mFilteredSteering −1..1, mGear −1/0/1+). Relevant to GTTF telemetry-field hypotheses, but it documents runtime state, not the `.VCR` file bit layout; apply only as units/range evidence.
- `~/tmp/tools.unsorted.irrelevant/` - remaining large/generated/irrelevant items (installers, caches, etc.).

- `../RaceRoomTheGame/` (497M, 6,756 files), `../RaceRoomTheGame2/` (1.1G, 15,163): early RaceRoom ISIMotor sims; 14,603 loose JCA v1 GMTs decryptable with the **volvo** key (see `media_tool.detect_jca_key()`), plus `.car/.gdb/.aiw/.cam/.aud/.rcs` configs; `docs/corpus-reference.md` has details.
- `../ccgepmonitor/` (2.7M, 65 files; **no license file — reference only, do not copy code**): C# monitor reading GTR2 telemetry shared-memory buffers (`$GTR2CrewChief_Telemetry$` etc.); `GTR2Data.cs` documents GTR2 runtime state (game phase, yellow flags, surface types, sectors, pit state) useful only as GTTF telemetry hypotheses cross-check, not file formats.
- `../SuperleagueFormula2009/` (717M, 568): rF1-era sim with the known Superleague ISI signature (enctype 1); 28 type-1 `.mas`, `.veh/.rcd/.cam/.scn/.aiw/.gdb`, 6 `.vcr` replays.
- `../LexusIsfTrackTime/` (233M, 412), `../TC2000/` (1.4G, 938), `../SimuladorTopRace2009/` (2.1G, 1,084): rF1-era single-series sims; type-1 MAS archives, `.veh/.hdv/.rcd/.svm/.scn/.aiw`, `.rfm`. TC2000 introduces a 12-key "talent" `.rcd` driver family; TR2009 uses the known Top Race 2009 ISI signature on 118 uppercase GMTs that decrypt but expose no submeshes. See `docs/corpus-reference.md`.

## Reference corpora index
- `docs/corpus-reference.md` is the condensed quick-lookup index of all `../` folders (sizes, counts, key formats, licenses, and what each is useful for). The per-folder notes below remain authoritative for caveats. These folders are always available for reference during tasks; record newly verified findings in the relevant docs and update that index when roles change.

## `../rfactortools` facts (verified)
- Python package (`setup.py`, `setuptools`, `version=0.4.0`); C extension `rfactortools/_crypt` from `rfactortools_crypt.cpp` (`SConstruct` also builds `rfactordec.c` and shared lib).
- Core modules: `aiw.py`, `crypt.py`, `gdb.py`, `gmt.py`, `gsc2013.py`, `gtr2.py` (currently GTR2->GSC2013 direction), `img.py`, `mas.py`, `scn.py/scn_parser.py`, `sfx.py`, `util.py`, `veh.py`; CLI entrypoints under `rfactortools/programs/`.
- Tests: `tests/test_*.py` (`unittest`). `SConstruct`: `scons`/default runs flake8 (`python3 -m flake8.run --max-line-length=120`), `scons test` runs `python3 -m unittest discover`, `scons all` runs flake8+pylint+test. `flake.nix` targets nixos-22.05/python310, `doCheck=false`.
- Dependencies in docs/nix: Python 3 + Pillow (`python3-pil`, `python3-pil.imagetk`), tkinter for GUI. README notes Python3.4/Pillow; verify against current environment before relying on old version assumptions.

## Legacy gotchas
- Many `legacy/*.py` scripts hardcode absolute home-directory paths (`ROOT="<home>/rfactortools"`, `TMPDIR=<tmpdir>`) that do not exist in a fresh checkout. Update paths to `../rfactortools` or package imports before reuse.
- Legacy harness/demo scripts import modules/symbols not present in `../rfactortools` as-is (e.g. `rFactorToGTR2`, `Race07ToGTR2`, `gtr2verify`, `convert`, `gmtconvert`). Treat them as evidence of intended API, not working code against current reference repo.
- Legacy contains large sample binaries/data (`.aiw`, `.tga`, `.dds` in sample dirs) kept for reference; avoid copying generated conversion outputs back into git.

## Documentation Maintenance

Maintain the following Markdown files as accurate, concise, end-user-oriented documentation. Update them whenever relevant functionality, requirements, or behavior changes.

- **CHANGES.md** — Chronological changelog, newest first, with timestamps (`YYYY-MM-DD HH:MM:SS ±HHMM`). Record meaningful additions, improvements, fixes, removals, and breaking changes. Write entries suitable for generating release notes; describe user-visible outcomes rather than internal development activity.
- **FEATURES.md** — High-level overview of implemented features, organized by end-user relevance and interest. Describe what the project offers and why it is useful, not implementation details. Keep descriptions brief and avoid listing every underlying capability.
- **CAPABILITIES.md** — Detailed inventory of supported technical operations and behaviors, including lower-level functionality that enables features but may not be directly exposed to users. Describe what is actually possible, its scope, limitations, and relevant prerequisites.
- **DEPENDENCIES.md** — Environment setup reference listing required external software, libraries, tools, projects, services, files, and directories. Include versions or compatibility constraints when relevant, installation or acquisition instructions, configuration requirements, and distinctions between required and optional dependencies. Exclude standard components unless their presence or version matters.

### General Rules

1. **Keep documentation synchronized:** Review affected files after every meaningful change; update only those impacted.
2. **Document verified reality:** Distinguish implemented, experimental, partial, unsupported, and planned functionality. Never present untested assumptions as confirmed capabilities.
3. **Maintain clear boundaries:** Features describe user-facing value; capabilities describe technical possibilities; dependencies describe operational requirements; changes describe what changed and when.
4. **Write for users:** Prefer clear, actionable, concise language over implementation jargon. Avoid unnecessary repetition, speculation, and development-process noise.
5. **Preserve consistency:** Ensure claims, terminology, version requirements, and limitations agree across files and with actual project behavior.
6. **Preserve history:** Append new changelog entries in reverse chronological order; never silently rewrite historical facts. Correct inaccuracies explicitly when material.
7. **Treat documentation as part of completion:** A task is not fully complete until applicable documentation is accurate. Do not add changelog entries for documentation-only housekeeping unless meaningful to users.

## Working method
- Be autonomous, resourceful, and evidence-driven. Decompose problems into testable components; form competing hypotheses and design experiments that discriminate between them.
- Use all available sources: web/GitHub/search, open-source implementations, docs, package repos, Linux/RE/debugging tools. Research existing solutions before reinventing.
- Prefer deterministic, reusable scripts (Python on Windows/Linux; Bash for shell integration; other languages only when justified). Use AI to develop the procedure, not to execute it repeatedly at runtime.
- Optimize numeric parameters with bounded search/bisection and adaptive refinement; converge at ~1% relative tolerance; record bounds and best verified result.
- Verify with tests, measurements, and independent evidence. Distinguish verified facts, inferences, and unknowns; never present assumptions as confirmed.
- Persist until the objective is verified or a genuine blocker is established; avoid unproductive loops and summarize exact blockers when stopped.

## Test execution modes
Design recurring automated tasks (tests, validation, diagnostics, benchmarks, sweeps) with three modes via a common `--mode quick|normal|full` option (default `normal`):
- **Quick (≤1 min):** smoke tests, critical paths, representative checks.
- **Normal (≤5 min):** Quick plus broader regressions, edge cases, representative scenarios.
- **Full (unrestricted):** all tests, extended sweeps, stress and expensive checks.
- Progressive coverage (`Quick ⊆ Normal ⊆ Full`); budgets are end-to-end. Prefer repeatable selection, fixed seeds, parallelism where safe, early failure detection.
- Report mode, duration, tests run/skipped, failures, and coverage; distinguish passing tests from untested code. Classify tests by cost/importance; rebalance periodically.
