# GTL `.PHS` investigation (2026-11-23)

## Conclusion

The five GTL `.phs` MAS members are **not encrypted physics data**. Four of them are
PAR2-style recovery containers for a single file, `GTL_Update_0901.exe`; the fifth
(`PHYSICS.PHS`) is a small opaque high-entropy blob with no PAR2 packets. The
"PHYSICS/CARS/DRIVERS/AI/TRACKS" names are archive member labels, not evidence of
gameplay physics content. No evidence was found that GTL reads PHS contents as
structured physics data.

## Evidence table

| Evidence | Class | Source |
|---|---|---|
| 5 members (`AI.PHS`, `TRACKS.PHS`, `DRIVERS.PHS`, `PHYSICS.PHS`, `CARS.PHS`) in 3 archives | Observation | `mas_tool.read_archive` |
| MAS entries are zlib-compressed; `size < zsize` by only 0.03–0.08% | Observation | MAS entry metadata |
| Speednut `mas_extract.exe` under Wine extracts byte-identical PHS members | Observation | Wine run on `Physics2.gtl` |
| `.phs` literal absent from `GTL.exe`/`GTLDedicated.exe`; archives listed in `UIData/gtlui.mnu` `Source_MAS` | Observation | `strings`, menu file |
| 3 of 5 files contain `PAR2\0PKT` packets with contiguous length chain | Observation | `phs_tool.find_packets` |
| Header is 64 bytes: magic(8), u64 length, set id(16), constant hash(16), type(16) | Observation | hexdump |
| Constant 16-byte hash `7a8c71fb...` equals MD5 of the canonical Main-packet body | Observation | SHA/MD5 check |
| Main packet: slice size 384000, 1 file, id `2f1fc214fdfa91110008fa2a52a622d1` | Observation | `phs_tool.parse_main` |
| FileDesc packet names `GTL_Update_0901.exe` with the same file id | Observation | `phs_tool.parse_filedesc` |
| Large packets are `RecvSlic` (PAR2 recovery slices), high entropy | Observation | type field + entropy |
| `PHYSICS.PHS` has no PAR2 packets; 13064 bytes, pure entropy | Observation | scan |
| No standard compression on decompressed bytes (skip 0..64); no repeating-key XOR | Observation | prior probes |
| Pairwise PHS XOR retains ~7.99 bits/byte | Observation | prior probe |
| PHS are PAR2 recovery data for an update executable | **Inference** | packet metadata |
| GTL does not need PHS for gameplay | **Inference** | no `.phs` string in exe; update-file target |
| `PHYSICS.PHS` is also recovery data (slices only) | Speculation | size/entropy only |

## Ranked hypotheses

1. **PAR2 recovery data for `GTL_Update_0901.exe`** — supported by Main/FileDesc
   metadata, contiguous packet chain, recovery slices, and incompressible payloads.
   Highest confidence.
2. **Unused update artifacts shipped in MAS archives** — supported by the update
   executable target, absence of `.phs` in executables, and UI-menu-only archive
   references. No evidence of gameplay loading.
3. **`PHYSICS.PHS` is a recovery slice with no metadata packets** — plausible from
   size/entropy but unverified; could also be an unrelated opaque blob.
4. ~~Encrypted physics tables~~ — contradicted by plaintext PAR2 metadata and the
   update filename.
5. ~~Custom ISI/JCA cipher~~ — contradicted by PAR2 structure and prior cipher tests.

## Reproducible artifacts

- `phs_tool.py` — packet chain walker, Main/FileDesc parsers, string extractor
- `tests/test_phs_tool.py` — validates packet chain, Main metadata and FileDesc filename
- `docs/binary-formats.md`, `CHANGES.md` — experiment log

## Follow-up review (2026-11-23, second pass)

New angles tried that were not in the first investigation:

| Experiment | Result | Interpretation |
|---|---|---|
| `strings` for `PAR2`, `PAR 2.0`, `RecvSlic`, `FileDesc`, `Update_0901` across `GTL.exe`, `GTLDedicated.exe`, `GTLConfig.exe`, `GTLReporter.exe`, and all DLLs | **No hits** | GTL binaries contain no PAR2 vocabulary; consistent with PHS being unused update artifacts, not proof (loader may use hashes/indices) |
| Runtime trace under Wine (`WINEDEBUG=+file`) | GTL exits with status 53; `Net.dll` needs `MFC42.DLL`, unavailable; winetricks `mfc42` fails (status 43) | Runtime consumer trace is **blocked by environment**, not by evidence |
| Compare `RecvSlic` bodies across AI/TRACKS/CARS | Distinct bodies, exponent fields `0x3b`, `0x3a`, `0x35`; each body MD5 differs | Distinct recovery slices for one file — expected PAR2 behaviour |
| Entropy of slice bodies vs controls | Slice bodies 7.9996 bits/byte ≈ `os.urandom` 7.9969; compressed BIK 7.73; zlib text 2.67 | Uniformly random, consistent with Reed–Solomon parity data |
| File length divisibility | 384000-byte slice size; files hold 1–2 full slices plus metadata/partial slices | Consistent with truncated/partial PAR2 sets |
| `PHYSICS.PHS` entropy | 7.986 (slightly below the other four); no PAR2 packets | Still opaque; could be a partial slice or unrelated blob |

Excluded by this pass: a literal PAR2-aware loader in the GTL binaries; a feasible
Wine runtime trace in this environment; identical recovery slices across the PHS
files. None of these contradict the recovery-container conclusion.

## Static consumer analysis (2026-11-23, second pass)

- **No game-code references**: `GTL.exe`, `GTLDedicated.exe`, all DLLs contain **no**
  `.phs`, `Physics2.gtl`, `AIStrat.gtl`, `LiveTrack2.gtl`, `PHYSICS.PHS` or `CARS.PHS`
  strings. The only references are in `UIData/gtlui.mnu` as `Source_MAS` entries
  (lines 25-27), alongside UI archives (`GTLOptions1/2.gtl`, `UIAssets.gtl`).
- **Archives contain only PHS**: `Physics2.gtl` = DRIVERS/PHYSICS/CARS.PHS,
  `AIStrat.gtl` = AI.PHS, `LiveTrack2.gtl` = TRACKS.PHS — no UI assets at all.
- **Inline-immediate search (radare2)**: searched GTL.exe for `50 53 48` ("PHS") as an
  inline comparison constant — 3 hits at 0x72f1f4/0x72f208/0x72f218, all part of
  `PSHADEBUMPEXDECL`/`PSHADEBUMPDECL`/`PSHADEEXDECL` pixel-shader strings. **False positives**;
  no PHS extension-dispatch constant exists.
- **Cross-correlation with plain-text physics**: 4,672 `.rcd/.hdv/.veh/.tyr/.gen` files
  across 8 corpora (entropy 4.95, 100% printable) vs PHYSICS.PHS (entropy 7.986, 38%
  printable, all 256 byte values) — zero of 4,787 extracted tokens appear in PHS.
  **No structural match**; PHS is not a simple encoding of known physics text.
- **Full zlib scan**: scanned all 13,064 byte offsets — one `0x78 0x9c/da/01/5e`-like
  header, but no valid zlib decompression anywhere. Combined with the earlier bit-shift
  and skip scans, standard DEFLATE is excluded at any alignment.
- **Truncated-slice test**: PHYSICS.PHS's 13,064 bytes share no 64-byte chunk with any of
  the four PAR2 containers' recovery slices at any alignment, and its length is not a
  simple fraction of the 384,000-byte slice size from their Main packet. So it is not a
  fragment of the same recovery set (though it could belong to a different set).
- **PAR2 recovery-slice test (fresh)**: all five PHS containers were scanned for PAR2 packets.
  PHYSICS.PHS contains **zero** PAR2 packets; the other four contain Main/FileDesc/RecvSlic packets,
  and the 7 RecvSlic bodies each hold a full 384,000-byte recovery slice (unique hashes). PHYSICS.PHS
  matches none of those slices (50/13,064 byte prefix agreement = chance), contains no slice as a
  substring, and the best XOR combination of all 7 slices gives 69/13,064 (chance ≈51). It is therefore
  not a truncated slice from this PAR2 set, nor an XOR of its slices. The `GTL_Update_0901.exe` string
  occurs only in DRIVERS.PHS; no EXE or update-named file exists anywhere in the GTL install to compare against.
- **Arbitrary-offset window test**: scanned all 7 recovery slices at 64-byte steps for a 13,064-byte window matching PHYSICS.PHS (sampling every 16th byte): best 12/816 matches — chance level. It is not a window of any slice.
- **Recovery-slice exponent test**: the 7 `RecvSlic` bodies carry 4-byte PAR2 exponents; PHYSICS.PHS's
  leading u32 (0x6050b465) matches none of them, so it is not a bare recovery-slice body from that set.
- **Distribution comparison**: PHYSICS.PHS byte entropy 7.986 (chi2 0.993 vs uniform) is statistically
  indistinguishable from the RecvSlic recovery-slice bodies (7.984-7.985, chi2 1.04-1.11), supporting a
  parity/recovery-data classification without proving exact slice identity.
- **Interpretation**: the UI source-MAS loader likely opens these archives looking for
  UI/localization assets and finds none relevant; the PHS members are not dispatched
  to any physics consumer by name. Strong evidence PHS data is **unused by GTL
  gameplay** — consistent with leftover update/recovery artifacts bundled in the
  install. This is a resource-identification result, not a decoded consumer routine.

## Recommendation

**Defer further decoding.** The recovery-data hypothesis is structurally validated;
the remaining high-entropy bytes are parity data whose "decoding" would only
reconstruct `GTL_Update_0901.exe`, which is not part of the game's gameplay assets.
`PHYSICS.PHS` needs no action unless a consumer is found. Revisit only if GTL runtime
tracing shows PHS members being read by a named subsystem.
