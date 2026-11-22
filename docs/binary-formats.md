# Binary Formats Inventory (GTL/GTR2)

First-pass inventory for GTL (`../GTLSteam/GameData`) and GTR2 (`../GTR2Steam/GameData`), with cross-game observations from BMW M3 Challenge (`../BMWM3Challenge`), rFactor 1 vanilla (`../RF1Vanilla`), Copa Petrobras de Marcas (`../CopaPetrobrasdeMarcas`), Sports Car GT (`../SportsCarGTUsa`), Automobilista (`../Automobilista`), F1 2002 (`../F12002`) and F1 Challenge 99-02 (`../F1C`). Goal: identify, understand, and provide read/write path for every binary file format possible.

**Legend**
- **R/W**: lossless read/write capability in this repo/tooling, or standard library path.
- **Understanding**: `high` = structure well understood; `medium` = header/container understood, some internals unknown; `low` = identified, internals largely unknown/proprietary.

## Inventory (binary or binary-on-disk)

| Ext | GTL+GTR2 count | Kind | Magic/header (observed) | Understanding | R/W path |
|---|---:|---|---|---|---|
| `.gtl`, `.gtr`, `.bmw`, `.mas` | 1113 + 17 + 85 + 50 + 61 | Game archive (MAS) | type0 `GMOTORMAS10`, type1 `c8cfd2d8...`, type1X `cec3d5c7c0d9e6c9...`, type2 (no signature) | high | `mas_tool.py` create/list/extract/add/update/delete; round-trip verified on all corpus variants; type-1X signature preserved on rewrite |
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

### F1 Challenge 99-02 (ISI, 2003) cross-corpus observations (evidence only, `../F1C`)
- 197 `.mas` archives use MAS type 3 (`CUBEMAS4.10`); 21,977 members total. `mas_tool.py` reads/writes them.
- 14,834 `.mts` members: 13,769 with standard `CUBE_MTS_4.10\0\0\0` magic, 1,065 with an object-level header variant (unconfirmed semantics). 128 `.anm` animations start with an 8-character name and are not parsed.
- No file carries a known ISI 16-byte-header signature; no encrypted MAS members.
- F1C is the direct rFactor predecessor; its mesh format is still CUBE MTS (GMT appears in rFactor 1).
- Verification: `tests/test_f1c.py`.

### F1 2002 (ISI, 2002) cross-corpus observations (evidence only, `../F12002`)
- 63 `.mas` archives use the MAS type-3 signature `CUBEMAS4.10\0\0\0\0\0` (19,235 members). `mas_tool.py` reads and writes all 63 with member-level round-trip verified. This review fixed a latent struct-format bug in type-3 writing.
- 13,100 `.mts` mesh members: 12,640 start with `CUBE_MTS_4.10\0\0\0` (CUBE-era ancestor of GMT); 460 start with an object-level record (`u32 count` + name) and have an undecoded header variant. MTS internals are not otherwise decoded.
- No filesystem file carries a known ISI 16-byte-header signature; no encrypted MAS members observed.
- Other formats are text or known families (`.veh` `\r\nHDVehi`, `.hdv`, `.scn` `CUBEASF`, `.aiw`, `.dst`, `.cin`, `.bmp/.tga/.jpg/.wav/.bik`).
- Verification: `tests/test_f12002.py`.

### Automobilista (Reiza, 2016) cross-corpus observations (evidence only, `../Automobilista`)
- 470 `.mas` archives all use the standard MAS type-1 signature (header-only scan).
- 470 archives hold 111,943 members, of which 91,974 are GMTs. Encrypted members use the Game Stock Car signature `0x4b1dca9f960524e8` (enctype 1), decryptable with `isi_crypt.py` skip=4. A real member (`AdelaideMesh.MAS::ADVERTISEMENT001.GMT`) matches `rfactordec` byte-for-byte.
- All 91,974 GMTs use the **old-style magic** `...bba8bf90` at 0x1D4 (91,962 GSC-encrypted + 12 plain). Despite being the newest source game here, Automobilista keeps the old rF1-era GMT layout — same structural gap for GTR2 conversion as rF1/Copa.
- Verification: `tests/test_ams.py`.

### Sports Car GT (1999) cross-corpus observations (evidence only, `../SportsCarGTUsa`)
- 61 `.mas` archives have no 16-byte magic; they use the MAS type-2 layout from `quickbms_scripts/mas.bms`: 8-byte header `(count, data_size)`, then `count` 32-byte records `(name[16], offset, size, zsize, dummy)`, data starting at `8 + 32*count`. `mas_tool.py` now reads and writes this layout (16,070 members).
- Member compression variants observed: 13,621 raw (`size == zsize` or `zsize == 0`), 2,427 with a 16-byte texture header `(width, height, flags, 0)` followed by a zlib stream of raw pixels (decoded by `mas_tool.py`), and 22 with an undecoded compression variant (stored losslessly, `Entry.type == 2`).
- One archive (`WPEDIT.MAS`) has a malformed `zsize` on one member; data is preserved but `zsize` is normalized on rewrite.
- Verification: `tests/test_scgt.py`.

### Copa Petrobras de Marcas cross-corpus observations (evidence only, `../CopaPetrobrasdeMarcas`)
- 50 `.mas` archives use the MAS type-1X signature `cec3d5c7c0d9e6c9caddd8bebba6bf90` (documented as `MAS_TYPE1X` in `quickbms_scripts/mas.bms`: type-1 layout, first 6 bytes differ). All now read with `mas_tool.py`; signature preserved on rewrite (16,026 members total).
- 13,679 members carry the Game Stock Car ISI signature `0x4b1dca9f960524e8` (enctype 1): 12,990 `.gmt`, 649 `.dds`, 31 `.tga`, 9 `.bmp`. `isi_crypt.decrypt_bytes(data, skip=4)` matches `rfactordec` byte-for-byte on `commonmaps.MAS::STARTBOX.GMT` (first real-file validation of the enctype-1 path).
- All 12,990 GMT members are GSC-signature encrypted and, after decryption, use the old rF1-style magic `...bba8bf90` at 0x1D4 — none use the GTR2-style 0x08 layout. This Reiza-era game therefore needs the same old-layout converter as rFactor 1.
- Note: block-aligned prefix decryption must preserve `(len - 20) % 128` for enctype 1, otherwise the keystream alignment shifts.
- Verification: `tests/test_mas_tool.py` (type-1X), `tests/test_copa.py` (GSC decryption + all-GMT layout).

### rFactor 1 vanilla cross-corpus observations (evidence only, `../RF1Vanilla`)
- 85 `.mas` archives use the MAS type-1 signature (`c8cfd2d8ced8e6c9caddd8bebba6bf90`); all open with `mas_tool.py` (13,075 members).
- 9,662 GMT members: 9,630 old-layout (magic `...bba8bf90` at 0x1D4, bounding box at 0x08) and 32 new-layout (GTR2/GTL magic `...bba7bf90` at 0x08). The 32 new-layout files parse and round-trip with `gmt_format.py`; see `docs/gmt-format.md`.
- 120 GMT members are ISI 16-byte-header encrypted with the known rFactor signature; `isi_crypt.py` decrypts them with skip=4 (verified byte-for-byte against `rfactordec`). 90 are old-layout, 30 new-layout after decryption.
- Verification: `tests/test_rf1_vanilla.py`.

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
