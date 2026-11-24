# Local `../` reference folders (condensed)

All folders under `../` are **read-only reference material** available offline for
future tasks. Never copy game data, binaries, or third-party code into this repo.
`AGENTS.md` "Key locations" has longer per-folder notes and caveats; this file is
the quick-lookup index. Sizes/counts are approximate (surveyed 2026-11-23/24).

## Target format — GTR2

| Folder | Size / files | Key facts |
|---|---|---|
| `GTR2Steam/` | 1.6G / 3,964 | **Primary target reference.** 34 gzip `.hat` files (`gMb1.000f` header); 34 CUBEASF `.scn` and 34 `.clf` scene files. Real `GameData` layout, `.car/.hdc/.eng/.tyr/.aud/.gdb/.trk/.gtr`, GMOTORMAS10 archives. 3 plain `.aiw`, 25 plain `.aud` (all text); 136 `.gdb`, 972 `.car`, 139 `.cam` JCA-encrypted in broader Race07-style installs but GTR2's own config files here are plain. |

## ISIMotor source corpora (conversion inputs)

| Folder | Size / files | Key facts |
|---|---|---|
| `GTLSteam/` | 1.8G / 2,510 | GTL→GTR2 source. `.CAR` uppercase, `.gtl` type-0 archives, GTL-era GDB/classes. 3 plain `.aiw`, 31 plain `.aud`, 53 plain `.gdb`, 26 plain `.tyr`; 5 `.PHS` members (4 PAR2 recovery containers + opaque `PHYSICS.PHS`). |
| `RF1Vanilla/` | 1.5G / 2,688 | rFactor 1 vanilla: 85 type-1 `.mas`, 9,662 GMTs (9,630 old layout), 120 ISI-encrypted GMTs (skip=4), 904 archived `.anm` files (fully decoded). |
| `Race07Complete/` | 12G / 122k | Race 07 + DLC. Loose DDS in 3 variants incl. `RaceGMT\0`; **101/137 `.aud`, 45/77 `.dmg`, 92/124 `.eng`, 621/823 `.car`, 80/114 `.gdb`, 141/196 `.cam`, 60 `.tyr` JCA-encrypted**; 66,186 loose GMTs; 88 JCA cube maps; 192 JCA `.PSH` shaders; 136 gzip `.hat` track files (bare `Ver 0.08` header); 20,889 `.svm` car setups. |
| `Race07Vanilla/` | 2.7G / 40k | 21,687 loose JCA DDS, 2 small type-0 `.gtr`; 43/43 `.aud` JCA; 8 JCA cube maps; 192 JCA `.PSH`. |
| `BMWM3Challenge/` | 369M / 513 | 17 `.bmw` type-0 archives, loose `.gmt/.fxm/.fxa/.lma/.car/.hdc/.eng/.tyr/.trk/.aiw`, media; 2 plain `.aud`. |
| `VolvoTheGame/` | 504M / 4,639 | SimBin JCA with **custom `volvo` key**; 2,026 loose GMTs decrypt to GTR2 layout; 9/9 `.aud` JCA, 8 JCA cube maps. |
| `CopaPetrobrasdeMarcas/` | 2.2G / 718 | 50 type-1X `.mas` (Petrobras signature), 13,679 Game-Stock-Car-signature encrypted members. |
| `GameStockCar/` | 2.1G / 809 | 48 type-1 archives, 19,995 members, 19,987 GSC-encrypted. |
| `StockCarExtreme/` | 16G / 5,807 | 196 type-1 archives, 71,814 members, 62,522 encrypted members. |
| `Automobilista/` | 35G / 14,796 | 470 type-1 archives, 111,943 members, 91,974 old-layout GMTs (91,962 GSC-encrypted). |
| `NascarSimRacing/` | 1.9G / 7,965 | 311 type-3 archives, 26,473 CUBE MTS meshes incl. `CUBE_MTS_4.20` variant. 1,506 `.hdr`/`.dat` MP3 audio pairs (decoded by `media_tool.hdr_dat_mp3()`); 748 archived `.anm` animations. |

## Newly added ISIMotor-era reference folders (reviewed 2026-11-25)

| Folder | Size / files | Key facts |
|---|---|---|
| `RaceRoomTheGame/` | 497M / 6,756 | Early RaceRoom sim; 4,226 loose GMTs all **JCA-wrapped** (v1) and decryptable with the **volvo** key (not the `raceroom` keys) to plain ISI-magic@8 GMTs; `gmt_semantic.read_gmt()` finds real submeshes. 1,218 DDS, 645 TGA, 245 WAV, `.car/.gdb/.aiw/.cam/.aud/.lma/.fxm/.psh/.vsh`, `.rcs` control configs (text). |
| `RaceRoomTheGame2/` | 1.1G / 15,163 | Later RaceRoom sim; 10,377 loose JCA v1 GMTs, also **volvo** key, decrypting to ISI-magic@8 GMTs with submeshes. 3,209 DDS, 681 TGA, 319 WAV, 102 `.car`, 21 `.svm`, `.skn`-like skin assets, `.rcs` configs. |
| `LexusIsfTrackTime/` | 233M / 412 | rF1-era single-car time-trial: 21 type-1 `.mas` archives (e.g. `commonmaps.mas`, 44 members), 148 WAV, 116 JPG, 11 `.veh`, 5 `.scn`/`.cam`, `.rfm` mod file, plugins (RealFeel, Internals). No loose GMTs. |
| `TC2000/` | 1.4G / 938 | rF1-era Argentine touring-car sim: 34 type-1 `.mas`, 188 DDS, 158 WAV, 36 `.veh`, **35 `.rcd` with a distinct 12-key "talent" driver family** (no `reputation`/`courtesy`/`recovery`) now handled by `parse_rcd()`/`validate_rcd()`, 26 `.cam`/`.gdb`/`.aiw`, 14 `.hdv`, 12 `.svm`, `.tdf` text. |
| `SimuladorTopRace2009/` | 2.1G / 1,084 | rF1-era: 26 type-1 `.mas`, 241 DDS, 158 WAV, 118 **uppercase `.GMT`** files carrying the known Top Race 2009 ISI signature (`0xde4139f961fa2817`, enctype 0); `isi_crypt` decrypts all 118 but none expose the standard GMT magic/submeshes (same unresolved post-decryption pattern as GSC GMTs). 41 `.veh`, 40 `.rcd`, 27 `.cam`, `.tdf`, Qt DLLs. |

## Ancestral ISIMotor / format-evolution corpora

| Folder | Size / files | Key facts |
|---|---|---|
| `SportsCarGtUsa/` | 338M / 993 | 61 signature-less type-2 `.mas` (16,070 members), `.vrl` meshes, 16-byte-header+zlib textures; **2 AMBC.BMP members decoded** as 16-byte header + 768 raw RGB (5 trailing bytes in inter-member gap). |
| `F12000/` | 471M / 570 | 118 type-2.5 (`CUBEMAS2.50`) archives, 30,909 members; `.scn/.aiw/.veh/.tgq`. |
| `F12001/` | 453M / 647 | 80 type-6 (`CUBEMAS4.00/4.01`) archives, 16,720 members; CUBE MTS meshes. |
| `F12002/` | 600M / 1,065 | 63 type-3 (`CUBEMAS4.10`) archives, 19,235 members, 13,100 MTS meshes; `.anm` corpus. |
| `F1C/` | 591M / 798 | 197 type-3 archives, 21,977 members, 14,834 MTS meshes; `.anm` (unparsed originally, now decoded); direct rFactor predecessor. |
| `F1CS2000/` | 471M / 570 | Byte-identical copy of `F12000` — no new format work needed. |
| `NT2003/` | 722M / 2,968 | 179 type-3 archives, 19,006 members, 10,397 MTS; `.hdr/.dat` audio, `.veh/.hdv` text. |
| `NT2004/` | 632M / 2,108 | 136 type-3 archives, 20,414 members, 14,250 MTS; `.hdr` audio, `.skn`, `.djs`. |
| `GTR1Vanilla/` | 1.2G / 3,613 | 430 type-0 `.gtr`; 33,477 GMTs with third magic at +0x04 (decoder coverage proven 8,109/8,109); 3 use `OR_GMT_1.00`. |

## Reference tools / code (reference only — check licenses, do not copy)

| Folder | Size / files | Key facts |
|---|---|---|
| `rfactortools/` | 44M / 694 | Python package + C extension, GPLv3; source of parsing patterns; **read before implementing converters**. Tests, CLI programs. |
| `gtr2-tools/` | 592M / 2,431 | Includes freeware `AIW Repair Utility v1.0` documenting rF1→SimBin AIW rules (scale `wp_galpha`×0.45, drop 12 rF1-only tags, `wp_cheat`→`wp_event=(1.000,0,0)`). Several third-party tools with unclear licences — do not copy. |
| `gtr2-agent-tools/` | 148M / 641 | CC BY-NC 4.0; `scripts/gtr2_driving/` parsers: `mas.py`, `gmt.py`, `trackmap.py` (AIW), `cargears.py`, `pitzones.py`; ghost-frame marker layout. |
| `guitarmaen-aiw-cam-editor-gtr2-qt/` | 9.6M / 73 | Qt5 AIW/CAM/GDB editor; **no license — reference only**. Vendors original Turbo Basic source `rF_AIW_CAM_422.x` (~9.6k lines) — authoritative for AIW/CAM field semantics/defaults (WP_PTRS classes, 4 paths, negated CAM coords, Flags1 bits, deactivation sentinel). |
| `rFactorSharedMemoryMap/` | 308K / 40 | GPLv2; `rfSharedStruct.hpp` documents rF1 runtime telemetry units/ranges (rad, m/s, gear −1/0/1+, throttle 0..1, steering −1..1). Not a file-format spec. |
| `rF2SharedMemoryMapPlugin/` | 3.1M / 71 | GPLv3; `rF2State.h` documents rF2 runtime telemetry fields. Useful for units only, not `.VCR` layout. |
| `quickbms_scripts/` | 13M / 2,745 | QuickBMS format scripts; `mas.bms` covers GMOTORMAS10/CUBEMAS4/ISI MAS. Spec cross-check. |
| `MAS2Extract/` | 312K / 38 | C# GPLv3 tool for rF2 `GMOTOR_MAS_2.90` only — not GMOTORMAS10/GTR2/GTL. |
| `Speednuts_mas_extract/` | 264K / 1 | C MAS extractor (GTR2/GTL/rF1); our `mas_tool.py` supersedes it. |
| `Race07Decryptor/` | 65M / 1 | .NET 8 JCA/Blowfish tool, no source; reference only. |
| `modding-tools-and-tutorials/` | 131M / 538 | Third-party tools/tutorials; `GTL2GTR2 Converter` (rename-only), RacerM notes, GMT hex-editing hints. Do not commit binaries. |

## Scratch / generated (treat as reference, not authoritative)

| Folder | Size / files | Key facts |
|---|---|---|
| `hand_selected/` | 29G / 24,943 | Curated samples (`.aud`, `.gtr`, `.car`, xval trees). Large generated output trees live here, outside the repo. |
| `legacy/` | 50M / 168 | Prior-attempt ad-hoc scripts/fixtures; hardcoded dead paths, imports absent from current `rfactortools`. |
| `old-tmp-files/` | 49M / 68 | More prior-attempt scratch: probes, GUI screenshots, `gMa1.002f` AIW fixture. Not ruled out — revisit for field-level work. |
| `tools.unsorted/` | — | Remaining large/irrelevant items (moved to `~/tmp/tools.unsorted.irrelevant/`). |

## Verified format-identification coverage (2026-11-24)

`media_tool.identify()` is now content-based across the corpora: 21,180 plain GMTs (ISI magic @8), 45,359 JCA GMTs, 643 `RaceGMT\0` meshes, 1,090 `.mas` + all `.gtr`/`.gtl`/`.bmw` archives (6 variants), 1,640 PNG, 479 GIF87a/GIF89a (plus JPEG/PNG/HTML masquerading as `.gif`), 188 gzip `.hat` track files, 1,982 NASCAR `.hdr`/`.dat` MP3 pairs, 21,141 `.svm` setups, 2,763 `.veh` / 156 `.hdv` / 294 `.gen` descriptors, 123 `.scr` / 409 `.cin` scripts, 22 CUBEASF `.set` camera files, and plain `.rcd/.gdb/.car/.aiw/.cam/.hed/.dmg/.grb/.cas/.sp/.inccar` text configs. JCA-wrapped configs decrypt via `decrypt_jca_text()`. Parsers in `simbin_text_tool.py`: `parse_veh`, `parse_hdv`, `parse_hdc` (via `parse_hdv`), `parse_svm`, `parse_set`, `parse_sp`, `parse_skn`, `parse_hed`, `parse_rcd`, `parse_grb`, `parse_eng`, `parse_cin`, `parse_scr`, `parse_gdb`/`parse_car`, `parse_dmg`, `parse_aud`, `parse_cam`, `parse_scn`; plus `read_anm`, `hdr_dat_mp3`, `hat_decompress`, `fxm_tool`, `gmt_semantic`. Conversion helpers: `gtl_to_gtr2.validate_svm_setup()` / `rf1_svm_paths()`. Remaining opaque: GTTF frame fields 7/9/32/36/40, `PHYSICS.PHS`, 10 encrypted `.svm` payloads, ~95% of GSC-encrypted GMTs (distinct post-decryption layout), `.hdr` index table, 4 E30 wiper FXM files (MSVC debug-fill garbage).

## Practical rules

- These folders are **always available** for reference, lookup, and cross-checking during any task.
- Prefer native Python in this repo / `rfactortools` for pipeline integration; use third-party tools only as format oracles.
- Record new verified findings from these corpora in `CAPABILITIES.md`, `docs/binary-formats.md`, `docs/file-formats.md`, or `docs/open-issues-research.md` as appropriate, and update this index when a folder's role changes.
