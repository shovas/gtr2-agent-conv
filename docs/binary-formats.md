# Binary Formats Inventory (GTL/GTR2)

First-pass inventory for GTL (`../GTLSteam/GameData`) and GTR2 (`../GTR2Steam/GameData`), with cross-game observations from BMW M3 Challenge, rFactor 1 vanilla, Copa Petrobras de Marcas, Sports Car GT, Automobilista, F1 Championship Season 2000 / F1 2000 / F1 2001 / F1 2002 / F1 Challenge 99-02, Game Stock Car, NASCAR SimRacing / Thunder 2003 / Thunder 2004, Stock Car Extreme, Race 07 (vanilla + complete/DLC), Volvo and a third-party Race 07 decryptor binary. Goal: identify, understand, and provide read/write path for every binary file format possible.

**Legend**
- **R/W**: lossless read/write capability in this repo/tooling, or standard library path.
- **Understanding**: `high` = structure well understood; `medium` = header/container understood, some internals unknown; `low` = identified, internals largely unknown/proprietary.

## Inventory (binary or binary-on-disk)

| Ext | GTL+GTR2 count | Kind | Magic/header (observed) | Understanding | R/W path |
|---|---:|---|---|---|---|
| `.gtl`, `.gtr`, `.bmw`, `.mas` | all reviewed corpora | Game archive (MAS) | type0 `GMOTORMAS10`, type1 `c8cfd2d8...`, type1X `cec3d5c7c0d9e6c9...`, type2 (no signature), type3 `CUBEMAS4.10`, type5 `CUBEMAS2.50`, type6 `CUBEMAS4.00/4.01` | high | `mas_tool.py` create/list/extract/add/update/delete; round-trip verified on all corpus variants; signatures preserved on rewrite |
| `.gmt` | 56 loose (+26931 in GTL/GTR2 archives; ~100k more across other corpora) | 3D mesh/model | new layout: `c8cfd2d8...bba7bf90` at 0x08; old layout: `...bba8bf90` at 0x1D4; JCA header `0fb1ffff`; DLC header `RaceGMT\0` | medium | `gmt_tool.py`/`gmt_format.py` structural parse/write for the new layout; `isi_crypt.py`/`jca_crypt.py` decrypt; `gmt_layout.py` prototype old→new bridge (semantics unvalidated). See `docs/gmt-format.md` |
| `.aiw` | 59 (GTL/GTR2) | Text waypoint file (SimBin header has null bytes) | `//[[gMa1.000f...]]` | high (text) | `simbin_text_tool.py aiw` parses waypoints/features; lossless byte round-trip trivial. Observed: all 59 start with `//[[gMa1.000`; contain `[Features]`. |
| `.dsi` | 142 | Gzip-compressed SimBin text | gzip `1f8b08`, payload `//[[gMb1.000f...]]` | high | `gzip_simbin_tool.py` info/extract/create (deterministic gzip). Content round-trip verified |
| `.hat` | 34 | Gzip-compressed SimBin text | gzip `1f8b08`, payload `//[[gMb1.000f...]]` | high | `gzip_simbin_tool.py` info/extract/create. Content round-trip verified |
| `.gtt` | 29 | Gzip-compressed SimBin time-trial/ghost (GTTF payload) | gzip `1f8b08`, payload `//[[gMb1.000f...]]\nGTTF...` | high (container) | `gzip_simbin_tool.py` decompress/compress; `simbin_events_tool.py` reads magic/version/TRK/AIW/strings. Lap/frame record semantics undecoded. |
| `.vcr` | 13 | Gzip-compressed SimBin replay (IRSR payload) | gzip `1f8b08`, payload `//[[gMb1.000f...]]\nIRSR...` | high (container) | `gzip_simbin_tool.py` decompress/compress; `simbin_events_tool.py` reads magic/version/TRK/AIW/strings. Frame record semantics undecoded. |
| `.fxm` | 135 | SimBin 3ds Max animation/export | `FXM ` | medium | `fxm_tool.py` info/nodes/roundtrip; header partially observed (BE fixed-header interpretation can overlap string data), decoded skeleton-node table + TRS keyframes via `parse_node_records()` / `decode_node_keys()`, exposed by `fxm_tool.py keys`; trailer semantics unconfirmed |
| `.fxa` | 4 | SimBin animation (FXM family) | `FXA ` | medium | `fxm_tool.py` info/nodes/roundtrip; same container family observations as FXM |
| `.phs` | 5 (in GTL MAS) | SimBin physics/AI binary (PHYSICS/CARS/DRIVERS/AI/TRACKS; distinct from `.psh` shaders) | high-entropy, no known magic | low | Identified; lossless byte copy possible. Not ISI 16-byte-header, not JCA (all keys tried). Bounded 2026-11-23 probe: no zlib/gzip/lzma/bz2 stream at any skip 0..64 and no repeating-key XOR signal (index of coincidence ~0.0039, i.e. random) across key lengths 2..32. Pairwise XOR of the 5 files retains ~7.99 bits/byte entropy (no shared keystream). No local tool or online source documents the format. Follow-up hypothesis recorded in `docs/task-plan.md`. |
| `.lma` | 116 | SimBin animation (FXM magic/variant) | `LMA ` observed in GTR2/GT Legends | medium | `fxm_tool.py` info/nodes/roundtrip; node/bone strings extractable; internal structure unconfirmed |
| `.svm` | 258 | SimBin text-like with null padding | `//[[gMa1.000f...]] [[\0...]]` | high (text-ish) | Treat as text/binary-safe bytes; preserve null padding. Not a structured binary format |
| `.ani` | 60 | Text animation/script | `// ...` | high (text) | Plain text read/write |
| `.bik` | 137 | Bink video (proprietary) | `BIKi` / Bink signature | low | Identify header + lossless copy. Observed: all 137 GTR2/GTL BIK files start with `BIKi`. Decode is available via ffmpeg (`media_tool.py bink-decode`, `binkvideo` decoder verified on real files); BIKi encoding is available via the LGPL-2.1 `raynorpat/libbink` `bink_build` tool (`media_tool.py bink-encode`); a decoded-then-re-encoded real GTR2 BIK passed `--verify` and ffmpeg decode with a compatible BIKi header. `bink_build` is an external executable (code not copied here). `marcussacana/Bink2` targets Bink 2, not GTR2 Bink 1. |
| `.wav` | 1245 | RIFF WAVE audio | `RIFF....WAVEfmt ` | high | Python stdlib `wave` for PCM; MP3-in-WAV (fmt 0x55) lossless copy. Observed in 1245 GTR2/GTL WAVs: PCM (1144) + MP3 0x55 (101). |
| `.dds` | 56 (fs) / 34150 (MAS) | DirectDraw Surface texture | `DDS ` | high (standard) | Standard DDS; identify/parse; DXT1/3/5 + uncompressed RGB(A) semantic R/W in `media_tool.py`. Observed in 20,073 scanned MAS DDS headers: DXT1/DXT3/DXT5 and uncompressed RGB(A) (pf 0x41/0x40). |
| `.tga` | 323 (fs) / 1157 (MAS) | Targa image | TGA header (e.g. type 2) | high (standard) | Semantic R/W for type 2/3/10 in `media_tool.py`; lossless copy for others. Observed in GTR2/GTL: types 2 and 10. |
| `.bmp` | 207 (fs) / 544 (MAS) | **Mixed on fs**: 147 BMP (`BM`), 60 TGA-header (`00 00 02 00...`, type 2) with `.bmp` extension | `BM` or TGA header | high (standard containers) | Detect by header; semantic R/W for BI_RGB 24/32 BMP in `media_tool.py`; lossless copy for others. Observed BM BMPs: BI_RGB bpp 8/24/32. |
| `.jpg` | 93 | JPEG image | `FFD8FF...` | high (standard) | Identify/metadata parse/lossless copy in `media_tool.py`. Observed: all 93 GTR2/GTL JPGs are baseline SOF0, 8-bit, 3 components. Semantic decode/encode not implemented in-repo. |
| `.mp3` | 24 | MP3 audio | `ID3` or MPEG frame | high (standard) | Identify/metadata parse/lossless copy in `media_tool.py`. Observed: 23/24 have ID3/sync, 1 null-padded (`pitSoundsprivate.mp3`). Semantic decode/encode not implemented in-repo. |

## Text formats observed as text/binary-safe

These are usually text but may contain null-padded SimBin headers: `.aiw`, `.svm`, `.ani`, `.ds`, `.dst`, `.gdb`, `.trk`, `.car`, `.hdc`, `.eng`, `.tyr`, `.aud`, `.dmg`, `.sp`, `.grb`, `.hed`, `.cam`, `.grd`, `.rcd`, `.set`, `.txt`, `.cdb`, `.ddb`, `.tec`, `.fxm`? No - `.fxm` is binary FXM. `.cas` is text-like.

## Game-specific binary formats: status

### Wave 2 tooling (GTTF/IRSR + rF1 pipeline)
- `simbin_events_tool.py` reads GTTF/IRSR magic, f32 version (1.0 / 1.05), u32-length TRK and AIW filenames, and embedded ASCII strings. Verified across all 29 GTT and 9 VCR files. `simbin_events_tool.find_frame_grid()` / `read_frames()` locate GTTF frame records: 252-byte stride, f32 position at +0 and a monotonic f32 timestamp at +20, with the grid start varying by metadata length. Validated on 6 time trials (215 frames spanning 45.09s for a 45.297s lap); exposed by `simbin_events_tool.py --frames`. Remaining frame fields are uninterpreted. Metadata framing after the AIW name is now decoded: an 11-byte prefix, then 1-byte-length Pascal name(s) and a NUL-terminated car filename. GTTF files hold driver + co-driver + car (31/31 across GTR2 and BMW M3); GTL-IRSR holds driver + car (4/4). GTR2-IRSR is decoded by `parse_gtr2_irsr_metadata()`: 11-byte prefix, 5-byte field, two 1-byte-length names (team, driver), then a NUL-terminated car filename (9/9 GTR2 replays; exposed as `EventFile.team`). rF1-IRSR is decoded by `parse_rf1_metadata()`: four u32-length strings (mod `.rfm`, empty, `.SCN`, `.AIW`), a fixed 9-byte prefix, then a 1-byte-length driver name and NUL-terminated vehicle/skin names (5/5 RF1Vanilla replays). `EventFile.driver/co_driver/car` and `simbin_events_tool.py` CLI expose it.- `rf1_to_gtr2.py` implements unpack → ISI decrypt → structural layout bridge → type-0 repack → `gmt_format` validation. A 253-GMT rF1 archive converts and repacks successfully. Geometry semantics of the bridge are unvalidated.

### Reference-material mining and loose-extension survey (task plan #1/#2/#4)
- `docs/reuse-rfactortools.md` records ready-made parsers in `../rfactortools` (AIW, SCN, SFX, VEH, full rFactor→GSC2013 conversion pipeline) and the RacerM/GTL2GTR2 tutorial rules: material prefixes `GRAS`/`GRVL`/`ROAD`, SCN→TRK SearchPath/MASFile rewrites, SkyBoxI block replacement, DDS-only textures.
- JCA is not limited to GMTs: Race 07 has 64 encrypted `.cam`, 47 `.gdb`, 41 `.trk`, 41 `.scn`; Volvo has 11/9/2/1 of the same. All decrypt with `jca_crypt.py` (volvo key for Volvo) to valid text (`CUBEASF`, `StaticCam=`, `ApplicationTitle=`).
- Loose-extension survey: `.pf` (5) are ICC colour profiles (`KCMS`); `.map` (16) start with GUID bytes; `.sdt` (51) high-entropy audio tables; `.tgq` (22) `SCHl` header; `.cch` (20) SimBin text; `.dat` (475) MPEG audio (`fff3c4c4`); `.hdr` (1,763) audio headers with varied `0xffff00XX` prefixes.
- Verification: `tests/test_fixtures.py`, expanded `tests/test_race07.py` / `tests/test_volvo.py`.

### Volvo (SimBin, ISIMotor) cross-corpus observations (evidence only, `../VolvoTheGame`)
- 2,026 loose GMTs all use JCA encryption (`0fb1ffff`) with the non-default **volvo key**. `jca_crypt.decrypt_bytes(data, custom_key=jca_crypt.CUSTOM_KEYS["volvo"])` yields standard GTR2-layout GMTs; 200 sampled files parse and round-trip with `gmt_format.py`.
- Animations are plain FXM (22), FXA (14), LMA (6) — no extension/magic mismatch here.
- Verification: `tests/test_volvo.py`.

### F1 2001 (ISI, 2001) cross-corpus observations (evidence only, `../F12001`)
- 80 `.mas` archives use MAS type 6 (`CUBEMAS4.01\0...` in 56, `CUBEMAS4.00\0...` in 24): 16-byte signature, u32 count at 0x10, u32 data_size at 0x14, then 256-byte records `(u32 type, offset, size, zsize, crc, name[236])` starting at 0x18. Data sequential after the table; 16,720 members.
- `mas_tool.py` type 6 reads/writes all 80 archives, preserving the original signature. Decodes plain-zlib and 16-byte-header+zlib members; `size` semantics differ by member type (textures exclude the header, meshes include it).
- Verification: `tests/test_f12001.py`.

### NASCAR Thunder 2003 (ISI, 2002) cross-corpus observations (evidence only, `../NT2003`)
- 179 MAS type-3 archives, 19,006 members; 10,397 `.mts` meshes (10,206 standard `CUBE_MTS_4.10` magic, 191 object-level header variants). No known ISI encryption signatures.
- 476 `.hdr` audio headers paired with 476 `.dat` MPEG-audio files (`fff3`/`fffb` frame sync); 70 `.veh` (`\r\nHDVehi`) and 70 `.hdv` (`\r\n//`) text files.
- Verification: `tests/test_nt2003.py`.

### Race07Complete (Race 07 + DLC: WTCC, STCC, Race On, GTR Evolution) — evidence only
- 12G, 122,292 files; `GameData` contains DLC markers `GTR_Evo.gdb`, `Stcc.gdb`, `SIM_OFFICIAL.gdb`, and many STCC/WTCC/Camaro/Volvo directories.
- 66,186 loose `.gmt` files in **three** variants (sampled 1,000: ~693 JCA-encrypted, ~294 standard new-layout magic at 0x08, ~13 `RaceGMT\0`).
- New format `RaceGMT\0`: 8-byte magic, u32 ASCII name length, name bytes, then float payload. 643 files observed (trees, people, track props from DLC tracks like MidOhio/Zolder09/Marrakech). Internal mesh structure not decoded — only header verified.
- JCA-encrypted GMTs decrypt with `jca_crypt.py` default key to standard new-layout GMTs (verified). 80 `.gdb`, 66 `.trk`, 57 `.scn`, 141 `.cam` are also JCA-encrypted.
- 2 MAS type-0 `.gtr` archives.
- Verification: `tests/test_race07_complete.py`.

### Partial decoding of new mesh variants (task 4)
- `CUBE_MTS_4.10` and `CUBE_MTS_4.20` share a verified header: `magic[16], u32 object_count, char name[8]` (`mts_format.py`, 4,200+ sampled meshes in `../NascarSimRacing`). Payload after 0x1C remains undecoded; same-name files across versions have unrelated sizes, so it is not a magic-only difference.
- `RaceGMT\0` (643 DLC files in `../Race07Complete`) has a verified header: `magic[8], u32 name_len, name, u32 flags=0x04000020, 12+ bounding-box/vertex floats` (`race_gmt.py`). Same-size file diffs (e.g. `PEOPLE_STAND_01/02`) reveal a single **36-byte** record grid (3 × (x,y,z) position triples); all differing bytes align to 4-byte slots within it. Earlier 64-byte run gaps were alternating differing records, not a second section. Payload starts at `16 + name_len` (unaligned); `race_gmt.read_positions()` is an **experimental raw-grid reader**, not a validated triangle decoder: sampled blocks contain mixed position, UV, index and material data, and ASCII stage strings (`L0DIFFUSET0`, `PESSOAS_E`, …) appear at 0x30AF in `PEOPLE_STAND_01` inside the nominal grid. All 643 RaceGMT files contain such ASCII material strings. In `PEOPLE_STAND_01` the 20 strings form exactly 5 groups of 4 (material name + 3 stage names with `L0`/`L1`/`L2` prefixes), validated by test — material/stage grouping is confirmed; `race_gmt.read_material_blocks()` resolves 264-byte stage records; the u32 at +256 is a **stage-type enum** driven by the stage name, and `build_stage_type_map()` builds the mapping. RaceGMT-only corpus (643 files, 4,603 blocks): `L0DIFFUSET0`→1, `L1DIFFUSET0`→2, `L2*`→0, `L0CMAPT0`→3, `L1BUMPSPECMAPT0`→5, `L1CMAPT0`→7; all 6 well-sampled names are 100% deterministic. The u32 at +260 is a per-material **texture-channel index**, decoded by `race_gmt.decode_stage_channels()` (stages grouped by contiguous 264-byte stride via `group_stages()`). Across 1,535 material groups, all 1,534 L2 stages use channel 0; L0/L1 channels fall in {0,1,3,4,5,6}. Concrete group: (L0DIFFUSET0,type1,ch4), (L1BUMPSPECMAPT0,type5,ch5), (L2BUMPSPECMAPT0,type0,ch0) in building01_loda.gmt; a DIFFUSE material instead uses channel 1 for L0/L1. Note: the same 264-byte stage structure also appears in new-layout GMTs, but with different type values (e.g. `L1BUMPSPECMAPT0`→7), a clean 800-file sample gives `L1BUMPSPECMAPT0`→5, `L1SPECULART0`→4, `L0DIFFUSET0`→1. `gmt_format.build_stage_type_map()` mirrors this for new-layout GMTs (L0DIFFUSET0→1, L1BUMPSPECMAPT0→5, L1SPECULART0→4). Type maps must be built per format (earlier mixed-format probes gave misleading values). Earlier "triangle soup" interpretation is withdrawn.
- CUBE MTS 4.20 same-size file diffs reveal a **48-byte** record grid; differing fields cluster at record offsets 36 and 44 for some pairs, but this is a **weak** pattern: on the largest same-size pair only ~23% of differing bytes align to that grid, and sampled field values mix integer-like and float data. Treat the 48-byte grid as unconfirmed rather than a vertex table. The real geometry table was found instead: `mts_format.parse_mesh_table()` locates an 8-u32 header `(object_count, object_offset, vertex_count, vertex_offset, normal_count, normal_offset, index_count, index_offset)` and per-submesh records `(marker, index, count_a, offset_a, count_b, offset_b, ...)` spaced 64 bytes apart — marker 129 for 4.20, 130 for 4.10. In `LIGHTBOX02.MTS` the table is at 0x500 with header `(5, 328, 118, 648, 97, 4896, 0, 6448)` and 5 submeshes. The 8-u32 header resolves in 200/200 sampled files of each variant. `mts_format.read_geometry()` decodes real geometry blocks using strides derived from consecutive offsets: vertices 36 bytes (3 position triples), normals 16 bytes (3 floats + u32) in 200/200 sampled files of each variant; LIGHTBOX02.MTS yields 118 vertices / 97 normals. The table's last u32 is the **end of the normal block** (`noff + ncount*16`, verified on JACK.MTS and 200 sampled files), not an index offset — bytes there decode as floats, so no u16 index block exists in this layout. The bytes immediately after the normal block are float data (validated in `tests/test_mts_format.py`), i.e. additional geometry arrays rather than indices. Two submesh-record layouts are decoded: marker-based 64-byte records (129/130) and an alternate count/offset record at table+48 `(count_a, 0, count_b, offset_b, count_c, offset_c, 0, 0)` (e.g. `CROWD.MTS`). With both, 198/200 (4.20) and 200/200 (4.10) sampled files expose submesh records. A long run of plausible float triples in `TLRA.MTS` was also rejected as a normal array (only 140/814 triples are unit-length), so vertex/normal table location remains unresolved. Uppercase ASCII submesh names are extractable from the payload of both variants and in 644/800 sampled 4.20 files (and 130/200 sampled 4.10 files) `object_count - len(names) == 1` (correlation only). In `LIGHTBOX02.MTS` the four names sit at offsets 216/412/608/804 — a verified **196-byte descriptor stride** (`mts_format.submesh_descriptors()`), observed as the dominant name spacing in 206/300 sampled 4.20 files. Field at descriptor+32 is a packed u32: high 16 bits are `0x4890` (1,953/2,001) or `0x2890` (48), low 16 bits are small (0/2/32/96/2048/2080) — `mts_format.descriptor_fields()`. Field at descriptor+164 is mostly one of three states (`0x00000000` ~1038/2001, `0x0B4CE680` ~521, `0xFFFFFFFF` ~381; `mts_format.descriptor_tail_u32()`), semantics unconfirmed. Same-name pair diffs at +32/+164 showed changes only in the last descriptors and did not resolve into vertex/index file offsets (tested and documented as unresolved). The 48-byte blocks are **not** simple position triples: sampled records contain float values >1e5 incompatible with coordinates (negative-result test in `tests/test_mts_format.py`). 4.10 material records are also decoded: `mts_format.parse_material_records()` resolves 36-byte records with markers 128+index and a 1.0f field (TIREMANFRONT.MTS: records at 0x1A68, stride 36; present in 22/293 sampled 4.10 files). `mts_format.decode_material_numbers()` splits the 4.10 material-record packed u32 into two u16 values; all three resulting numbers are <1024 in 1,227 sampled records. They are stable across same-name files (79/79 identical for TIREMANFRONT/TIREMANBACK), suggesting asset-level material IDs. Across TIREMANFRONT.MTS they span 68 distinct values in 313..442, but no contiguous ID table exists in the file, so they reference an external material table not present in the corpus. Further evidence: `mts_format.rig_table_signature()` shows the triple tables are **shared per rig**, not per mesh — 22 files with these records yield only 4 distinct tables (9 pit-crew meshes, 8 R_ARM/R_TGT, 4 L_ARM, 1 JET), and triples often form consecutive integers (31/79) with adjacent records sharing a value (43/78). The records are therefore a shared skeleton/rig table, not material IDs; their exact semantics remain unconfirmed.

### GTR 2004 (GTR1) — previously missing target corpus (evidence only)
- 430 MAS type-0 `.gtr` archives, 1.2G; sampled 60 archives / 34,385 members (mostly `.gmt`/`.dds`). No ISI encryption signatures.
- 33,477 GMTs have a **third magic** `c8cfd2d8ced8e6c3d6ded8bdbba6bf90` at **0x04** (vs 0x08 in GTL/GTR2 with `...bba7bf90`, and 0x1D4 in rF1 with `...bba8bf90`). 3 files use `OR_GMT_1.00`. `gmt_format.py` does not parse this layout. The header differs by a 4-byte shift (u32 size-like field at 0x00, magic at 0x04); no new-layout 8-u32 geometry table pattern exists anywhere in the first 0x400 bytes, so it needs a dedicated parser. `gmt_semantic.read_gtr1_descriptors()` decodes the 64-byte descriptor grid at 0x194 `(vertex_count, vertex_offset, index_count, index_offset)`; valid in 184/300 sampled files (others use a different header variant). Vertex blocks are 32-byte records and index blocks u16 arrays after a 4-byte lead; vertex-field semantics remain undecoded. GTR1 is a reference corpus, not a conversion target.
- Verification: `tests/test_gtr1_vanilla.py`.

### Game Stock Car / NASCAR SimRacing / F1CS2000 (evidence only)
- `F1CS2000/` is a byte-identical copy of `F12000/` (all 570 files MD5-match) — no new formats.
- `GameStockCar/`: 48 MAS type-1 archives, 19,995 members; 19,987 GSC-signature encrypted; sampled GMTs all use the old 0x1D4/0xA8 layout (same as Copa/SCE/AMS).
- `NascarSimRacing/`: 311 MAS type-3 archives, 36,716 members; 26,473 `.mts` meshes use **two magic versions**: `CUBE_MTS_4.20\0\0\0` (25,689) and `CUBE_MTS_4.10\0\0\0` (784). No ISI encryption signatures. 4.20 internals are not decoded (only magic/prevalence verified).
- Verification: `tests/test_three_corpora.py`.

### F1 2000 (ISI, 2000) cross-corpus observations (evidence only, `../F12000`)
- 118 `.mas` archives use the `CUBEMAS2.50\0` signature (type 5 in `mas_tool.py`): 12-byte magic, u32 count, u32 data_size, then 256-byte records `name[244], size, zsize, 4 padding` starting at 0x14. Data is sequential after the table. 30,909 members total.
- Member compression variants: 25,392 raw (`size == zsize`), 23,997 plain zlib (`.vrl` meshes), 5,198 16-byte-header + zlib (`.bmp` textures), and 319 tiny textures with an undecoded variant preserved losslessly (`Entry.type == 2`).
- All 118 archives round-trip at member level with `mas_tool.py`.
- Other formats: 71 `.scn` (`CUBEASF`), 55 `.aiw`, 26 `.veh`, 22 `.tgq` (`SCHl` header — not decoded). Bounded 2026-11-23 probe: no valid zlib stream at candidate `78 9c/da/01` headers and no ASCII strings in the first 20 KB; only QuickBMS `SCHl` reference targets a different game.
- Verification: `tests/test_f12000.py`.

### NASCAR Thunder 2004 (ISI, 2003) cross-corpus observations (evidence only, `../NT2004`)
- 136 MAS type-3 archives, 20,414 members; all 14,250 `.mts` meshes have standard `CUBE_MTS_4.10` magic (same family as F1 2002/F1C).
- 1,286 `.hdr` files are audio headers with `0xffff00XX` first u32; 81 `.skn` are text skins; 14 `.djs` start with MP3 frame sync `ff fb`. No known ISI encryption signature.
- Verification: `tests/test_nt2004.py`.

### Third-party Race 07 decryptor (reference only, `../Race07Decryptor`)
- `Race07Decryptor.exe` is a self-contained .NET 8 win-x64 console app (65M) containing `Race07Decryptor.dll`, with Blowfish/OpenSSL decryption identifiers (`TryDecryptWithFallback`, `DecryptBlocks`). No source or format spec shipped; no license file. Reference only — our native `jca_crypt.py` provides the same capability without external binaries.

### Race 07 (SimBin, 2007) cross-corpus observations (evidence only, `../Race07Vanilla`)
- 2 small `.gtr` archives (`DevFiles/CamEd/ingame.gtr`, `GameData/Scripts/crew.gtr`) are MAS type 0. The 5 GMTs in `crew.gtr` use the **standard new layout** (magic at 0x08) and parse/round-trip with `gmt_format.py`.
- All 21,687 loose GMTs start with `0f b1 ff ff 03 00 00 00`. This is **SimBin JCA encryption**, not a third GMT layout: header is `(magic 0xffffb10f, u32 file_version, u32 data_size, u32 zlen)` followed by a Blowfish-encrypted payload at 0x10. `quickbms_scripts/raceroom.bms` recognizes the magic and explicitly directs users to the external GPLv2 tool `wtcced` (`-k raceroom` for RaceRoom/JCA); the QuickBMS scripts themselves do **not** decrypt.
- Verified decryption: `wtcced -o <enc.gmt> <dec.gmt>` (GPLv2 source from aluigi.org/papers/wtcced.zip; compiled here with 32-bit `unsigned long` -> `uint32_t` fixes for 64-bit Linux) turns real Race 07 GMTs into **standard GTR2-layout GMTs** (magic at 0x08) that parse and round-trip with `gmt_format.py`. The default file version 3 uses keytable 1 (`ver23_key`), zlib-decompress, then XOR with 0xEB.
- Native support: `jca_crypt.py` (with GPLv2-attributed `jca_tables.py`) implements all 8 versions, custom game keys, encrypt+decrypt, and matches `wtcced` byte-for-byte on real files. 200 sampled GMTs decrypt and parse with `gmt_format.py`. `tests/test_jca_crypt.py` covers this; `tests/test_race07.py` retains an optional external-tool cross-check. The JCA modules are GPLv2 (user-approved adoption of the published algorithm/tables).
- 195 animation files (`FXM `/`FXA `/`LMA `): 77 FXM/FXM, 62 LMA/LMA, 22 FXM/LMA, 22 FXA/LMA, 12 FXA/FXA — extension/magic mismatches common.
- No filesystem file carries a known ISI 16-byte signature.
- Verification: `tests/test_race07.py`.

### Stock Car Extreme (Reiza, GSC-based) cross-corpus observations (evidence only, `../StockCarExtreme`)
- 196 `.mas` archives use the standard MAS type-1 signature; 71,814 members total.
- 62,522 members carry the Game Stock Car signature `0x4b1dca9f960524e8`, decryptable with `isi_crypt.py` skip=4. No loose filesystem file has a known ISI signature.
- All 60,841 GMT members use the old-style magic `...bba8bf90` at 0x1D4 (60,840 encrypted + 1 plain) — consistent with Copa and Automobilista.
- Other observed files are text/known families (`.veh`, `.rcd`, `.aiw`, `.gdb`, `.tdf`, `.cin`, `.cch` `//[[gMa1`, `.xcf` GIMP images, gzip `.vcr/.hat`).
- Verification: `tests/test_stockcar_extreme.py`.

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

### Sports Car GT (1999) cross-corpus observations (evidence only, `../SportsCarGtUsa`)
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
- **FXM/FXA/LMA**: magic identified (`FXM `/`FXA `/`LMA `), lossless round-trip, heuristic node/bone name extraction; BE header interpretation may overlap string data. Two observed layout families: first string at offset 19 (common in LMA driver skeletons, bone names; 113 files observed with BE u16[1]==257, BE u32[2] in {1,256}, BE u32[3] in {80,184}, BE u32[4]==1, BE u32[5] in {65,66,67,77}) and offset 30 (common in FXA/FXM pit animations, "3D Studio Max..." source string; all 142 offset-30 files observed with BE u16[1]==257, BE u32[2]==4096, BE u32[4]==256, BE u32[5]==528; most contain a source path string within 300 bytes). In sampled GTR2 LMAs, many Bip01 node names are preceded by a 12-byte LE(u32,u32,u32) prefix where third==1 and second matches BE header u32 at offset 8 (semantics unconfirmed). `fxm_tool.parse_node_records()` decodes the contiguous skeleton-node table anchored on `Bip01\x01\x00\x00\x00`: each record is `name, u32 marker=1, u32 size_hint, u32 key_count=3, 84 keyframe bytes (3 x 28)` and records are contiguous (stride = name length + 96). In `FU_PreIdle4-R.FXM` this yields 27 clean nodes (Bip01 hierarchy + FU_Cap_LOCK) and avoids 3ds Max metadata false positives. `fxm_tool.decode_node_keys()` decodes the 84-byte block as 2 TRS keys (position xyz + rotation quaternion xyzw + scale xyz, 40 bytes each) plus a 4-byte trailer; quaternion norms ~1 in 54/54 keys, scale ~1 in 52/54. `fxm_tool.build_node_id_map()` shows the size_hint field equals 84 + a 4-byte trailer (148/148 nodes in 91 files), and that trailer is a **name-stable bone id**: all 27 distinct node names map to exactly one value (Bip01→12, Bip01 Pelvis→11, Bip01 Head→13). `key_count` is exactly 3 in all 148 sampled node records (a fixed field, not the 2 decoded TRS keys); its meaning is unconfirmed.

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
