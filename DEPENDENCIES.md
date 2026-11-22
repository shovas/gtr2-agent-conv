# Dependencies

## Runtime

- **Python 3.9+** - required to run tools and tests. Development/testing has used Python 3 on Linux.
- **Python standard library only** - current tools/tests use stdlib modules such as `argparse`, `dataclasses`, `gzip`, `pathlib`, `re`, `struct`, `unittest`, `wave` (where applicable).

## Optional / external (not bundled)

- **`../rfactortools`** - reference Python package and C sources; useful for comparison and for `rfactordec.c` / `_crypt` experiments. Not required by current project tests.
- **Game corpora under `../`** - many local game installs used as format oracles/reference data; the full list is in `AGENTS.md`. Not required; tests skip when absent.
- **`monodis` / .NET tooling** - used once to cross-check the JCA implementation against a third-party decryptor; not required for normal use.
- **GCC / Python headers** - only needed if experimenting with building ISI decrypt/encrypt C code (`rfactordec.c` / `_crypt` extension). Not required for normal tool use.
- **Pillow or other image libraries** - not currently required. Would be needed for semantic DDS/TGA/BMP/JPG read/write/edit beyond lossless copy/identification.
- **Bink SDK/licensed tools** - required for full BIK decode/encode. Not included; current support is identify/lossless copy only.

## Development

- **git** - repository history/change tracking.
- **unittest** - built into Python; used for tests.

## Notes

- Keep external reference repos/data outside this repository unless explicitly decided otherwise.
- Do not add heavyweight dependencies without documenting them here and in `README.md`.
- `jca_crypt.py` / `jca_tables.py` are GPLv2 (derived from the published `wtcced` algorithm/tables); all other modules are unaffected.