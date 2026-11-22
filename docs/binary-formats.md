# Binary Formats Inventory (GTL/GTR2)

First-pass inventory for GTL (`../GTLSteam/GameData`) and GTR2 (`../GTR2Steam/GameData`). Goal: identify, understand, and provide read/write path for every binary file format possible.

**Legend**
- **R/W**: lossless read/write capability in this repo/tooling, or standard library path.
- **Understanding**: `high` = structure well understood; `medium` = header/container understood, some internals unknown; `low` = identified, internals largely unknown/proprietary.

## Inventory (binary or binary-on-disk)

| Ext | GTL+GTR2 count | Kind | Magic/header (observed) | Understanding | R/W path |
|---|---:|---|---|---|---|
| `.gtl`, `.gtr` | 1113 | Game archive (MAS) | `GMOTORMAS10\0\0\0\0\0` | high | `mas_tool.py` create/list/extract/add/update/delete; round-trip verified on real files |
| `.gmt` | 56 loose (+26931 in archives) | 3D mesh/model | normal: `c8cfd2d8ced8e6c3d6ded8bebba7bf90` at 0x08; obj_list_offset at 0x00 | medium | `gmt_tool.py` info/scan/diff; `gmt_format.py` structural parse/write (header, mesh table, vertex/index blobs, material tail best-effort) with lossless round-trip tests. See `docs/gmt-format.md` |
| `.aiw` | 59 | Text waypoint file (SimBin header has null bytes) | `//[[gMa1.000f...]]` | high (text) | Text read/write; `rfactortools/aiw.py` parses it. Not a binary struct format despite null-padded header |
| `.dsi` | 142 | Gzip-compressed SimBin text | gzip `1f8b08`, payload `//[[gMb1.000f...]]` | high | `gzip_simbin_tool.py` info/extract/create (deterministic gzip). Content round-trip verified |
| `.hat` | 34 | Gzip-compressed SimBin text | gzip `1f8b08`, payload `//[[gMb1.000f...]]` | high | `gzip_simbin_tool.py` info/extract/create. Content round-trip verified |
| `.gtt` | 29 | Gzip-compressed SimBin time-trial/ghost (GTTF payload) | gzip `1f8b08`, payload `//[[gMb1.000f...]]\nGTTF...` | high (container) | `gzip_simbin_tool.py` decompress/compress; content round-trip verified. Internal GTTF record semantics not fully decoded; observed header: magic+f32 ver+u32 len+TRK+u32 len+AIW. |
| `.vcr` | 13 | Gzip-compressed SimBin replay (IRSR payload) | gzip `1f8b08`, payload `//[[gMb1.000f...]]\nIRSR...` | high (container) | `gzip_simbin_tool.py` decompress/compress; content round-trip verified. Internal replay record semantics not fully decoded; observed header: IRSR+f32 ver+u32 len+TRK+u32 len+AIW. |
| `.fxm` | 135 | SimBin 3ds Max animation/export | `FXM ` | medium | `fxm_tool.py` info/nodes/roundtrip; header partially observed (BE fixed-header interpretation can overlap string data), node/bone name strings extractable; internal animation/keyframe semantics not fully decoded |
| `.fxa` | 4 | SimBin animation (FXM family) | `FXA ` | medium | `fxm_tool.py` info/nodes/roundtrip; same container family observations as FXM |
| `.phs` | 5 (in GTL MAS) | Unknown SimBin/ISI binary (AI/physics/drivers/cars/tracks data) | high-entropy, no known magic; not ISI 16-byte-header signature | low | Identified; lossless byte copy possible. Not decryptable by known ISI 16-byte-header scheme; internal format undecoded. |
| `.lma` | 116 | SimBin animation (FXM magic/variant) | `LMA ` observed in GTR2/GT Legends | medium | `fxm_tool.py` info/nodes/roundtrip; node/bone strings extractable; internal structure unconfirmed |
| `.svm` | 258 | SimBin text-like with null padding | `//[[gMa1.000f...]] [[\0...]]` | high (text-ish) | Treat as text/binary-safe bytes; preserve null padding. Not a structured binary format |
| `.ani` | 60 | Text animation/script | `// ...` | high (text) | Plain text read/write |
| `.bik` | 103 | Bink video (proprietary) | `BIKi` / Bink signature | low | Identify header + lossless copy. Full decode/encode requires Bink SDK/tools (proprietary) |
| `.wav` | 1245 | RIFF WAVE audio | `RIFF....WAVEfmt ` | high | Python stdlib `wave` for PCM; MP3-in-WAV (fmt 0x55) lossless copy. Observed in 1245 GTR2/GTL WAVs: PCM (1144) + MP3 0x55 (101). |
| `.dds` | 56 (fs) / 34150 (MAS) | DirectDraw Surface texture | `DDS ` | high (standard) | Standard DDS; identify/parse; DXT1/3/5 + uncompressed RGB(A) semantic R/W in `media_tool.py`. Observed in 20,073 scanned MAS DDS headers: DXT1/DXT3/DXT5 and uncompressed RGB(A) (pf 0x41/0x40). |
| `.tga` | 323 | Targa image | TGA header (e.g. type 2) | high (standard) | Standard TGA; lossless copy possible |
| `.bmp` | 205 | **Mixed**: 145 real BMP (`BM`), 60 TGA-like (`00 00 02 00...`) | `BM` or TGA header | high (standard containers) | Detect by header: if `BM` parse as BMP; if TGA header parse as TGA. Preserve original bytes on round-trip |
| `.jpg` | 93 | JPEG image | `FFD8FFE0` | high (standard) | Standard JPEG; lossless copy possible |
| `.mp3` | 8 | MP3 audio | `ID3` or MPEG frame | high (standard) | Standard MP3; lossless copy possible |
| `.fxa`? (covered) | - | - | - | - | - |

## Text formats observed as text/binary-safe

These are usually text but may contain null-padded SimBin headers: `.aiw`, `.svm`, `.ani`, `.ds`, `.dst`, `.gdb`, `.trk`, `.car`, `.hdc`, `.eng`, `.tyr`, `.aud`, `.dmg`, `.sp`, `.grb`, `.hed`, `.cam`, `.grd`, `.rcd`, `.set`, `.txt`, `.cdb`, `.ddb`, `.tec`, `.fxm`? No - `.fxm` is binary FXM. `.cas` is text-like.

## Game-specific binary formats: status

### Done / strong
- **MAS (`.gtr/.gtl/.mas`)**: full read/write in `mas_tool.py`, tested on real GTR2/GTL archives.
- **DSI/HAT/GTT/VCR**: gzip container understood; `gzip_simbin_tool.py` extracts/creates deterministic payloads (GTTF for GTT, IRSR for VCR).
- **FXM/FXA/LMA**: magic identified (`FXM `/`FXA `/`LMA `), lossless round-trip, heuristic node/bone name extraction; BE header interpretation may overlap string data. Two observed layout families: first string at offset 19 (common in LMA driver skeletons, bone names; 113 files observed with BE u16[1]==257, BE u32[2] in {1,256}, BE u32[3] in {80,184}, BE u32[4]==1, BE u32[5] in {65,66,67,77}) and offset 30 (common in FXA/FXM pit animations, "3D Studio Max..." source string; all 142 offset-30 files observed with BE u16[1]==257, BE u32[2]==4096, BE u32[4]==256, BE u32[5]==528; most contain a source path string within 300 bytes). In sampled GTR2 LMAs, many Bip01 node names are preceded by a 12-byte LE(u32,u32,u32) prefix where third==1 and second matches BE header u32 at offset 8 (semantics unconfirmed). Internal animation/keyframe/node-record structure not fully decoded.

### Partial
- **GMT**: header/mesh table partially decoded (`obj_list_offset`, flags, magic, mesh records, 32-byte vertices, u16 indices + 4-byte lead). Material/object table partially observed. No geometry converter. See `docs/gmt-format.md`.

### Proprietary / standard-external
- **BIK**: Bink proprietary. Can identify (`BIKi` header) and lossless-copy; full decode/encode not practical without licensed tools.
- **DDS/TGA/BMP/JPG/MP3/WAV**: standard formats. Read/write via stdlib/Pillow/external tools; lossless copy always safe.

## Verification commands

```bash
python3 -m unittest discover -s tests -v
python3 mas_tool.py list ../GTR2Steam/GameData/Locations/Anderstorp/Anderstorp.gtr
python3 gmt_tool.py info ../GTR2Steam/GameData/Teams/M-FPDriver.gmt
python3 gzip_simbin_tool.py info ../GTR2Steam/GameData/Locations/HAT_Dedicated/3ANDERSTORP.hat
python3 fxm_tool.py info ../GTR2Steam/GameData/Animations/Pit/FH.FXA
python3 fxm_tool.py nodes ../GTR2Steam/GameData/Animations/Driver/ExtDriver_A.LMA
```
