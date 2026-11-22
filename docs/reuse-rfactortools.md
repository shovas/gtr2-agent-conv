# Reusing reference material (rfactortools + tutorials)

This document records mining of the two reference sources that were previously
only sampled: `../rfactortools` (Python package, GPLv3) and
`../modding-tools-and-tutorials` (third-party tools/tutorials, reference only).

## 1. `../rfactortools` — ready-made parsers/converters (GPLv3)

The reference package cannot be imported directly here (`rfactortools._crypt`
C extension is not built), but the source is readable and the following parts
are directly reusable as *patterns* (we must not copy GPLv3 code verbatim into
this repo without a licensing decision).

| Module | Symols | Relevance to our goal |
|---|---|---|
| `rfactortools/aiw.py` | `parse_aiwfile`, `AIW.waypoints`, `Waypoint.pos/bitfields/branch_id`, `render_aiw` | AIW waypoint parsing: `[Waypoint]` sections, `wp_pos` vec3, `wp_bitfields`, `wp_branchID`. Matches the `//[[gMa1` + `[Features]` files we identified in GTR2/GTL. |
| `rfactortools/scn_parser.py` | `process_scnfile`, `ScnParser`, `InfoScnParser` (`search_path`, `mas_files`, `has_skyboxi`), `scn2posix_path` | SCN/TRK parsing: `SearchPath=`, `MASFile=`, `Instance=SkyBoxI` keys and `{`/`}` sections. Directly applicable to our `.scn`/`.trk` files. |
| `rfactortools/util.py` | `lookup_path_icase`, `find_files`, `open_read` (latin-1) | Case-insensitive path resolution vital for GTR2/GTL mixed-case filenames. |
| `rfactortools/gdb.py` | `process_gdb_file` | Shows GDB is paired with same-basename SCN; uses `InfoScnParser` for SearchPath/MasFiles. |
| `rfactortools/sfx.py` | `parse_sfxfile`, `modify_sfxfile`, `try_fix_wav_path` | SFX WAV path rewrite patterns (`key=value.wav` and `key=n,file.wav`). |
| `rfactortools/veh.py` | `parse_vehfile`, `Veh`, `find_file_backwards` | `.veh`/`.hdv` vehicle chain walking via `GenData` backwards search. |
| `rfactortools/gsc2013.py` | `rFactorToGSC2013Config`, `rFactorToGSC2013`, `find_data_directories`, `find_track_directory`, `convert_gdb/veh/scn/aiw/sfx/gmt/mas/tdf/jpg/tga`, `convert_file` extension dispatch, `exclude_files` (2,794 entries) | **A complete ISIMotor→other-game conversion pipeline.** Provides extension dispatch, directory hierarchy copying, GDB `Filter Properties`/`VenueName` rewrites, VEH `Classes`/`Team`/`Category` rewrites, SCN light-intensity clamp, AIW thumbnail generation, MAS decrypt+repack, exclusion list. This is the strongest "unknown known". |
| `rfactortools/gtr2.py` | `GTR2ToGSC2013.convert_gtr` | Contains the explicit comment: *"TODO: This doesn't work .gmt files have different formats in GSC2013 and rFactor and need to be converted first"* — independent confirmation of our GMT-layout finding. |

**Key insight:** For GTL→GTR2 the pipeline is *simpler* than rFactor→GSC2013:
no encryption is involved, and the GMT layout is the same (new layout at 0x08).
The GSC2013 converter's non- GMT steps (path resolution, GDB/VEH/SCN/SFX
rewrites, exclusion list) are the reusable part.

## 2. Third-party tutorials — concrete conversion rules (reference only)

### GTL2GTR2 Converter v0.9.0.1 (`ReadMe ...txt`)
- Only renames `.gtl`/`.gtr` extensions and edits `.trk` MASFile names.
- **Explicitly does not** fix AIWs, GDBs, missing files, or safety cars.
- Works only with add-on tracks, single-layout tracks.

### RacerM, "CONVERTING RFACTOR TRACKS TO GTL/GTR" (`...pdf`) — the valuable one

Concrete rules for rFactor→SimBin track conversion (GTL and GTR2 share layout):

1. **Material naming convention** (critical): SimBin games require material
   names starting `GRAS` (grass), `GRVL`/`GRAV` (gravel), `ROAD` (tarmac/asphalt).
   Wrong prefixes cause the "quicksand effect". rFactor does not enforce this.
   The first four characters are what the game reads.
2. **SCN → TRK**: rename `.scn` to `.trk`; rewrite `SearchPath` to
   `GameData\Locations\Shared` and `GameData\Locations\<track>`; rewrite
   `MASFile=` entries to SimBin names (e.g. `skies_central.gtr`,
   `<track>maps.gtl`, `<track>.gtl`).
3. **SkyBoxI**: rFactor's `SkyBoxI` block differs; copy the whole block from a
   known-good GTR2/GTL `.trk`.
4. **AIW/CAM**: copied unchanged. **GDB**: copy text from a known-good converted
   track and substitute track info.
5. **Sky GMT and SkyBoxI GMT**: 3DSimEd cannot convert these automatically;
   handled manually via "Save As GT Legends GMT / Save Data".
6. **Textures**: must be DDS (BMP/TGA unsupported by SimBin).
7. **CTD causes**: mismatched names across folder/GDB/TRK/searchpath/MASFile;
   missing converted sky/skyboxi GMTs; old SkyBoxI block; unconverted SearchPath.

`rfactor2gtr2tracks.txt` adds: converted tracks need shadows set to MEDIUM in
GTR2 or framerate collapses; the supplied GDBs are hand-verified.

## JCA cross-check against the third-party decryptor (task #7)

`Race07Decryptor.exe` is a single-file .NET 8 bundle. The managed assembly was
carved out (valid PE at file offset 9,641,984) and disassembled with `monodis`.
Its IL confirms our `jca_crypt.py` exactly:
- `WtccCodec.IsEncrypted` checks magic `0F B1 FF FF`;
- `Decrypt` reads version at +4, data_size at +8, zlen at +0x0C, payload at +0x10;
- `Blowfish.DecryptBlocks` reads/writes LE u32 pairs — same as ours;
- `KeyForVersion`/custom-key switch covers `volvo`, `raceroom`, `raceroom_plr`, `old_raceroom`;
- `XorBuf` is called with constant `235` (`0xEB`);
- `InflateWithWorkaround` mirrors the unaligned-tail workaround.

No algorithm differences found; no code was copied.

## Actionable next steps derived from this mining

- A GTL→GTR2 track converter should implement rules 2/3/4/6 above, plus
  case-insensitive path resolution from `util.py`.
- Material-prefix validation (`GRAS`/`GRVL`/`ROAD`) is a cheap, high-value check
  we can add to our tooling — no binary format work needed.
- The 2,794-file exclusion list from `gsc2013_excludes.py` can be adapted as a
  "do not copy" list.
