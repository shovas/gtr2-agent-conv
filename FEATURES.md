# Features

End-user guide to what you can ask an agent to do with this repository. This project is WIP; features marked **partial** have known gaps.

## Convert ancestral SCGT track meshes to GTR2 GMT (partial)

**What it does**: Converts decoded Sports Car GT `.vrl` meshes into GTR2-layout `.gmt` files. Positions come from the corpus-verified VRL vertex streams, normals are computed from triangulated geometry, and the result is re-parsed to verify vertex/index counts and data before writing.

**How to ask**:
- "Convert this `.vrl` to a GTR2 `.gmt` using a real GTR2 GMT as a structural template."

VRL per-corner UV coordinates are transferred by expanding shared vertices at seams into the GTR2 UV block.

## Convert GTR1 third-magic meshes to GTR2 GMT (partial)

**What it does**: Converts GTR1 third-magic `.gmt` meshes (inside `.gtr` archives) into GTR2-layout GMTs, merging descriptor submeshes into one mesh. Positions and unit normals come from corpus-verified descriptor fields; triangles are rebuilt from the descriptor index lists.

**How to ask**:
- "Convert this GTR1 `.gmt` to a GTR2 `.gmt` using a real GTR2 GMT as a structural template."

Vertex fields 9/10 are decoded as UV pairs and written into the GTR2 UV block; descriptor-less meshes have no UV source and are left unchanged.

## Batch-convert mesh archives

**What it does**: Walks SportsCarGtUsa and GTR1Vanilla archives, converts every decoded mesh with the converters above, verifies each output by re-parsing and material checks, and writes only verified GMTs to a directory you choose.

**How to ask**:
- "Batch-convert the SCGT and GTR1 meshes into `/tmp/gtr2_meshes` using this GTR2 GMT as a template."

**Commands**:
```bash
python3 batch_convert.py --template template.gmt --out /tmp/gtr2_meshes --limit 10
```

## 1. Inspect MAS archives (`.gtr`, `.gtl`, `.mas`)

**What it does**: Lists, extracts, creates, and modifies GMOTORMAS10 MAS archives used by GTR2/GT Legends.

**How to ask**:
- "List the contents of `path/to/file.gtr`."
- "Extract `file.gtr` to `/tmp/out`."
- "Create a MAS archive from these files..."
- "Add/replace/delete `foo.gmt` in this archive."

**Commands**:
```bash
python3 mas_tool.py list <archive>
python3 mas_tool.py extract <archive> <outdir>
python3 mas_tool.py create <archive> <files...>
python3 mas_tool.py add <archive> <files...>
python3 mas_tool.py update <archive> <files...>
python3 mas_tool.py delete <archive> <name...>
```

## 2. Decrypt/encrypt ISI files (partial)

**What it does**: Decrypts/encrypts ISI/rFactor 16-byte-header files (GMT/MAS-style), with GMT skip=4 handling. Encrypted `//[[gM` text configs (rFactor `.svm` and GTR-family gMb files) are decoded by `isi_gm_crypt.py` using the documented game keynums.

**How to ask**:
- "Decrypt this GMT/MAS file."
- "Encrypt this file with a GSC/rFactor signature."
- "Check if this GMT is ISI-encrypted."

**Command**:
```bash
python3 isi_crypt.py <input> <output>             # decrypt
python3 isi_crypt.py -e -s 4b1dca9f960524e8 <in> <out>  # encrypt
python3 -c "import isi_gm_crypt as g; d=open('setup.svm','rb').read(); print(g.decrypt_gm_file(d, g.GM_KEYNUMS['rf1']).decode('latin-1'))"
python3 gsc_exe_tool.py list "../CopaPetrobrasdeMarcas/Marcas.exe"
python3 gsc_exe_tool.py extract "../CopaPetrobrasdeMarcas/Marcas.exe" out/
```

**Limitations**: Only known ISI sign/key 16-byte-header variants. Unknown-signature files (e.g. DETOMASO_PANTERA_RAINSCREEN.GMT) remain unresolved.

## 3. Inspect GMT files (partial)

**GSC → GTR2 conversion**: `python3 gmt_layout.py encrypted_member.gmt output.gmt --gsc` rebuilds a GTR2-layout mesh from an encrypted GSC-family member (150/150 sampled members preserve geometry).

**What it does**: Parses GMT headers, mesh table records, material/stage string evidence, and observed vertex/stream layouts; diffs GMTs; performs structural lossless round-trip, and can rebuild all offsets after mesh data grows (`gmt_tool.py relayout ...`). Previously opaque GSC GMTs now decode to real geometry with `gmt_semantic.decode_gsc_member()` (correct ISI skip=4); 150/150 sampled members produce plausible vertices and faces. GTR1 and VRL conversions now carry UVs in the real GTR2 UV block.

**How to ask**:
- "Inspect this GMT and tell me what we know about its structure."
- "Scan this GameData directory for GMT files and summarize them."
- "Diff these two GMT files."
- "Round-trip this GMT through the parser and confirm it's byte-identical."

**Commands**:
```bash
python3 gmt_tool.py info <file.gmt>
python3 gmt_tool.py scan <dir>
python3 gmt_tool.py diff <a.gmt> <b.gmt>
python3 gmt_tool.py f0-compare <a.gmt> <b.gmt>   # compare per-mesh f0 markers
python3 gmt_tool.py relayout <input.gmt> <output.gmt>   # rebuild offsets after mesh data grows
```

**Limitations**: Stage type (+256) and texture channel (+260) are decoded, but UV/LOD/shader/flag meanings and in-game geometry correctness remain unresolved. GSC GMT conversion correctness in-game remains unvalidated; the earlier region-mask blocker was an ISI-parameter artifact.

## 4. Inspect/round-trip DSI/HAT/GTT/VCR gzip containers

**What it does**: Reads gzip-wrapped SimBin `.dsi`/`.hat`/`.gtt`/`.vcr` files, reports metadata, and round-trips content byte-for-byte (verified on all 197 shipped GTR2 containers). `.hat` payload bodies are partly decoded: the header holds a spatial-grid origin/scale (the former "signature"), the declared polygon count, its bisection-tree size and the record count, and a table of track-space height samples; `media_tool.py hat-layout FILE CORPUS_DIR` reports all of these and matches layouts across GTL/GTR2/Race07. The opaque per-record identifier has no decoder in either shipped executable; the trailing stream is known from code to be a tree of typed 34-byte nodes, but its framing transform and field semantics remain undecoded.

**How to ask**:
- "Inspect this HAT/DSI file."
- "Decompress and recompress this HAT while preserving content."

**Command**:
```bash
python3 gzip_simbin_tool.py info <file.hat|file.dsi>
```

## 5. Inspect/round-trip FXM/FXA/LMA files (partial)

**What it does**: Identifies FXM/FXA/LMA headers, extracts heuristic node/bone names, and performs lossless round-trip.

**How to ask**:
- "What kind of FX file is this?"
- "Lossless round-trip this FXA/FXM/LMA."
- "List node/bone names from this LMA."

**Commands**:
```bash
python3 media_tool.py bink-decode <file.bik> <out_dir> [--frames N]
python3 media_tool.py tgq-decode <file.tgq> <out_dir> [--frames N]

python3 fxm_tool.py info <file.fxm|file.fxa|file.lma>
python3 fxm_tool.py nodes <file.fxm>            # heuristic name extraction
python3 fxm_tool.py keys <file.fxm>             # decoded skeleton node TRS keyframes
```

**Decoded**: contiguous skeleton-node table, per-node 2 TRS keys (position/quaternion/scale), a name-stable bone ID (`size_hint == 84 + id`), and `key_count` (3 components for TRS nodes, 1 for rotation tracks — corpus-verified on 56,838 nodes). **Limitations**: animation playback semantics in-game are unconfirmed.

## 6. Identify media formats / WAV, TGA, BMP round-trip (partial)

**What it does**: Identifies common GTL/GTR2 media files (WAV/DDS/TGA/BMP/JPG/MP3/BIK), parses basic headers, detects BMP-as-TGA quirk, and performs semantic round-trip for WAV PCM, TGA type 2/3/10, and uncompressed BI_RGB 24/32-bit BMP.

**How to ask**:
- "Identify this DDS/BMP/BIK file."
- "Round-trip this WAV/TGA/BMP file and verify it."

**Commands**:
```bash
python3 media_tool.py info <file>
python3 media_tool.py wav-roundtrip <src.wav> <dst.wav>
python3 media_tool.py tga-roundtrip <src.tga> <dst.tga>
python3 media_tool.py bmp-roundtrip <src.bmp> <dst.bmp>
```

**Limitations**: DDS reads cover DXT1/DXT3/DXT5, BC4/BC5, all 14 BC6H UF16/SF16 modes and all 8 BC7 modes, plus uncompressed RGB(A); writes cover DXT1/DXT3/DXT5, BC4/BC5/BC6H/BC7 (byte-exact when unedited) and uncompressed RGB(A); cube maps round-trip byte-identically but faces are not exposed to other tools; TGA limited to type 2/3/10; BMP limited to uncompressed BI_RGB 8/24/32; all WAV round-trips are byte-lossless (compressed payloads included); JPG/MP3 metadata parsed but full semantic decode/encode/edit not implemented; BIK decode via ffmpeg (`media_tool.py bink-decode`) and BIKi encode via external LGPL `bink_build` (`media_tool.py bink-encode`).

## 7. Decrypt SimBin JCA files (Race 07, Volvo, etc.)

**What it does**: Decrypts/encrypts SimBin JCA files (GMT, `.gdb`, `.trk`, `.scn`, `.cam`) with all 8 versions and known game keys. GPLv2 implementation.
**How to ask**:
- "Decrypt this Race 07 GMT and check its magic."
- "Decrypt this Volvo `.trk` with the volvo key."

**Commands**:
```bash
python3 jca_crypt.py decrypt <file.gmt> <out.gmt>
python3 jca_crypt.py encrypt <file> <out.jca> --version 3
```
**Limitations**: Only known JCA keys/versions; JCA is unrelated to ISI 16-byte-header encryption.

## 8. Read AIW / SCN / TRK semantics (partial)

**What it does**: Extracts waypoints/features from `.aiw` and SearchPath/MASFile/SkyBoxI from `.scn`/`.trk`.
**How to ask**: "What MAS files does this TRK reference?" / "How many waypoints does this AIW have?"

```bash
python3 simbin_text_tool.py aiw <file.aiw>
python3 simbin_text_tool.py scn <file.trk>
python3 simbin_text_tool.py aiw-convert <rfactor.aiw>   # prints SimBin-style AIW
```
The `aiw-convert` mode applies the rFactor→GTR2/GTL rules from the AIW Repair Utility: scale `wp_galpha` by 0.45, drop 12 rFactor-only waypoint tags, and replace `wp_cheat` with `wp_event=(1.000,0,0)`. CRLF line endings, indentation and inline comments are preserved; inputs already in SimBin style are left unchanged (detected by the absence of rFactor-only tags).

## 9. Prototype conversion tools (unvalidated geometry)

**What it does**: Structural and semantic old→new GMT bridges (`gmt_semantic.py` decodes positions/UVs/indices) and an archive-level rF1→GTR2 pipeline (unpack → decrypt → convert → repack → validate) with optional offset relayout after mesh edits.
**How to ask**: "Try converting this rFactor archive to GTR2 and tell me what was validated."

```bash
python3 gmt_layout.py <old.gmt> <new.gmt>
python3 -c "import gmt_layout,pathlib; pathlib.Path('new.gmt').write_bytes(gmt_layout.old_to_new_semantic(pathlib.Path('old.gmt').read_bytes()))"  # semantic
python3 rf1_to_gtr2.py <archive.mas> <out.gtr>
python3 rf1_to_gtr2.py <archive.mas> --check
python3 rf1_to_gtr2.py <archive.mas> <out.gtr>   # semantic bridge preserves all submeshes (default)
python3 rf1_to_gtr2.py <directory> --tree        # check every archive in a tree
python3 rf1_to_gtr2.py <archive.mas> <out.gtr> --structural   # legacy single-submesh bridge
```
**Limitations**: Geometry is preserved structurally and validated on 60 real GMTs, but no ground-truth pair exists and in-game behaviour is NOT validated.

## 10. Read GTTF / IRSR headers (partial)

**What it does**: Reads time-trial/replay magic, version, track/scene filenames, embedded strings, and decoded metadata (driver/co-driver/team/car) from gzip payloads.
**How to ask**: "Which track and driver does this replay reference?"

```bash
python3 simbin_events_tool.py <file.gtt|file.vcr>
```
**Decoded**: GTTF metadata, GTL-IRSR, GTR2-IRSR and rF1-IRSR framing; the 63-byte GTTF frame grid (`--frames`); and the full replay frame stream for both GTR2 v1.05 and GTL v1.01 (participant names, car/skin files, activity windows, frame counts, sub-records and absolute session times). `--replay` reports all of this, including the decoded first-driver world position and heading-like value. All 9 GTR2 and 4 GTL replays, plus 142 Driving School `.dsi` files, parse to exact EOF; `.dsi` ghost polylines are the decoded frame positions. `shift_replay_times()` can shift replay timestamps consistently. Decoded driver-state channels include a steering-like pair difference (`shorts[0]-shorts[1]`, 8/8 replays) and a vertical-motion channel (`small_a`, 8/8 replays); `--channels` exports both as CSV for cross-recording analysis; `python3 simbin_events_tool.py <replay_dir> --summary` prints a per-file table of steering/elevation channel correlations. The SimBin text CLI (`simbin_text_tool.py scn|cam|aiw|aiw-convert`) now transparently decrypts JCA-wrapped Race07/Volvo/RaceRoom configs. **Limitations**: `small_b` and the u16 units/wheel assignment remain uninterpreted, as do the HAT per-record identifier and trailing stream; game acceptance of edited replays is untested.

## 11. Inspect setups, descriptors and legacy audio/config containers

**What it does**: Parses rFactor `.veh` vehicle descriptors and `.svm` car setups, identifies gzip `.hat` track data and NASCAR-era `.hdr`/`.dat` MP3 audio pairs, and recognises CUBEASF scene files.

**How to ask**: "Parse this .veh descriptor" / "Identify this .svm setup" / "Decompress this .hat file" / "Decode this .hdr/.dat audio pair."

```bash
python3 media_tool.py hat-decompress <file.hat> <out.bin>
python3 media_tool.py hdr-dat-decode <file.hdr> <out.wav>
python3 media_tool.py info <file.svm|file.hat|file.hdr|file.veh|file.scn>
python3 -c "import simbin_text_tool as s; print(s.parse_veh(open('car.veh','rb').read()))"
```

**Decoded**: `parse_veh()` (2,763 files, 57 keys; also handles 42 `.inccar` configs with 100 keys), `parse_hdv()` (156 files, 17 sections/496 keys), `parse_svm()` (21,141 setups classified), `parse_set()` (22 CUBEASF camera files), `parse_sp()` (172 suspension files with body-reference validation), `parse_hed()` (88 head-physics files, fixed 5-spring order), `parse_skn()` (262 skin descriptors with nested Layer/Word validation), `parse_rcd()` (5,047 race configs in 4 families), `parse_grb()` (248 gearbox files, b/a ratio semantics), `parse_eng()` (333 engine files, rising RPMTorque curves), `parse_cin()`/`parse_scr()` (409 cinematic + 123 scene scripts), `parse_gdb()`/`parse_car()` (4,672 race/vehicle configs, structural validation), `parse_aud()` (364 sound maps), `parse_dmg()` (200 damage configs, 43 universal keys), `parse_scn()` (also handles 417 `.cas` and 294 `.gen` descriptors), `hat_decompress()` (188 gzip files) and `hdr_dat_mp3()` (1,982 pairs). **Limitations**: 10 encrypted `.svm` payloads, the `.hdr` index table, and the GTTF/PHYSICS opaque fields remain undecoded.

## 11. Consult format documentation

**What it does**: Provides evidence-based notes for GTL/GTR2 binary formats.

**How to ask**:
- "What do we know about the GMT format?"
- "Which GTR2/GTL binary formats can we read/write?"
- "What are the blockers for full format support?"

**Files**:
- `docs/gmt-format.md`
- `docs/binary-formats.md`
- `docs/file-formats.md`
- `docs/reuse-rfactortools.md`
- `docs/task-plan.md`
- `CAPABILITIES.md`
- `CHANGES.md`

## 12. Corpus comparison and diagnostics

**What it does**: Compare same-name files in two corpora (optionally inside MAS archives) to find safe carry-over candidates; check GMT material prefixes against SimBin conventions.
**How to ask**: "Which GTL/GTR2 files are byte-identical?" / "Does this GMT have SimBin-safe surface names?"

```bash
python3 corpus_diff.py <dirA> <dirB> --ext gmt --archives
python3 validate_materials.py <file.gmt>
```

## 13. Run pre-push safety/privacy checks

**What it does**: Scans tracked files and commit metadata for secrets, personal home paths/emails, credentials in remote URLs, oversized/game-data files, untracked files, and commit identity mismatches.
**How to ask**: "Check whether this repo is safe to push to GitHub."

```bash
python3 pre_push_check.py
```
**Notes**: The username `shovas` and its GitHub noreply email are explicitly allowlisted. Editor swap files (`*.swp`) and `__pycache__` are ignored by `.gitignore`.

## 14. Run tests

**What it does**: Runs the unittest suite covering MAS, GMT, DSI/HAT/GTT/VCR, and FXM tools.

**How to ask**:
- "Run the tests."
- "Verify the GMT round-trip tests pass."

**Command**:
```bash
python3 run_tests.py --mode quick|normal|full
```

## 15. Inspect CUBE MTS meshes (Nascar SimRacing / F1C lineage)

**What it does**: Parses 4.10/4.20 mesh headers, geometry tables, submesh records, vertex/normal blocks and material records.

**How to ask**: "Show the decoded geometry of this CUBE MTS mesh."

```bash
python3 mts_format.py <file.mts>
python3 mts_format.py --detail <file.mts>
```

**Decoded**: 8-u32 geometry table, two submesh-record layouts, 36-byte vertices / 16-byte normals, 4.10 material records. **Limitations**: material IDs reference an external table not present locally; no triangle/index block in this layout.

## 16. Inspect `RaceGMT` material/stage blocks (Race 07 DLC)

**What it does**: Decodes 264-byte stage blocks into material groups with stage types and texture channels.

**How to ask**: "List the materials and texture channels in this Race 07 mesh."

```bash
python3 race_gmt.py --materials <file.gmt>
```

**Decoded**: stage-type enum at +256 and per-material texture-channel index at +260. **Limitations**: the 36-byte position grid is experimental and is not a validated triangle decoder.

## GTL -> GTR2 conversion (building block)

**What it does**: Converts the GTL container layer to GTR2 conventions — rewrites `.trk` `MASFile=` entries (`.gtl`→`.gtr`, teammaps2, `Misc.gtr`) and repacks `.gtl` archives as `.gtr`, and can copy GTR2 session keys into GTL `.gdb`/`.car` files from a same-track/same-vehicle GTR2 template.

**Commands**:
```bash
python3 gtl_to_gtr2.py <source.gtl> <target.gtr>
python3 gtl_to_gtr2.py <source.gtl> --check
python3 gtl_to_gtr2.py --validate <GameData-dir>
```

**Limitations**: geometry, physics, vehicle/track config and in-game correctness are not converted or validated.

## FXM semantic decoding

`fxm_tool.py semantic <file>` decodes and validates FXM skeleton nodes from both file variants. **Limitations**: animation-to-mesh binding and in-game playback remain unresolved.

## JCA-encrypted audio

`media_tool.py jca-decrypt <src> <dst> [--key NAME]` decrypts any JCA-wrapped payload (WAV/DDS/TGA, plus text configs and shaders); `wav-decrypt` is an alias for WAV. It decrypts SimBin JCA-wrapped WAV files to plain RIFF/WAVE; `media_tool.py wav-decode <src.wav> <dst.wav>` converts ADPCM/MP3-in-WAV payloads to PCM and `wav-encode` encodes back; JCA keys auto-detected. **Limitations**: compressed (MP3/ADPCM) WAV payloads still round-trip losslessly rather than being transcoded.

## JPG / MP3 semantic conversion

`media_tool.py jpg-decode|jpg-encode` (Pillow) and `mp3-decode|mp3-encode` (ffmpeg) convert between compressed media and uncompressed PNG/PCM WAV. **Limitations**: lossy; metadata/tags are not preserved.

## Animation files

`anm_format.py <file.anm>` decodes ISIMotor animations (single- and multi-bone) to TRS keyframes. **Limitations**: keyframe semantics in-game are unvalidated.
