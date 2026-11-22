# Binary Formats Inventory (GTL/GTR2)

First-pass inventory for GTL (`../GTLSteam/GameData`) and GTR2 (`../GTR2Steam/GameData`), with cross-game observations from BMW M3 Challenge (`../BMW M3 Challenge`). Goal: identify, understand, and provide read/write path for every binary file format possible.

**Legend**
- **R/W**: lossless read/write capability in this repo/tooling, or standard library path.
- **Understanding**: `high` = structure well understood; `medium` = header/container understood, some internals unknown; `low` = identified, internals largely unknown/proprietary.

## Inventory (binary or binary-on-disk)

| Ext | GTL+GTR2 count | Kind | Magic/header (observed) | Understanding | R/W path |
|---|---:|---|---|---|---|
| `.gtl`, `.gtr`, `.bmw` | 1113 + 17 (BMW M3 Challenge) | Game archive (MAS) | `GMOTORMAS10\0\0\0\0\0` | high | `mas_tool.py` create/list/extract/add/update/delete; round-trip verified on real GTR2/GTL and BMW M3 Challenge `.bmw` archives |
| `.gmt` | 56 loose (+26931 in archives) | 3D mesh/model | normal: `c8cfd2d8ced8e6c3d6ded8bebba7bf90` at 0x08; obj_list_offset at 0x00 | medium | `gmt_tool.py` info/scan/diff; `gmt_format.py` structural parse/write (header, mesh table, vertex/index blobs, material tail best-effort) with lossless round-trip tests. See `docs/gmt-format.md` |
| `.aiw` | 59 | Text waypoint file (SimBin header has null bytes) | `//[[gMa1.000f...]]` | high (text) | Text read/write; `rfactortools/aiw.py` parses it. Observed: all 59 start with `//[[gMa1.000`; contain `[Features]`. Lossless byte round-trip trivial. |
| `.dsi` | 142 | Gzip-compressed SimBin text | gzip `1f8b08`, payload `//[[gMb1.000f...]]` | high | `gzip_simbin_tool.py` info/extract/create (deterministic gzip). Content round-trip verified |
| `.hat` | 34 | Gzip-compressed SimBin text | gzip `1f8b08`, payload `//[[gMb1.000f...]]` | high | `gzip_simbin_tool.py` info/extract/create. Content round-trip verified |
| `.gtt` | 29 | Gzip-compressed SimBin time-trial/ghost (GTTF payload) | gzip `1f8b08`, payload `//[[gMb1.000f...]]\nGTTF...` | high (container) | `gzip_simbin_tool.py` decompress/compress; content round-trip verified. Internal GTTF record semantics not fully decoded; observed header: magic+f32 ver+u32 len+TRK+u32 len+AIW. |
| `.vcr` | 13 | Gzip-compressed SimBin replay (IRSR payload) | gzip `1f8b08`, payload `//[[gMb1.000f...]]\nIRSR...` | high (container) | `gzip_simbin_tool.py` decompress/compress; content round-trip verified. Internal replay record semantics not fully decoded; observed header: IRSR+f32 ver+u32 len+TRK+u32 len+AIW. |
| `.fxm` | 135 | SimBin 3ds Max animation/export | `FXM ` | medium | `fxm_tool.py` info/nodes/roundtrip; header partially observed (BE fixed-header interpretation can overlap string data), node/bone name strings extractable; internal animation/keyframe semantics not fully decoded |
| `.fxa` | 4 | SimBin animation (FXM family) | `FXA ` | medium | `fxm_tool.py` info/nodes/roundtrip; same container family observations as FXM |
| `.phs` | 5 (in GTL MAS) | Unknown SimBin/ISI binary (AI/physics/drivers/cars/tracks data) | high-entropy, no known magic; not ISI 16-byte-header signature | low | Identified; lossless byte copy possible. Not decryptable by known ISI 16-byte-header scheme; internal format undecoded. Observed: entropy ~7.95, no known game signature, ISI enctype 0/1 with embedded key/skip variants does not reduce entropy, no embedded gzip/zlib. Note: 0 files in GTR2/GTL installs carry known ISI 16-byte-header signatures. |
| `.lma` | 116 | SimBin animation (FXM magic/variant) | `LMA ` observed in GTR2/GT Legends | medium | `fxm_tool.py` info/nodes/roundtrip; node/bone strings extractable; internal structure unconfirmed |
| `.svm` | 258 | SimBin text-like with null padding | `//[[gMa1.000f...]] [[\0...]]` | high (text-ish) | Treat as text/binary-safe bytes; preserve null padding. Not a structured binary format |
| `.ani` | 60 | Text animation/script | `// ...` | high (text) | Plain text read/write |
| `.bik` | 137 | Bink video (proprietary) | `BIKi` / Bink signature | low | Identify header + lossless copy. Observed: all 137 GTR2/GTL BIK files start with `BIKi`. Full decode/encode requires Bink SDK/tools (proprietary). |
| `.wav` | 1245 | RIFF WAVE audio | `RIFF....WAVEfmt ` | high | Python stdlib `wave` for PCM; MP3-in-WAV (fmt 0x55) lossless copy. Observed in 1245 GTR2/GTL WAVs: PCM (1144) + MP3 0x55 (101). |
| `.dds` | 56 (fs) / 34150 (MAS) | DirectDraw Surface texture | `DDS ` | high (standard) | Standard DDS; identify/parse; DXT1/3/5 + uncompressed RGB(A) semantic R/W in `media_tool.py`. Observed in 20,073 scanned MAS DDS headers: DXT1/DXT3/DXT5 and uncompressed RGB(A) (pf 0x41/0x40). |
| `.tga` | 323 (fs) / 1157 (MAS) | Targa image | TGA header (e.g. type 2) | high (standard) | Semantic R/W for type 2/3/10 in `media_tool.py`; lossless copy for others. Observed in GTR2/GTL: types 2 and 10. |
| `.bmp` | 207 (fs) / 544 (MAS) | **Mixed on fs**: 147 BMP (`BM`), 60 TGA-header (`00 00 02 00...`, type 2) with `.bmp` extension | `BM` or TGA header | high (standard containers) | Detect by header; semantic R/W for BI_RGB 24/32 BMP in `media_tool.py`; lossless copy for others. Observed BM BMPs: BI_RGB bpp 8/24/32. |
| `.jpg` | 93 | JPEG image | `FFD8FF...` | high (standard) | Identify/metadata parse/lossless copy in `media_tool.py`. Observed: all 93 GTR2/GTL JPGs are baseline SOF0, 8-bit, 3 components. Semantic decode/encode not implemented in-repo. |
| `.mp3` | 24 | MP3 audio | `ID3` or MPEG frame | high (standard) | Identify/metadata parse/lossless copy in `media_tool.py`. Observed: 23/24 have ID3/sync, 1 null-padded (`pitSoundsprivate.mp3`). Semantic decode/encode not implemented in-repo. |
| `.fxa`? (covered) | - | - | - | - | - |

## Text formats observed as text/binary-safe

These are usually text but may contain null-padded SimBin headers: `.aiw`, `.svm`, `.ani`, `.ds`, `.dst`, `.gdb`, `.trk`, `.car`, `.hdc`, `.eng`, `.tyr`, `.aud`, `.dmg`, `.sp`, `.grb`, `.hed`, `.cam`, `.grd`, `.rcd`, `.set`, `.txt`, `.cdb`, `.ddb`, `.tec`, `.fxm`? No - `.fxm` is binary FXM. `.cas` is text-like.

## Game-specific binary formats: status

### BMW M3 Challenge cross-corpus observations (evidence only)
- 17 `.bmw` files are GMOTORMAS10 type-0 archives (2,720 members total), readable and member-level lossless round-trippable with `mas_tool.py` unchanged.
- 976 GMTs (26 loose + 950 inside `.bmw`) all have normal GMT magic.
- 75 FXM-family files (`FXM `/`FXA `/`LMA ` magics) all use known magics; 5 have extension != magic (e.g. `TE_wait-l.FXM` is `LMA `, `FPDriverRHD_M02.LMA` is `FXM `).
- `.psh`/`.vsh` inside archives are plain-text HLSL/PS1.1 shader sources; embedded `.db` is a Windows thumbnail cache. No new binary format found.
- Verification: `tests/test_bmw_m3.py`.

### Done / strong
- **MAS (`.gtr/.gtl/.mas/.bmw`)**: full read/write in `mas_tool.py`, tested on real GTR2/GTL and BMW M3 Challenge archives.
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
