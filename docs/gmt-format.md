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

## Observed GTR2/GT Legends header (first 24+ bytes)

| Offset | Type (LE) | Observed/example | Notes |
|---:|---|---|---|
| 0x00 | u32 | 72138, 69904, 223002, 333428 | Version/size-related; close to, not always equal to, file size. |
| 0x04 | u32 | `0x04000000`, `0x04000020` | Flags/version bits; differs in at least one GTL/GTR2 pair. |
| 0x08 | 16 bytes | `c8 cf d2 d8 ce d8 e6 c3 d6 de d8 be bb a7 bf 90` | ISI obfuscated magic/signature family. Same family seen in GTR2/GT Legends GMTs and `GOALPOST.GMT`. |
| 0x18+ | mixed u32/float | varies | Likely bounds/transform/metadata; not yet decoded. |

Examples:
- `BMW_M3GTR_OBJ.gtr` -> `BMW_M3GTR_BUMPER_A.GMT`: `06 0f 01 00 00 00 00 04 c8 cf ...`
- `Anderstorp.gtl` -> `TWLAN13.GMT`: `ac 82 02 00 20 00 00 04 c8 cf ...`

## GTL vs GTR2 comparison

Loose GMTs present in both installs (same basename, case-insensitive): **22 common, 21 identical byte-for-byte, 1 different**.

| File | GTL | GTR2 | Observation |
|---|---:|---:|---|
| `M-FPDriver.gmt` | 335,096 bytes; hdr `333428, 0x04000020, c8cf...` | 224,670 bytes; hdr `223002, 0x04000000, c8cf...` | Same magic family, different flags/size/content. Not safely copy-assumable. |

Most sampled shared animation GMTs were identical; do not generalize from that subset.

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

## Unknowns / next steps
- Decode full GMT body: sections, materials, textures, vertices/indices, normals/UVs, LODs, shaders.
- Determine meaning of u32 at 0x00 and flags at 0x04.
- Build an inventory of GTL GMTs differing from GTR2 counterparts by category (car/track/anim/driver).
- Locate or reconstruct `gmtconvert` behavior before attempting GMT transforms.