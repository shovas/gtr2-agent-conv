# Capabilities

Lower-level, technical capability inventory. Status reflects evidence in code/tests/docs, not aspirational goals.

## Archive formats

### MAS / GMOTORMAS10 (`.gtr`, `.gtl`, `.mas`)
- **Read**: Yes. Parse GMOTORMAS10 container, list entries, extract files.
- **Write**: Yes. Create new archives; add/update/delete entries.
- **Verification**: `tests/test_mas_tool.py`; real GTR2/GTL round-trip tests when reference files present.
- **Tool**: `mas_tool.py`.
- **Notes**: Handles observed GMOTORMAS10 layout used by GTR2/GT Legends. Also verified on the 17 `.bmw` archives in `../BMWM3Challenge` (type 0, member-level round-trip in `tests/test_bmw_m3.py`).

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
- **Gaps**: material/stage numeric param semantics, UV/LOD/shader/flag meanings, f0/f7/extra/stream semantics, geometry conversion, encrypted GMT decrypt/encrypt. The **old rFactor 1 GMT layout** (magic at 0x1D4 with 0xA8 byte, bounding box at 0x08) is not parsed by `gmt_format.py`; 9,630 such files exist in `../RF1Vanilla` and need a structural converter. See `docs/gmt-format.md`.

## SimBin container formats

### DSI/HAT/GTT/VCR (gzip-wrapped)
- **Read**: Yes. Detect gzip, decompress, inspect. GTT contains GTTF payload (time trial/ghost); VCR contains IRSR replay payload.
- **Write**: Yes. Recompress with content round-trip.
- **Verification**: `tests/test_simbin_tools.py` (DSI/HAT/GTT/VCR real-file tests when present).
- **Tool**: `gzip_simbin_tool.py`.
- **Gaps**: GTTF/VCR internal record semantics not fully decoded.

### FXM/FXA/LMA
- **Read**: Header identification + lossless container read. Recognizes observed magics `FXM `, `FXA `, `LMA `. Reports LE/BE header field interpretations (BE fixed-header interpretation can overlap string data; semantics unconfirmed). Heuristic node/bone name extraction (`nodes`/`extract_strings`).
- **Write**: Lossless round-trip.
- **Verification**: `tests/test_simbin_tools.py` (real LMA round-trip, BE-field observation, node-name extraction when present).
- **Tool**: `fxm_tool.py`.
- **Gaps**: internal animation/keyframe/node/bone semantics.

## Other binary formats

### PHS (GTL MAS, 5 files observed)
- **Read**: Identified (high-entropy binary). Lossless byte copy possible.
- **Write**: Lossless byte copy possible.
- **Verification**: `tests/test_simbin_tools.py` (confirms not decryptable by known ISI 16-byte-header scheme).
- **Gaps**: internal format/encryption undecoded.

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
- **Available building blocks**: MAS read/write, GMT structural inspection/round-trip, DSI/HAT and FXM/FXA/LMA lossless handling, format docs.
- **Missing for full conversion**: validated GMT semantic conversion where needed, vehicle/track config adaptation rules, encrypted GMT handling, FXM semantic handling where needed, comprehensive format coverage, and in-game validation workflow.
