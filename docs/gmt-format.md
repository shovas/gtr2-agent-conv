# GMT Format Deep Dive (GTL vs GTR2)

First-pass binary analysis for GTL -> GTR2 conversion. **Not a complete spec**; verify with game behavior and targeted tests.

## Evidence
- Sampled loose `.gmt` files in `../GTR2Steam` and `../GTLSteam`.
- Extracted GMTs from GMOTORMAS10 archives (`.gtr/.gtl`) using `mas_tool.py`.
- Inspected `hand_selected/xval_test/test/GOALPOST.GMT`.
- Reviewed `rfactortools/programs/gmttool.py`, `rfactortools/gtr2.py`, `rfactortools/gsc2013.py`.
- Note: current `../rfactortools` snapshot has `gmttool.py` but no `gmt.py`/`gmtconvert.py`; legacy scripts expected those modules.

## Purpose
- GMT is an ISIMotor 3D mesh/model asset used by cars, tracks, animations, and scene objects.
- Referenced by `.trk` instances, car graphics/configs (`.cas`/vehicle chains), and MAS archive contents.
- Conversion risk: incompatible GMT versions/layouts can cause invisible objects, load failures, or crashes.

## Observed GTR2/GT Legends header/structure (first pass)

| Offset | Type (LE) | Observed/example | Notes |
|---:|---|---|---|
| 0x00 | u32 | 72138, 69904, 223002 | **Object/material list offset** (points near EOF; `size - offset` is trailing table size, commonly 1152+). Confirmed by ASCII names at offset. |
| 0x04 | u32 | `0x04000020` (12320), `0x20` (6207), `0x04000000` (6128), `0x0` (2273), `0x02000020` (2) | Header flags (observed across 26930 normal-magic archive GMTs). Semantics not fully proven; bits `0x04000000` and `0x20` dominate. |
| 0x08 | 16 bytes | `c8 cf d2 d8 ce d8 e6 c3 d6 de d8 be bb a7 bf 90` | ISI obfuscated magic/signature family for normal GTR2/GTL GMTs. |
| 0x16C | u32, u32 | `count, first_record` | Mesh table header. Validated on 26916/26931 archive GMTs with `0 < count <= 256` and bounds check. Observed `first_record==528` (0x210) in scanned normal-magic GMTs; 0x174..0x210 is a non-zero header/gap region. |
| `first_record + i*108` | 27*u32 | record | Mesh record. Observed fields: `[1]=flags`, `[3]=vertex_count`, `[4]=vertex_offset`, `[10]=index_count`, `[11]=index_offset`. |
| vertex | 32 bytes | `u32, xyz floats, normal xyz floats, u32` | Observed by structure probe; consistent with external reference. |
| indices | 4-byte lead + u16[] | triangle list | Observed `index_offset + 4 + index_count*2` within file. |

Examples:
- `BMW_M3GTR_OBJ.gtr` -> `BMW_M3GTR_BUMPER_A.GMT`: `06 0f 01 00 00 00 00 04 c8 cf ...`
- `Anderstorp.gtl` -> `TWLAN13.GMT`: `ac 82 02 00 20 00 00 04 c8 cf ...`
- `GOALPOST.GMT`: `4a 17 00 00 00 00 00 00 c8 cf ...`

## Inventory findings (GTR2Steam + GTLSteam, `.gtr/.gtl/.mas` archives)

- **26931 GMT files** scanned in archives.
- **26930** have normal GTR2/GTL magic; **1** odd magic: `GTLSteam/GameData/Teams/GTC-TC-76/Detomaso Pantera/DETOMASO_PANTERA_CPIT.gtl` -> `DETOMASO_PANTERA_RAINSCREEN.GMT` (3072 bytes, magic `ced8e6c3d6ded8bdbba6bf9000000000`, flags `0xd8d2cfc8`). Observed as the only non-normal-magic GMT in 26,931 scanned MAS GMTs. Looks encrypted/scrambled (GMT encryption skips first 4 bytes in `rfactortools/crypt.py`; C extension unavailable here). Treat as **needs decrypt/verify**, not normal GMT.
- **26916** pass mesh-table bounds check with relaxed count (`<=256`); **15** fail strict `<=64` sanity cap: 14 are GTR2 `*_MOTEC_ADL2.GMT` cockpit display meshes with count 72-76 and valid bounds; 1 is the odd encrypted rainscreen. The old `<=64` cap was too strict for car cockpit GMTs.
- Flag distribution: `0x04000020` (12320), `0x20` (6207), `0x04000000` (6128), `0x0` (2273), rare `0x02000020` (2), plus encrypted outlier.
- **Same-track archive comparison (Anderstorp GTL vs GTR2)**: 507 common GMT basenames, 57 identical, 450 different, 1 GTL-only, 190 GTR2-only. Same-name assets across different tracks are not comparable; same-track comparison is the meaningful check.
- **Cross-archive basename comparison** is noisy (name collisions across different tracks/archives); do not use it as a conversion diff signal without same-track/archive context.

## GTL vs GTR2 comparison

Loose GMTs present in both installs (same basename, case-insensitive): **22 common, 21 identical byte-for-byte, 1 different**.

| File | GTL | GTR2 | Observation |
|---|---:|---:|---|
| `M-FPDriver.gmt` | 335,096 bytes; hdr obj=333428, fl=`0x04000020`, c8cf... | 224,670 bytes; hdr obj=223002, fl=`0x04000000`, c8cf... | Same magic family, different flags/obj offset/size/content. Not safely copy-assumable. |

Most sampled shared animation GMTs were identical; do not generalize from that subset. Car/track GMTs inside archives need per-file or per-category validation.

## Relation to rFactor GMT tooling

- `rfactortools/programs/gmttool.py` is an rFactor GMT inspector with a different parsed layout (object offsets at 0/4, seeks to 372/404, name at 404, 16-byte constant read later: `C8 CF D2 D8 CE D8 E6 C3 D6 DE D8 BE BB A8 BF 90` in comment).
- `rfactortools/gtr2.py` comment: "GMT files have different formats in GSC2013 and rFactor and need to be converted first."
- Implication: GMT format varies by ISIMotor game/era. GTL and GTR2 are close SimBin-era siblings, but per-asset compatibility must be validated.

## Conversion implications (GTL -> GTR2)

- **Default**: binary carry-over with validation, not blind rewrite.
- **Fast path**: copy/repack unchanged when file is identical to known-good GTR2 equivalent or passes sanity/in-game checks.
- **Checks to implement**:
  - Header sanity: expected magic family at offset 8 for GTR2/GTL GMTs.
  - Archive integrity: GMT survives `.gtl` extraction -> `.gtr` repack.
  - Reference resolution: all GMT/MeshFile refs resolve.
  - Smoke test in GTR2 for visual/load correctness.
- **Edge cases**: if GTR2 rejects a GMT, investigate version/flag differences and use/port a real GMT converter. Legacy expected `gmtconvert`; current rfactortools snapshot lacks it.

## External parser clues (reference only)
- `../gtr2-agent-tools/scripts/gtr2_driving/gmt.py` (CC BY-NC 4.0, read-only, track-mesh focused) parses GTR2 GMTs by reading mesh table at `0x16C`: `u32 count, u32 first_record`; records 108 bytes, `u32[27]` with `flags=[1], vertex_count=[3], vertex_offset=[4], index_count=[10], index_offset=[11]`; vertices 32 bytes (`u32, pos xyz floats, normal xyz floats, u32`); indices `u16` triangle list with 4-byte lead. It validates bounds/counts and raises on implausible data. Useful as a structural clue; verify against GTL/GTR2 car and track GMT variants before relying on it.

## Tooling
- `gmt_tool.py`: `info`, `scan`, `diff` for GMT header/mesh-table inspection. Uses observed structure only; no geometry conversion.

## Additional confirmed findings

- **Mesh -> material index**: mesh rec[2] is within material table count for **85363/85363** mesh records checked.
- **File header flags (observed)**: normal-magic GMT `flags` at offset 4 use only bits in `0x06000020` in scanned samples (values 0, 0x20, 0x02000000, 0x04000000, 0x04000020). Semantics unconfirmed.
- **Header name field (observed)**: `0x194..0x1D4` contains a 64-byte null-terminated ASCII object/name string; often matches GMT basename but not always.
- **Vertex stride/layout (confirmed structure)**: 32-byte base in 85352 records (`rec[5]==0, rec[6]==vo+vc*32`). 11 records have 48-byte extended vertices split into two contiguous blocks: base 32-byte block `vo..rec[5]` where `rec[5]==vo+vc*32`, extra 16-byte block `rec[5]..rec[6]` where `rec[6]==vo+vc*48` (FUELHOSE, EXT_DRIVER_STYLE01-10). 2 records (GRATING1) have `rec[6]==0` but 32-byte fits. Scanned samples also show `rec[0]==0` and stride 32/48 only. Observed extra 16-byte vertex raw_u32 == `[0, 0xFFFFFFFF, 0, 0]` in 11 meshes/2918 verts.
- **Index data (observed)**: index block has 4-byte lead + u16 indices. Scanned samples: index refs are within vertex_count; index_count is not always multiple of 3 (9386/50054), suggesting triangle strips/mixed topology possible; 4-byte lead is often 0 but can be other float-like values. Semantics unconfirmed.
- **Mesh record fields (observed)**: in scanned samples `rec[0,9,12-23]==0`; `rec[24]` is `0xFFFFFFFF` or `0`; `rec[2]` material index is within material count. Rare `rec[24..26]` patterns observed: `(0,0xFFFFFFFF,0)` (36/50054) and `(0xFFFFFFFF,0,1098907648==18.0f)` (11/50054); otherwise `(0xFFFFFFFF,0,0)`. Semantics unconfirmed.
- **Additional vertex streams observed**: some meshes have non-zero `rec[7]`, `rec[8]` (e.g. ANNOUNCERSOUND01: vc=20, vo=1164, v6=1804, v7=2444, v8=3084 - three contiguous 32-byte/vertex blocks, 32 bytes/vert each). Observed across scanned samples: when present, stream2/3 are 32 bytes/vertex; mesh `rec[1]` bit `0x20` correlates exactly with stream2/3 presence in scanned sample. `gmt_format.py` captures them as raw `stream2_data`/`stream3_data`; layout/semantics not fully decoded.
- **Mesh flag bits (observed, semantics unconfirmed)**: in scanned samples `rec[1]` bit 0x1 always set, bit 0x4000 always set, bit 0x2 set iff 48-byte extra vertex block present, bit 0x20 set iff stream2/3 present; bit 0x10 set in nearly all (GRATING1 exception observed); other bits vary (0x4,0x2000,0x20000000).
- **32-byte base vertex (observed/parsed view)**: `[u32 f0, f32 px,py,pz, f32 nx,ny,nz, u32 f7]`. Pos/norm plausible across samples; `f0` is 0 in vast majority of scanned vertices, `f7` varies widely; semantics unconfirmed (flags/color/packed UV/tangent bits possible). Parsed as `GmtVertexBase` while preserving raw bytes for lossless round-trip.
- **16-byte extra block (48-stride)**: 4 float/u32 values per vertex; observed first values in FUELHOSE/EXT_DRIVER_STYLE01 samples `[0.0, NaN, 0.0, 0.0]`. Captured as raw `extra_vertex_data` and decoded as `GmtVertexExtra(raw_u32, raw_f32)`; semantics not fully confirmed.
- **Material table**: tail at `obj_list_offset` starts `u16,u16,u32 count`; contains `count` material/object entries. Variable-size in general. **L0 heuristic**: many records have `L0...` stage string at `+152`; when L0 candidates match count and start at 8, `gmt_format.py` uses them as boundaries (fixes BUMPER_A). Fallback is equal split; raw tail always preserved for lossless round-trip. `gmt_format.py` extracts ASCII strings from material/stage blocks (texture names like `*.DDS/*.TGA`, stage names like `L0*`). Observed in scanned samples: texture-like strings appear in stage 3 only. L0-heuristic material header u32 invariants observed: [6..15]==0, [20..23]==1.0f, [28]==1.0f, [32]==1.0f, [36]==0 (semantics unconfirmed).
- **Material header/stage observed fields (semantics unconfirmed)**: material records have 152-byte header before 4x264-byte stage blocks. Observed stable fields in BUMPER_A mat0: header u32[32..37]=(1065353216,2,1,1109393408,0,3). Across sampled L0-heuristic materials, header u32[32]==1065353216 (1.0f) and u32[36]==0 were invariant; u32[33] commonly 2/5, u32[34] commonly 1/6, u32[35] varies (float-like), u32[37] commonly 0-3. Stage tail u32[64,65] at stage-byte offsets 256,260 correlate with stage name/type across large sample (e.g. `L0DIFFUSET0` commonly (1,0)/(1,1)/(1,4), `L0NOLIGHTING` (0,1)/(0,4), `L1BUMPSPECMAPT0` (5,5)/(4,5), empty stage (0,0)); semantics unconfirmed. Exposed as `GmtMaterial.header_raw`, `GmtStage.tail_u32_64/65`.
- **Texture filename location (observed)**: in sampled L0-heuristic materials, `.DDS/.TGA/.BMP` texture filename strings appear in stage block 3 (0-based, 4th of 4x264-byte blocks), not stages 0-2; rare exceptions may exist (e.g. header/no-stage cases observed in small numbers). Within stage 3, texture names commonly appear at byte offsets 28 and 200 (two observed slots); observed slot patterns are commonly (28,200) and (28,), with rare others. Stage-3 u32 at byte offset 24 varies (commonly 2-12) and u32 at offset 92 has common values (e.g. 131096/0x20018, 24, 131224); distributions differ by slot pattern but semantics unconfirmed.
- **Common stage shader names (observed, semantics unconfirmed)**: stage 0 commonly `L0NOLIGHTING`, `L0DIFFUSET0`, `L0DIFFUSET0XT1`, `L0SPECULART0`; stage 1 commonly `L1DIFFUSET0`, `L1USEVERTEXONLY`, `L1BUMPSPECMAPT0`, `L1SPECULART0`; stage 2 commonly `L2USEVERTEXPIXEL`, `L2SPECULART0`, `L2BUMPSPECMAPT0`, `L2SPECULARMAPT0`. Useful for GTL→GTR2 material/shader mapping, but exact semantics require spec/runtime validation.
- **Structural round-trip**: `gmt_format.py` parses header, mesh table, mesh vertex/index blobs, material table best-effort, and preserves original bytes for lossless round-trip. Tested on real GTR2/GTL GMTs.

## Unknowns / next steps
- Fully decode material/object record layout (variable-size?), texture stage slots, shader params, LODs, UV sets.
- Fully decode flags at 0x04 and mesh record flags at rec[1] semantics.
- Confirm 32/48-byte vertex field semantics (UVs, tangents, colors, packed normals).
- Build full same-track/same-archive GTL-vs-GTR2 GMT diff inventory.
- Handle encrypted GMTs. Added pure-Python ISI 16-byte-header decrypt/encrypt (`isi_crypt.py`, verified against rfactordec). `DETOMASO_PANTERA_RAINSCREEN.GMT` is not a standard ISI 16-byte-header encrypted GMT; it has mangled magic/flags and `mesh_count=0` but contains `RAIN_ANIM`/`RAIN_ANIM.TGA` strings. Repairing bytes 4..24 to `flags=0, normal magic` yields a structurally parseable, lossless-round-trippable GMT (test: `test_detomaso_rainscreen_header_repair_roundtrip`), but semantic correctness of this repair is unverified without a known-good reference.
- `gmtconvert` not found in workspace; any GMT transform needs a new tested converter backed by format evidence.