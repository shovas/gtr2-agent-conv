# Dependencies

## Runtime

- **Python 3.9+** - required to run tools and tests. Development/testing has used Python 3 on Linux.
- **Python standard library only** - current tools/tests use stdlib modules such as `argparse`, `dataclasses`, `gzip`, `pathlib`, `re`, `struct`, `unittest`, `wave` (where applicable).

## Optional / external (not bundled)

- **`../rfactortools`** - reference Python package and C sources; useful for comparison and for `rfactordec.c` / `_crypt` experiments. Not required by current project tests.
- **`../aluigi-mirror-261124/` and `../quickbms-mirror/`** - offline mirrors of Luigi Auriemma's GPLv2 tool sources (`rfactordec`, `rfactorgmdec`, `wtcced`) and QuickBMS scripts. Used as format/algorithm references only; no code or binaries copied. Inventory in `docs/tools-reference.md`.
- **`../gtl-tools/gtl_files.py`** - reference utility for GTL-specific `.gtl` MAS and gMb 'Encryptomatic' crypt; documents a cipher distinct from `rfactorgmdec`. Read-only reference; no code copied.
- **Game corpora under `../`** - many local game installs used as format oracles/reference data; the full list is in `AGENTS.md`. Not required; tests skip when absent.
- **`monodis` / .NET tooling** - used once to cross-check the JCA implementation against a third-party decryptor; not required for normal use.
- **GCC / Python headers** - only needed if experimenting with building ISI decrypt/encrypt C code (`rfactordec.c` / `_crypt` extension). Not required for normal tool use.
- **Pillow or other image libraries** - not currently required. Would be needed for semantic DDS/TGA/BMP/JPG read/write/edit beyond lossless copy/identification.
- **ffmpeg** (optional) - `media_tool.py bink-decode` / `tgq-decode` call the `ffmpeg` binary for BIK and EA TGQ video decode. Tests skip if absent.
- **`bink_build` from `raynorpat/libbink`** (optional, LGPL-2.1) - external encoder used by `media_tool.py bink-encode`; invoked as a separate executable (set `BINKBUILD` or put it on `PATH`), its code is not copied into this repo. Test skips if absent.
- **Bink SDK/licensed tools** - not required: decode uses ffmpeg and BIKi encoding uses the external LGPL `libbink` (validated round-trip on real GTR2 BIK).

## Development

- **git** - repository history/change tracking.
- **unittest** - built into Python; used for tests.
- **`coverage`** (optional) - enables `run_tests.py --coverage`; without it the runner still works and prints an "unavailable" notice.

## Notes

- Keep external reference repos/data outside this repository unless explicitly decided otherwise.
- Do not add heavyweight dependencies without documenting them here and in `README.md`.
- `jca_crypt.py` / `jca_tables.py` are GPLv2 (derived from the published `wtcced` algorithm/tables); all other modules are unaffected.
- `libbink` (external encoder) and the GPLv3 Blender GMT importer (format-reference only) are LGPL/GPLv3 projects consulted as references; no third-party code was copied into this repo.