# rfactortools2gtr2

Tools and format documentation for converting ISIMotor-lineage sim content (rFactor, Race 07, GSC 2013/GSCE, BMW M3 Challenge, Automobilista 1, GT Legends, etc.) to **GTR2**.

This repository is a work in progress. It currently provides inspected format documentation and Python tools for reading/writing specific GTR2/GT Legends binary formats, with tests.

## Status

- **MAS archives (`.gtr/.gtl/.mas`, GMOTORMAS10)**: read/write supported, with real GTR2/GTL round-trip tests.
- **DSI/HAT gzip containers**: read/write supported, with content round-trip tests.
- **GMT meshes**: structural lossless read/write supported; partial field decode (mesh table, material/stage strings, vertex block layout, extra streams) with tests. Full semantics and encrypted GMTs are not fully resolved.
- **ISI encryption/decryption**: pure-Python ISI/rFactor sign+key decrypt/encrypt for GMT/MAS-style 16-byte-header files (`isi_crypt.py`), verified against rfactordec. Unknown-signature/non-standard encrypted GMTs may still be unresolved.
- **FXM/FXA/LMA**: header identification and lossless round-trip supported; internal animation/keyframe semantics undecoded.
- **BIK**: identify/lossless copy only (proprietary Bink codec).
- **Standard media (DDS/TGA/BMP/JPG/MP3/WAV/BIK)**: identified with basic header parsing; WAV PCM, TGA (type 2/3/10), BMP (BI_RGB 24/32), and DDS DXT1 (BC1, lossy) semantic round-trip supported; DDS header semantic parse; lossless byte copy possible. Full pixel/audio decode/encode not implemented for all formats; BIK proprietary.

See `CAPABILITIES.md` for details and `docs/` for format notes.

## Features

- Inspect/list/extract/create/update GMOTORMAS10 MAS archives (`mas_tool.py`).
- Inspect GMT headers/mesh/material structure and diff GMTs (`gmt_tool.py`, `gmt_format.py`).
- Decrypt/encrypt ISI 16-byte-header GMT/MAS files (`isi_crypt.py`).
- Inspect and round-trip gzip-wrapped SimBin DSI/HAT files (`gzip_simbin_tool.py`).
- Inspect and lossless round-trip FXM/FXA/LMA headers/containers (`fxm_tool.py`).
- Identify media formats and semantic WAV round-trip (`media_tool.py`).
- Format documentation for GMT and binary format inventory in `docs/`.

## Requirements

- Python 3.9+ (developed/tested with Python 3 on Linux).
- No third-party Python packages required for the current tools/tests.
- Optional/external references (not required, not included): `../rfactortools`, `../GTR2Steam`, `../GTLSteam`.

## Install / Setup

```bash
git clone <repo-url>
cd project
python3 -m unittest discover -s tests -v
```

No package install is required; tools are runnable as scripts from the repo root.

## First things to do

1. Run tests: `python3 -m unittest discover -s tests -v`
2. Inspect a MAS archive:
   ```bash
   python3 mas_tool.py list /path/to/file.gtr
   python3 mas_tool.py extract /path/to/file.gtr /tmp/out
   ```
3. Inspect a GMT:
   ```bash
   python3 gmt_tool.py info /path/to/file.GMT
   python3 gmt_tool.py scan /path/to/GameData
   ```
4. Read format notes: `docs/gmt-format.md`, `docs/binary-formats.md`.

## Repository layout

- `mas_tool.py` - GMOTORMAS10 archive tool.
- `gmt_tool.py` / `gmt_format.py` - GMT inspection and structural parser/writer.
- `isi_crypt.py` - Pure-Python ISI decrypt/encrypt for 16-byte-header files.
- `gzip_simbin_tool.py` - DSI/HAT gzip container tool.
- `fxm_tool.py` - FXM/FXA/LMA header/round-trip tool.
- `media_tool.py` - Media identification and WAV semantic round-trip.
- `docs/` - format documentation.
- `tests/` - unittest suite.

## License / third-party material

Check individual file headers and external reference repositories before reuse. Some reference material outside this repo has restrictive licenses (e.g. CC BY-NC); this repo treats them as reference only.
