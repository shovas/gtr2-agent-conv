# AGENTS.md

## Project scope
- New project: conversion scripts from ISIMotor-lineage sim games (rFactor, Race 07, GSC 2013/GSCE, BMW M3 Challenge, Automobilista 1, etc.) to **GTR2**.
- Repo is nascent; keep commands/tooling lightweight and document them here as they are added.

## Commands
- Tests (unittest): `python3 -m unittest discover -s tests -v`

## Key locations
- `../rfactortools/` - inspiration/reference repo (rFactor -> GSC2013 tools, Python package). Read before implementing conversions; reuse patterns where they fit GTR2.
- `../GTR2Steam/` - local GTR2 Steam install (1.6G). **Target-format reference**: real `GameData` layout, `.car/.hdc/.eng/.tyr/.aud/.gdb/.trk`, and `.gtr` GMOTORMAS10 archives. Read-only reference; do not copy into repo.
- `../BMWM3Challenge/` - local BMW M3 Challenge install (369M, moved from in-project to workspace root). **ISIMotor source reference**: 17 `.bmw` GMOTORMAS10 archives (readable by `mas_tool.py`), loose `.gmt/.fxm/.fxa/.lma/.car/.hdc/.eng/.tyr/.trk/.aiw` and media. Read-only reference; do not copy into repo.
- `../GTLSteam/` - local GT Legends Steam install (1.8G). **ISIMotor source reference**: `.CAR` (uppercase) files, `.gtl` GMOTORMAS10 archives, GTL-era GDB/classes. Read-only reference; do not copy into repo.
- `../RF1Vanilla/` - local rFactor 1 vanilla install (1.5G). **ISIMotor source reference**: 85 MAS type-1 `.mas` archives, 9,662 GMTs (9,630 old-layout magic at 0x1D4 + 32 GTR2-style at 0x08), 120 ISI-encrypted GMTs decryptable with `isi_crypt.py` (skip=4). Read-only reference; do not copy into repo.
- `../legacy/` - prior attempt artifacts moved from `tools.unsorted`. Contains ad-hoc probe/phase scripts and small sample fixtures (`aiw_*`, `Brianza_*`). Treat as reference, not authoritative; not part of this repo.
- `../hand_selected/` - hand-picked artifacts recovered from `tools.unsorted.irrelevant`. Small samples: `audtest/default.aud`, `gtr1_sniffnnbe5l6i/.../Mesh.gtr`, `xval_r7/*.car`, `xval_test` (`.gtr/.GMT/.TGA/.JPG`). Large generated output trees are present locally for reference but are outside this repo.
- `../quickbms_scripts/` - large QuickBMS script collection (2745 files). **Format reference**; most relevant is `mas.bms` (GMOTORMAS10/CUBEMAS4/ISI MAS types). Use as spec cross-check; prefer native Python in `rfactortools`/this project for pipeline integration.
- `../MAS2Extract/` - small C# GPLv3 tool for **rFactor 2 MAS2** (`GMOTOR_MAS_2.90`) extraction/deciphering. Useful as rF2-format reference, but not GMOTORMAS10/GTR2/GTL.
- `../gtr2-agent-tools/` - GTR2 driving/UI automation toolkit (CC BY-NC 4.0). **Reference only** for format parsers in `scripts/gtr2_driving/`: `mas.py`, `gmt.py` (mesh table at 0x16C), `trackmap.py` (AIW), `cargears.py` (HDC/ENG/GRB), `pitzones.py` (TRK+MAS). Check license before reusing code.
- `../modding-tools-and-tutorials/` - local third-party modding tools/tutorials collection (131M, gitignored; moved from in-project to workspace root). **Reference only**; includes `GTL2GTR2 Converter v0.9.0.1` (simple ext/TRK-MAS rename only, no AIW/GDB fixes), RacerM rFactor->GTR2 track notes, GMT/hex-editing tutorial hints. Do not commit binaries.
- `~/tmp/tools.unsorted.irrelevant/` - remaining large/generated/irrelevant items (installers, caches, etc.).

## `../rfactortools` facts (verified)
- Python package (`setup.py`, `setuptools`, `version=0.4.0`); C extension `rfactortools/_crypt` from `rfactortools_crypt.cpp` (`SConstruct` also builds `rfactordec.c` and shared lib).
- Core modules: `aiw.py`, `crypt.py`, `gdb.py`, `gmt.py`, `gsc2013.py`, `gtr2.py` (currently GTR2->GSC2013 direction), `img.py`, `mas.py`, `scn.py/scn_parser.py`, `sfx.py`, `util.py`, `veh.py`; CLI entrypoints under `rfactortools/programs/`.
- Tests: `tests/test_*.py` (`unittest`). `SConstruct`: `scons`/default runs flake8 (`python3 -m flake8.run --max-line-length=120`), `scons test` runs `python3 -m unittest discover`, `scons all` runs flake8+pylint+test. `flake.nix` targets nixos-22.05/python310, `doCheck=false`.
- Dependencies in docs/nix: Python 3 + Pillow (`python3-pil`, `python3-pil.imagetk`), tkinter for GUI. README notes Python3.4/Pillow; verify against current environment before relying on old version assumptions.

## Legacy gotchas
- Many `legacy/*.py` scripts hardcode `ROOT="/home/matt_ollama/rfactortools"` and `TMPDIR=/home/matt_ollama/tmp`; that path does not exist in this workspace. Update paths to `../rfactortools` or package imports before reuse.
- Legacy harness/demo scripts import modules/symbols not present in `../rfactortools` as-is (e.g. `rFactorToGTR2`, `Race07ToGTR2`, `gtr2verify`, `convert`, `gmtconvert`). Treat them as evidence of intended API, not working code against current reference repo.
- Legacy contains large sample binaries/data (`.aiw`, `.tga`, `.dds` in sample dirs) kept for reference; avoid copying generated conversion outputs back into git.
