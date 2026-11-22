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

**Limitations**: Does not fully decode material/stage numeric semantics, UV/LOD/shader/flag meanings, encrypted GMTs, or geometry conversion.

## 4. Inspect/round-trip DSI/HAT/GTT gzip containers

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

**Command**:
```bash
python3 fxm_tool.py info <file.fxm|file.fxa|file.lma>
```

**Limitations**: Internal animation/keyframe/node semantics are not decoded.

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

**Limitations**: DDS limited to DXT1/DXT3/DXT5 and uncompressed RGB(A) mask-based formats, no mipmaps/cube maps; TGA limited to type 2/3/10; BMP limited to uncompressed BI_RGB 24/32; WAV compressed payloads (MP3/ADPCM) lossless-copy only; JPG/MP3 metadata parsed but full semantic decode/encode/edit not implemented; BIK proprietary.

## 7. Consult format documentation

**What it does**: Provides evidence-based notes for GTL/GTR2 binary formats.

**How to ask**:
- "What do we know about the GMT format?"
- "Which GTR2/GTL binary formats can we read/write?"
- "What are the blockers for full format support?"

**Files**:
- `docs/gmt-format.md`
- `docs/binary-formats.md`
- `CAPABILITIES.md`

## 8. Run tests

**What it does**: Runs the unittest suite covering MAS, GMT, DSI/HAT/GTT, and FXM tools.

**How to ask**:
- "Run the tests."
- "Verify the GMT round-trip tests pass."

**Command**:
```bash
python3 -m unittest discover -s tests -v
```
