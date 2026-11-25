# External tool mirrors (reference only)

Three new read-only folders were added under `../`. They are **format/tool references**, not game corpora; nothing from them is copied into this repository. Maintain `docs/corpus-reference.md` for game data and this file for tool inventories.

## `../aluigi-mirror-261124/` — full Luigi Auriemma mirror

202 MB / 4,405 files, root `mirror.aluigi.org/`.

| Section | Files | Contents |
|---|---|---|
| `papers/` | 294 (173 ZIPs) | Source + binaries for decompression/decryption tools; includes `rfactordec.zip`, `rfactorgmdec.zip`, `wtcced.zip`, QuickBMS builds/source, `quickbms.txt` (232 KB manual) |
| `mytoolz/` | 113 (64 ZIPs) | Small utilities (`wainfo`, `dump2func`, `exestringz`, compression helpers, etc.) |
| `bms/` | 2,762 | QuickBMS scripts; `mas.bms` (GMOTORMAS10/CUBEMAS4/ISI MAS) and `rfactor2.bms` (rF2 `GMOTOR_MAS_2.90`) are directly relevant |
| `adv/` | 881 | Security advisories; `rfactorx-adv.txt` documents an rFactor vulnerability |
| `patches/` | 192 (145 ZIPs) | Assorted game patches — potentially useful for missing update executables |
| `misc/`, `articles/`, `quickbms/`, `mymusic/` | 111 | Documentation, HTML indexes, images, music dumps |

### Relevant tool sources (verified 2026-11-26)

- **`papers/rfactordec.zip`** → `rfactordec.c` (26 KB) + Windows binary. Signature table (rFactor `0x38af5637e81bc9a0`, ARCA, ACTC, Top Race 2009, Superleague, GSC, etc.) and `isi_crypt`/`isi_key` implementation — the reference for our `isi_crypt.py`. GPLv2 (Luigi Auriemma).
- **`papers/rfactorgmdec.zip`** → `rfactorgmdec.c` (9 KB) + binary. Decrypts **encrypted `//[[gM` text configs** with a 256-byte key permutation and a game-dependent `keynum`: rFactor `0`, ARCA/ACTC `0x000b2023`, Top Race 2009 `0x000dfc2a`, Superleague `0x0001be0b`. GPLv2. **Verified against our corpus:** decrypted all 10 encrypted `.svm` files (keynum 0) and all 18 `gMb1.002f` configs (TC2000/TR2009 use `0x000dfc2a`, Superleague uses `0x0001be0b`) to 100% printable text. Reimplemented independently as `isi_gm_crypt.py`.
- **`papers/wtcced.zip`** → `wtcced.c` (21 KB), `blowfish.c/.h`, `wtcc_bf.h` (38 KB table), `utils.c` + binary. JCA/Blowfish encrypter/decrypter for SimBin Race/GTR Evolution/Volvo/RaceRoom. GPLv2; format oracle already used for `jca_crypt.py` / `jca_tables.py`. No source copied.
- **`bms/mas.bms`** and **`bms/rfactor2.bms`** — MAS container and rF2 encryption spec cross-checks; our `mas_tool.py` covers the GTR2/rF1 variants natively.

## `../quickbms-mirror/` — earlier, smaller mirror

99 MB / 1,025 files, root `aluigi.altervista.org/`. Subset of the above (papers 293 / 173 ZIPs, bms 81, mytoolz 110, adv 507, misc 5, quickbms 4). Contains the **same three relevant tool ZIPs** with identical sizes/checksums, plus the archived `papers.htm` that lists them. Useful as a stable offline copy and as the source of the Wayback-verified tool URLs; documentation above applies equally.

## `../gtl-tools/` — GTL-specific format utility

One file, `gtl_files.py` (5.4 KB), reverse-engineered from GTL.exe (Steam, MD5 `39f5eb5118e9156cece840b4d6bab97b`). CLI: `list` / `extract` GMOTORMAS10 `.gtl` archives, `decrypt` / `encrypt` GTL `gMb` configs.

Verified findings from its documentation and code:

- `.gtl` archives are plain gMotor MAS with zlib members — matches our `mas_tool.py` type 1.
- GTL `gMb1.000f` uses a **different cipher** ("Encryptomatic V1.0"): header embeds a u32 key; per-byte state uses a fixed 256-byte table **plus a nibble layer derived from MS CRT `rand()`**, and rotates the key with `ctr`. Documented keys: `0x22c6` (`garage.gar`), `0x1c79` (challenge/awards), `0x4d7` (career stats); `.pm` physics files take the key from their caller.
- `isi_gm_crypt.py`'s rfactorgmdec algorithm **does not** decrypt GTL's own `gMb` files (0.34 printability with key 0), and `gtl_files.decrypt_file()` **does not** decrypt our rFactor `.svm` / `gMb1.002f` files (0.34 printability). The two algorithms share the `//[[gMb...]]` header but are unrelated — an important correction to earlier assumptions.
- The file explicitly records that the `*.PHS` members are **not** this cipher (tested as text, binary and zlib), corroborating `docs/phs-research.md`.

## Full accounting of `../aluigi-mirror-261124/` (2026-11-26)

**4,405 files / 198,889,526 bytes (189.7 MiB).** Complete generated inventories:
- `docs/aluigi-mirror-manifest.tsv` — every file: section, relative path, size, extension.
- `docs/aluigi-mirror-archives.tsv` — all 461 ZIPs: path, size, member count, first 20 member names.

| Section | Files | Bytes | Main extensions / contents |
|---|---:|---:|---|
| `(root)` | 52 | 4,043,865 | 19 `.htm`, 8 `.php`, 5 `.txt`, 6 `.png`; site indexes and feeds |
| `adv/` | 881 | 4,828,755 | 875 `.txt` advisories, 3 `.pdf`; `rfactorx-adv.txt` (rFactor vulnerability) |
| `articles/` | 6 | 262,621 | 4 `.txt` articles, 1 `.htm`, 1 `.zip` |
| `bms/` | 2,762 | 4,711,914 | **2,757 QuickBMS scripts** + 2 `.xml`, 2 `.bat`, 1 `.txt` |
| `misc/` | 20 | 5,647,723 | 12 `.zip`, 4 `.txt`, 2 `.png`, 1 `.pdf`, 1 `.dll` |
| `mymusic/` | 66 | 50,098,980 | 65 `.zip` music rips + 1 `.txt` |
| `mytoolz/` | 113 | 6,788,045 | 64 `.zip`, 36 `.png`, 10 `.h`, 3 `.c` small utilities |
| `papers/` | 294 | 88,140,083 | **173 tool ZIPs**, 52 `.h`, 29 `.txt`, 24 `.c`, 9 `.png` |
| `patches/` | 192 | 34,101,295 | 145 `.zip`, 41 `.lpatch`, 6 `.txt` game patches |
| `quickbms/` | 19 | 266,245 | 16 `.png`, 3 `.htm` docs/screenshots |

By extension: `.bms` 2,758 · `.txt` 925 · `.zip` 461 · `.png` 69 · `.h` 62 · `.lpatch` 41 · `.c` 27 · `.htm` 26 · `.php` 8 · `.cfg` 5 · `.pdf` 4 · `.xml` 2 · `.bat` 2 · `.html` 1 · `.css` 1.

### HTML documentation (techniques and tool descriptions)

| Page | What it documents |
|---|---|
| `papers.htm` | Tool index. Relevant entries: **rfactorgmdec 0.2b** (encrypted `//[[gM`, keynums per game), **rfactordec 0.2.2** (encrypted GMT/DDS meshes, signature list, `-y` force mode), **wtcced 0.3.5** (SimBin JCA/Blowfish for Race07/GTR Evolution/Volvo/RaceRoom), and the note that rF2 needs QuickBMS. |
| `quickbms.htm` | QuickBMS scripting engine: `comtype` compression/decryption, `EXECUTE` external tools, scanning, generic AES/Blowfish/DES/RC4 examples. Lists `bms/mas.bms` for "ISI Gmotor engine MAS files" across rFactor, ARCA, BMW M3, **Sports Car GT**, NASCAR, F1 Challenge, Petrobras, and `rfactor2.bms` for rF2 `.MAS/.RFCMP`. |
| `old_index.htm` | 2007–2021 news/changelog with **115 relevant lines** documenting key additions: wtcced 0.3.3 RaceRoom JCA keys, 0.3.4/0.3.5 `raceroom`/`raceroom_plr`, volvo compatibility, rfactordec signatures (Game Stock Car 2011, Carretera 2012, Formula Truck 2013), rF2 QuickBMS script (2013). |
| `mytoolz.htm` | Small utility index (packet capture helpers, compression tools, PE/info utilities). |
| `index.htm`, `about.htm`, `articles.htm`, `misc.htm`, `patches.htm`, `poc.htm`, `pwdrec.htm`, `fakep.htm`, `keyres.htm`, `video.htm`, etc. | Site navigation, articles, patches, proofs-of-concept, password-recovery research, cd-key research, media. Less directly relevant; all indexed in the manifest. |

### Notable archives

- **papers/rfactordec.zip** (30,771 B) → `rfactordec.c`, `.exe`
- **papers/rfactorgmdec.zip** (8,983 B) → `rfactorgmdec.c`, `.exe` — source of our `isi_gm_crypt.py`
- **papers/wtcced.zip** (87,388 B) → `wtcced.c`, `blowfish.c/.h`, `wtcc_bf.h`, `utils.c`, `.exe`
- **papers/quickbms*.zip** (11–16 MB each) → Windows/Linux/macOS binaries and 0.12.0 source
- Other crypto-related ZIPs: `papers/EncryptX VB.net Conversion.zip`, `dwbdcrypto.zip`, `dwcryptonet.zip`, `pbmsdown.zip`, `pbmsgs.zip` — not racing-specific.

### `bms/gamestockcar_exe.bms` — embedded EXE resources (new decoder 2026-11-26)

Documents the `AXS.GS.0` container in GSC-family EXEs. Local corpora confirm it in 6 EXEs (GSC2012, Marcas, SCE, AMS; up to 637 resources each, including `.scn`, `.AIW`, `.MAS`). Implemented independently as `gsc_exe_tool.py`:

- `.keyMan` records hold SHA-1 key strings; one key is consumed per encrypted resource.
- Blowfish-CBC with big-endian blocks, IV = BF-ECB of eight zero bytes, plus the script's unaligned-tail XOR fix.
- `lzma86head` (13-byte header + raw LZMA) and LZ4 block decompression (pure Python).
- **Verified against QuickBMS 0.12.0 output** for `Marcas.exe`: 34 of 35 decoded files byte-identical; the 15.8 MB `.MAS` differs only in 7 final bytes plus 497 trailing padding bytes from QuickBMS's LZMA decoder. For `AMS.exe`: 626 of 627 decrypted files identical (one `.gen` differs in 19 bytes).
- **StockCarExtreme solved separately (2026-11-26):** SCE type-1 resources use `.keyMan` key at index `i + 11`; 204/204 validate and 207/218 resources extract (e.g. `bolognahistoric.scn` → 212,880-byte `CUBEASF`). The earlier negative came from an LZMA-props filter that excluded the valid `0x5D` properties byte. QuickBMS's own script still fails on SCE. `AMS.EXE` encrypted chunks are decrypted but **not** compressed by design, so `gsc_exe_tool.py` mirrors that limitation.

### Cross-check: `jca_crypt.py` vs wtcced 0.3.5 (verified 2026-11-26)

- Magic `0xFFFFB10F` (bytes `0f b1 ff ff`), XOR byte `0xEB`, all eight version→(key,keytable,compression) mappings and all custom keys (volvo, raceroom, raceroom_plr, old_raceroom) match wtcced source exactly.
- `jca_tables.py` contains the **first 3,090 identical 32-bit constants** of `wtcc_bf.h` (wtcced has 3 trailing zeros); regression test `test_jca_matches_wtcced_constants` verifies this from the mirror ZIP.
- Functional spot-check: `banner001.tga` (Race07Complete, JCA v3) reported by wtcced as version 3 / keytable 1 / 72,112 encrypted bytes / 262,188 output bytes; our `jca_crypt.decrypt_bytes()` produced 262,188 bytes with a valid TGA header (`00 00 02 00 ...`).

## Practical rules

- Read these mirrors for format specs, signatures and algorithm details; prefer native Python in this repo for pipeline integration.
- Licences: Luigi's tools are GPLv2; QuickBMS scripts have their own terms; `gtl_files.py` has no explicit licence. **No code or binaries from these folders are copied into the repository** — implementations in this repo are independent rewrites from published algorithm descriptions.
