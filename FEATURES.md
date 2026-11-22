# Features

End-user guide to what you can ask an agent to do with this repository. This project is WIP; features marked **partial** have known gaps.

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

**What it does**: Decrypts/encrypts ISI/rFactor 16-byte-header files (GMT/MAS-style), with GMT skip=4 handling.

**How to ask**:
- "Decrypt this GMT/MAS file."
- "Encrypt this file with a GSC/rFactor signature."
- "Check if this GMT is ISI-encrypted."

**Command**:
```bash
python3 isi_crypt.py <input> <output>             # decrypt
python3 isi_crypt.py -e -s 4b1dca9f960524e8 <in> <out>  # encrypt
```

**Limitations**: Only known ISI sign/key 16-byte-header variants. Unknown-signature files (e.g. DETOMASO_PANTERA_RAINSCREEN.GMT) remain unresolved.

## 3. Inspect GMT files (partial)

**What it does**: Parses GMT headers, mesh table records, material/stage string evidence, and observed vertex/stream layouts; diffs GMTs; performs structural lossless round-trip.

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
```

**Limitations**: Stage type (+256) and texture channel (+260) are decoded, but UV/LOD/shader/flag meanings, encrypted GMTs, and in-game geometry correctness remain unresolved.

## 4. Inspect/round-trip DSI/HAT/GTT/VCR gzip containers

**What it does**: Reads gzip-wrapped SimBin `.dsi`/`.hat` files, reports metadata, and round-trips content.

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

**Decoded**: contiguous skeleton-node table, per-node 2 TRS keys (position/quaternion/scale), and a name-stable bone ID (`size_hint == 84 + id`). **Limitations**: `key_count` meaning and animation playback semantics are unconfirmed.

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

**Limitations**: DDS limited to DXT1/DXT3/DXT5 and uncompressed RGB(A) mask-based formats, no mipmaps/cube maps; TGA limited to type 2/3/10; BMP limited to uncompressed BI_RGB 24/32; WAV compressed payloads (MP3/ADPCM) lossless-copy only; JPG/MP3 metadata parsed but full semantic decode/encode/edit not implemented; BIK decode via ffmpeg (`media_tool.py bink-decode`) and BIKi encode via external LGPL `bink_build` (`media_tool.py bink-encode`).

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
The `aiw-convert` mode applies the rFactor→GTR2/GTL rules from the AIW Repair Utility: scale `wp_galpha` by 0.45, drop 12 rFactor-only waypoint tags, and replace `wp_cheat` with `wp_event=(1.000,0,0)`.

## 9. Prototype conversion tools (unvalidated geometry)

**What it does**: Structural and semantic old→new GMT bridges (`gmt_semantic.py` decodes positions/UVs/indices) and an archive-level rF1→GTR2 pipeline (unpack → decrypt → convert → repack → validate).
**How to ask**: "Try converting this rFactor archive to GTR2 and tell me what was validated."

```bash
python3 gmt_layout.py <old.gmt> <new.gmt>
python3 -c "import gmt_layout,pathlib; pathlib.Path('new.gmt').write_bytes(gmt_layout.old_to_new_semantic(pathlib.Path('old.gmt').read_bytes()))"  # semantic
python3 rf1_to_gtr2.py <archive.mas> <out.gtr>
python3 rf1_to_gtr2.py <archive.mas> --check
```
**Limitations**: Geometry is preserved structurally and validated on 60 real GMTs, but no ground-truth pair exists and in-game behaviour is NOT validated.

## 10. Read GTTF / IRSR headers (partial)

**What it does**: Reads time-trial/replay magic, version, track/scene filenames, embedded strings, and decoded metadata (driver/co-driver/team/car) from gzip payloads.
**How to ask**: "Which track and driver does this replay reference?"

```bash
python3 simbin_events_tool.py <file.gtt|file.vcr>
```
**Decoded**: GTTF metadata, GTL-IRSR, GTR2-IRSR and rF1-IRSR framing, plus the 252-byte GTTF frame grid (position + timestamp; `--frames`). **Limitations**: remaining frame fields are uninterpreted.

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
python3 -m unittest discover -s tests -v
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
