# Capabilities

Lower-level, technical capability inventory. Status reflects evidence in code/tests/docs, not aspirational goals.

## Archive formats

### MAS / GMOTORMAS10 (`.gtr`, `.gtl`, `.mas`, `.bmw`)
- **Read**: Yes. Parse GMOTORMAS10 container, list entries, extract files.
- **Write**: Yes. Create new archives; add/update/delete entries.
- **Verification**: `tests/test_mas_tool.py`; real GTR2/GTL round-trip tests when reference files present.
- **Tool**: `mas_tool.py`.
- **Notes**: Handles observed GMOTORMAS10 layout used by GTR2/GT Legends. Also verified on the 17 `.bmw` archives in `../BMWM3Challenge` (type 0, member-level round-trip in `tests/test_bmw_m3.py`) and the 50 type-1X Petrobras de Marcas `.mas` archives in `../CopaPetrobrasdeMarcas` (type-1 layout with a different 16-byte signature; signature preserved on rewrite via `signature=` / `read_signature()`).
- **MAS type 2 (Sports Car GT)**: signature-less 8-byte header + 32-byte records; reads/writes all 61 archives in `../SportsCarGtUsa` (`tests/test_scgt.py`). Decodes the 16-byte-header + zlib texture variant; 22 members with an undecoded compression variant are preserved losslessly.
- **MAS type 3 (F1 2002)**: `CUBEMAS4.10` signature; reads/writes all 63 archives in `../F12002` (`tests/test_f12002.py`).
- **MAS type 5 (F1 2000)**: `CUBEMAS2.50` signature, 12-byte magic + 256-byte records; reads/writes all 118 archives in `../F12000` (`tests/test_f12000.py`). Decodes plain-zlib and 16-byte-header+zlib members; 319 undecoded-compression members preserved losslessly.
- **MAS type 6 (F1 2001)**: `CUBEMAS4.00`/`CUBEMAS4.01` signatures, 16-byte header + 256-byte records `(type, offset, size, zsize, crc, name[236])`; reads/writes all 80 archives in `../F12001` with signature preservation (`tests/test_f12001.py`).
- **rF1→GTR2 prototype pipeline**: `rf1_to_gtr2.py` unpacks, decrypts ISI-signed members, applies the structural GMT layout bridge, repacks as type 0 and validates with `gmt_format.py`. Verified on a 253-GMT archive (`tests/test_rf1_pipeline.py`). Geometry semantics remain unvalidated.
- **AIW/SCN text**: `simbin_text_tool.py` parses waypoints/features, SearchPath/MASFile/SkyBoxI (`tests/test_simbin_text_tool.py`). `aiw_for_simbin()` applies documented rFactor→SimBin rules (scale `wp_galpha` by 0.45, drop 12 rFactor-only tags, replace `wp_cheat` with `wp_event=(1.000,0,0)`) from the freeware AIW Repair Utility in `../gtr2-tools` (`tests/test_aiw_convert.py`).
- **GTTF/IRSR**: `simbin_events_tool.py` reads magic/version/TRK/AIW filenames, embedded strings, and metadata framing (driver/co-driver/car: 31/31 GTTF, 4/4 GTL-IRSR, 5/5 rF1-IRSR, 9/9 GTR2-IRSR) across 29 GTT + 9 VCR files; lap/frame record semantics undecoded.
- **Mesh variant headers/tables**: `mts_format.py` parses the shared CUBE MTS 4.10/4.20 header (magic/count/name), the 196-byte submesh descriptor grid, and the real geometry table (8-u32 count/offset header + 64-byte-spaced submesh records resolving vertex/normal offsets) — verified on 129/300 sampled 4.20 files. `race_gmt.py` parses the `RaceGMT\0` header and its 36-byte triangle records. Remaining: material/stage semantics and 4.10 table coverage.

## Coverage gaps (documented, not yet addressed)
- **GTR 2004 corpus available** (`../GTR1Vanilla`) but its GMT magic (`...bba6bf90` at 0x04) is not parsed by `gmt_format.py` — a third layout distinct from GTL/GTR2 and rF1. See `docs/binary-formats.md`.
- **Untested ISI signatures**: `isi_crypt.GAMES` supports 8 signatures but real corpora exist only for rFactor and Game Stock Car; ARCA Sim Racing, Simulador Turismo Carretera, Top Race 2009, Superleague Formula, STC 2012 and Formula Truck have no local corpus.
- See `docs/reuse-rfactortools.md` for reference material that may reduce these gaps.

## Encryption

### ISI/rFactor 16-byte-header encryption (GMT/MAS etc.)
- **Read/Decrypt**: Yes, for known ISI signatures. Pure-Python implementation in `isi_crypt.py` (isi_key/isi_crypt, enctype 0/1, GMT skip=4).
- **Write/Encrypt**: Yes. Can encrypt with known sign/key; round-trip verified.
- **Verification**: `tests/test_isi_crypt.py` (pure-Python round-trip; optional cross-check against `rfactordec` binary).
- **Gaps**: Files without recognized ISI sign/key 16-byte header are not decrypted. `DETOMASO_PANTERA_RAINSCREEN.GMT` is not standard ISI 16-byte-header format; header repair (normal magic/flags) makes it structurally parseable/lossless-round-trippable, but semantic correctness is unverified. Other/unknown variants may require further analysis.
- **Verified real corpus**: 120 rFactor 1 GMTs in `../RF1Vanilla` carry the known rFactor signature and decrypt with skip=4; output matches the `rfactordec` reference byte-for-byte (`tests/test_rf1_vanilla.py`). No GTR2/GTL install file carries a known ISI signature.

## 3D/mesh formats

### GMT (`.gmt`)
- **Read**: Structural/lossless. Parses header (obj_list_offset, flags, 16-byte magic), mesh table at 0x16C, 108-byte mesh records (27*u32), vertex/index blobs, material tail, 4x264-byte stage blocks, ASCII strings.
- **Write**: Lossless structural round-trip. Preserves original bytes for unknown/gap regions; writes known structural fields and data at original offsets.
- **Decoded/verified fields**:
  - Header: `obj_list_offset`, `flags`, magic.
  - Mesh: count/first, `rec[1]` flags, `rec[2]` material index, `rec[3]` vertex count, `rec[4]` vertex offset, `rec[5]` extra block/stream boundary, `rec[6]` vertex end/stream boundary, `rec[7]` stream2 end, `rec[8]` stream3 end, `rec[10]` index count, `rec[11]` index offset.
  - Vertex base 32-byte: `[u32 f0, f32 px,py,pz, f32 nx,ny,nz, u32 f7]` (pos/norm plausible; f0/f7 semantics unconfirmed).
  - 48-byte layout: 32-byte base + 16-byte extra block; extra captured raw.
  - Streams: rec[7]/8 extra 32-byte/vert stream blocks captured raw when present.
  - Materials: L0 boundary heuristic; 264-byte stage blocks; ASCII texture/stage strings extracted.
- **Verification**: `tests/test_gmt_format.py`, `tests/test_gmt_tool.py`; real GTR2/GT Legends samples.
- **Tools**: `gmt_format.py`, `gmt_tool.py`.
- **Gaps**: material/stage numeric param semantics, UV/LOD/shader/flag meanings, f0/f7/extra/stream semantics, and validated geometry conversion. Decryption itself is handled (`isi_crypt.py`, `jca_crypt.py`), but decrypted/old-layout GMTs are not fully semantic-converted. The **old rFactor 1 GMT layout** (magic at 0x1D4 with 0xA8 byte) is not parsed by `gmt_format.py`; 9,630 such files exist in `../RF1Vanilla` (plus ~60k each in Copa/Stock Car Extreme/Automobilista). A prototype structural bridge (`gmt_layout.py`) makes them parseable but its geometry semantics are unvalidated. See `docs/gmt-format.md`.

## SimBin container formats

### DSI/HAT/GTT/VCR (gzip-wrapped)
- **Read**: Yes. Detect gzip, decompress, inspect. GTT contains GTTF payload (time trial/ghost); VCR contains IRSR replay payload.
- **Write**: Yes. Recompress with content round-trip.
- **Verification**: `tests/test_simbin_tools.py` (DSI/HAT/GTT/VCR real-file tests when present).
- **Tool**: `gzip_simbin_tool.py`.
- **Gaps**: GTTF/VCR lap/frame record semantics not decoded; metadata framing (driver/co-driver/car) is decoded for GTTF and GTL-IRSR.

### FXM/FXA/LMA
- **Read**: Header identification + lossless container read. Recognizes observed magics `FXM `, `FXA `, `LMA `. Reports LE/BE header field interpretations (BE fixed-header interpretation can overlap string data; semantics unconfirmed). Decoded skeleton-node table (`parse_node_records`) and per-node TRS keyframes (`decode_node_keys`, 2 keys of position/quaternion/scale + trailer) via `fxm_tool.py keys`; heuristic name extraction retained via `nodes`.
- **Write**: Lossless round-trip.
- **Verification**: `tests/test_simbin_tools.py` (real LMA round-trip, BE-field observation, node-name extraction when present), `tests/test_fxm_records.py` (skeleton table + TRS decode + CLI).
- **Tool**: `fxm_tool.py`.
- **Gaps**: trailer/size_hint/key_count field semantics; writing/modifying animation data.

### JCA (SimBin Race 07 / GTR Evolution / Race Room)
- **Read/Decrypt**: Yes, native in `jca_crypt.py` — all 8 versions, optional zlib layer, XOR 0xEB, custom game keys (`raceroom`, `raceroom_plr`, `volvo`, `old_raceroom`).
- **Write/Encrypt**: Yes, exact inverse; round-trip verified for all versions.
- **Verification**: `tests/test_jca_crypt.py` — byte-for-byte match with `wtcced` on real Race 07 GMTs; 200 sampled GMTs decrypt and parse with `gmt_format.py`.
- **Licensing**: `jca_crypt.py` and `jca_tables.py` are GPLv2 (derived from Luigi Auriemma's published `wtcced` algorithm/tables, user-approved). Other project modules are unaffected.

## Other binary formats

### PHS (GTL MAS, 5 files observed)
- **Read**: Identified (high-entropy physics/AI/track binary, distinct from plain-text `.psh` shaders). Lossless byte copy possible.
- **Write**: Lossless byte copy possible.
- **Verification**: `tests/test_simbin_tools.py`, `tests/test_fixtures.py` (5 files: PHYSICS/CARS/DRIVERS/AI/TRACKS).
- **Gaps**: internal format/encryption undecoded — not ISI 16-byte-header, not JCA (all known keys tried), no standard compression. Follow-up hypothesis (may be another ISIMotor physics container under a different name) recorded in `docs/task-plan.md`.

## Media formats

### WAV
- **Read**: PCM WAVE read via stdlib `wave`; header/params/frames accessible. For unsupported wave formats (e.g. MP3-in-WAV format 0x55), parses fmt chunk metadata.
- **Write**: PCM WAVE write and round-trip; lossless byte-copy round-trip for unsupported stdlib formats.
- **Verification**: `tests/test_media_tool.py` (PCM round-trip; real MP3-in-WAV format 0x55 lossless round-trip when present).
- **Tool**: `media_tool.py`.
- **Gaps**: full semantic decode/encode of compressed WAV payloads (MP3/ADPCM) not implemented.

### DDS
- **Read**: Identify + DDS header/pixel-format/caps semantic parse; DXT1 (BC1), DXT3 (BC2), DXT5 (BC3), and uncompressed RGB(A) mask-based pixel decode to RGBA.
- **Write**: DXT1/DXT3/DXT5 (lossy) and uncompressed RGB(A) mask-based encode from RGBA + DDS file write; lossless byte copy possible.
- **Verification**: `tests/test_media_tool.py` (synthetic DXT1, DXT3, DXT5, A8R8G8B8, X8R8G8B8, R8G8B8, R5G6B5 round-trips).
- **Tool**: `media_tool.py`.
- **Gaps**: BC4/5/6H/7, mipmaps, cube maps, and some uncompressed layouts not fully implemented.

### TGA
- **Read/Write**: Semantic read/write for uncompressed truecolor/grayscale (type 2/3) and RLE truecolor (type 10) via `media_tool.py`. Type 2/3 round-trip is byte-identical; type 10 round-trip is pixel-identical (encoder emits raw packets).
- **Verification**: `tests/test_media_tool.py` (synthetic type 2 byte round-trip, synthetic type 10 pixel round-trip, real type 2 when present).
- **Gaps**: other TGA types/color maps not fully implemented.

### BMP
- **Read/Write**: Semantic read/write for uncompressed BI_RGB 24/32-bit BMP via `media_tool.py` (top-down memory representation, bottom-up file write).
- **Verification**: `tests/test_media_tool.py` (synthetic 24-bit round-trip).
- **Gaps**: compressed/other DIB variants not implemented; BMP-as-TGA quirk detected but routed separately.

### JPG/MP3
- **Read**: Identify; JPG SOF dimension/bit-depth metadata parsed; MP3 frame header fields parsed (version/layer/bitrate/samplerate index, ID3 tag presence).
- **Write**: Lossless byte copy possible.
- **Verification**: `tests/test_media_tool.py` (real JPG/MP3 metadata parsing when present).
- **Tool**: `media_tool.py`.
- **Gaps**: full semantic decode/encode/edit not implemented in-repo.

### BIK (Bink Video)
- **Read**: Identify and parse basic header fields; lossless copy possible.
- **Write**: Lossless copy only.
- **Verification**: `tests/test_media_tool.py` (real-file identification when present).
- **Tool**: `media_tool.py`.
- **Gaps**: proprietary codec; full decode/encode requires proprietary Bink SDK/licensed tools.

## Conversion pipeline

### GTL -> GTR2 end-to-end conversion
- **Status**: Not implemented as a complete, validated pipeline in this repo.
- **Available building blocks**: MAS read/write (all observed variants), GMT structural inspection/round-trip, old→new layout bridge prototype, ISI + JCA decryption, AIW/SCN and GTTF/IRSR readers, DSI/HAT and FXM/FXA/LMA lossless handling, format docs.
- **Verified carry-over**: 57 byte-identical same-name GMTs in Anderstorp GTL/GTR2 archives parse and repack correctly (`tests/test_carryover.py`); a prototype rF1→GTR2 archive pipeline converts a 253-GMT archive (`tests/test_rf1_pipeline.py`).
- **Text-level conversion**: `text_convert.py` applies AIW rules and SCN→TRK SearchPath/MASFile rewrites over a whole rFactor tree; `corpus_diff.py` finds identical/different same-name files across corpora; `validate_materials.py` checks `GRAS`/`GRVL`/`ROAD` prefixes.
- **Missing for full conversion**: validated GMT geometry semantics, vehicle/track config adaptation rules, FXM semantic handling where needed, comprehensive format coverage, and in-game validation workflow.
