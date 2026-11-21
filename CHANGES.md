# Changes

Newest-first change log. Timestamps use repository commit dates (ISO 8601, local offset).

## 2026-11-21 19:45:00 -0500 - FXM/LMA observed node-name evidence
- Add verifiable assertions for observed node-name strings in `ExtDriver_A.LMA` (lossless round-trip unchanged).

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
