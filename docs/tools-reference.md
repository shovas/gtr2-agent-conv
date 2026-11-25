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

## Practical rules

- Read these mirrors for format specs, signatures and algorithm details; prefer native Python in this repo for pipeline integration.
- Licences: Luigi's tools are GPLv2; QuickBMS scripts have their own terms; `gtl_files.py` has no explicit licence. **No code or binaries from these folders are copied into the repository** — implementations in this repo are independent rewrites from published algorithm descriptions.
