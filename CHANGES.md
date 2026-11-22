# Changes

Newest-first change log. Timestamps use repository commit dates (ISO 8601, local offset).

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
