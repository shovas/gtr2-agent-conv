# GTL `.PHS` investigation (2026-11-23)

## Conclusion

The five GTL `.phs` MAS members are **not encrypted physics data**. Four of them are
PAR2-style recovery containers for a single file, `GTL_Update_0901.exe`; the fifth
(`PHYSICS.PHS`) is a small opaque high-entropy blob with no PAR2 packets. The
"PHYSICS/CARS/DRIVERS/AI/TRACKS" names are archive member labels, not evidence of
gameplay physics content. No evidence was found that GTL reads PHS contents as
structured physics data.

## Runtime consumer search (2026-11-28)

Searched all **29** shipped `.exe`/`.dll` binaries in `GTLSteam` and `GTR2Steam` (including the unpacked `GTL.exe` and `GTR2.exe`) for `.PHS`, `.phs`, `PHS\0`, UTF-16LE `PHS`, `PHYSICS` and UTF-16LE `physics`. **Zero matches in every binary.** `GTL.exe` contains no PHS-related strings at all, so there is no evidence that the game loads these members as physics data. This closes the "find the runtime consumer / loading routine" avenue as a negative rather than an untried task; full-tier regression test added.

Note: the EXEs are unpacked PE images (`GTL.exe` sections `.text`/`.rdata`/`.data`), so the negative is not explained by packing.

## PAR2 recovery-slice coverage (2026-11-26)

Enumerated every PHS packet chain: `AI.PHS`, `TRACKS.PHS` and `CARS.PHS` each contain one `Main` packet and one `RecvSlic` packet; `DRIVERS.PHS` has only `FileDesc` (naming `GTL_Update_0901.exe` with file id `2f1fc214…`); `PHYSICS.PHS` has no PAR2 packets. The Main packets agree on slice size **384,000** bytes, file count 1 and the same file id. The three recovery bodies are 384,004 bytes each with exponents **53, 58, 59** and all share the same file id — total 1,152,012 bytes = **3 slices**. The 61,334,805-byte GTL 1.1 updater implies ~160 source slices at that size, so these cover ~1.9%; moreover exponents 0–52 and 54–57 are absent. **Reconstruction is infeasible** from the local PHS data even if the exact 0.9.01 executable were available. Regression test added (`tests/test_phs_tool.py`).

## Updater acquisition attempt (2026-11-26)

A direct GTL 1.1 updater was obtained from the Patches Scrolls page: the download link resolves to `download.php?g=GT+Legends&f=gtl_update_1100.zip`, then a session-cookie `GET /get.php` serves a **60,724,988-byte** ZIP. Its three members are `GTL_Update_1.1.0.0.exe` (61,334,805 B), `Readme 1.1.0.0.txt` and `Game Patches.url`; the readme's 35 changes contain no PHS/physics entries. A full `strings` scan of the executable found **zero** occurrences of `0901`, `PHYSICS.PHS` or `.phs`. Probing the same site for `gtl_update_0901.zip` / `GTL_Update_0901.exe` (and variants) returns **404**; a web search for the exact filename returns no results. The artifact was kept under `/tmp` only and is **not** committed (third-party executable, read-only reference). This closes the most promising acquisition lead: the missing `GTL_Update_0901.exe` and its PAR2 set are still unavailable, so the PHS blocker remains genuine. Unblock conditions now require a different archive/source for the 0.9.01 updater or a PAR2 spec enabling reconstruction from the four local PHS containers.

## Mirror reassessment (2026-11-26)

Searched `../aluigi-mirror-261124/mirror.aluigi.org/` in full: `patches/` (192 files, 145 ZIPs, 41 `.lpatch`) has **zero** filenames or ZIP members matching GTL/Legend/0901/PHYSICS/PAR2; all 461 ZIPs in the mirror likewise contain zero matching member names. A wider `../` filename search for `*0901*`, `*gtl*update*`, `*gtl*patch*`, `*.par2` found nothing relevant. The new tool mirrors added format knowledge (rfactordec/rfactorgmdec/wtcced) but **no missing update executable or PAR2 set**, so the PHS blocker remains genuine.

## Archive-container negative (2026-11-25)

A full-byte scan of the 13,064-byte `PHYSICS.PHS` member found **zero** ZIP local/central/EOCD/Zip64 signatures (`PK\x03\x04`, `PK\x01\x02`, `PK\x05\x06`, `PK\x06\x06`, `PK\x06\x07`), no 7z header magic (`37 7a bc af 27 1c`), and no RAR4/RAR5/MSCF signatures. The final 256 bytes contain no u32 value that points into the file (0/64 inward offsets), ruling out a trailing central-directory/index structure. Combined with the earlier PAR2, ISI-crypt, compression, XOR and entropy negatives, the blob has no identifiable container structure; no decoder is promoted.

## Equivalent-data search in other generations (2026-11-27)

Checked GTR2Steam, Race07Complete, RF1Vanilla, Automobilista, StockCarExtreme,
F1C, F12002 and NT2004 for `.phs`/`.PHS` files or other physics containers:
zero matches. Those generations express head/physics data as text
(`HeadPhysics.ini`, `.hed`), not a PHS-like archive. GTL's `Physics2.gtl`
remains the only such container locally, so the "equivalent payload in another
generation" bypass is closed. Full-tier guard added.

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
| ISI crypt forced enctype 0/1, skips 0..64 | best printability 0.427 (from 0.384), entropy still ~7.8 — no valid decrypt | **Excluded** as a simple ISI-crypt payload |
| PAR2 slice reconstruction: search all four sibling PHS files for PHYSICS.PHS's first 64 bytes | no match; PHYSICS.PHS also lacks the PAR2 set id and `PAR2\0PKT` magic; the `GTL_Update_0901.exe` target is not present locally | **Unverifiable offline** — needs the update executable or a full slice set |
| 256/512-byte record stride on PHYSICS.PHS (13,064 bytes) | no repeating header prefix; 8-/264-byte tails | **No structure found** |
| Raw-deflate brute force at **every** byte offset 0..13,061 (wbits -15/31/47) | only 3 tiny decompressions (317/109/139 bytes) yielding repetitive garbage (`c7 c7...`, `<<<<...`) | **Excluded** as a deflate/zlib stream anywhere in the blob |
| First 8 bytes as ISI signature (rF1 `0x38af...` / GSC `0x4b1d...`) | parsed as u64 `0x5c45fc1e6050b465`, no match; XOR byte patterns with either signature are random | **Excluded** as a standard ISI-crypt header |
| Byte-overlap with sibling PAR2 recovery data | full 13,064-byte blob and all 204 64-byte chunks absent from both `DRIVERS.PHS` (445 KB) and `CARS.PHS` (803 KB) | **Excluded** as a plain subset of sibling recovery slices |
| Reed-Solomon slice-window probe | 816 aligned 16-byte windows of PHYSICS.PHS absent from the 384,000-byte `RecvSlic` payload (exponent 53) in `CARS.PHS`; length is 3.4% of slice size | **Excluded** as a partial/embedded slice of the sibling set |
| 256-byte window entropy scan | every aligned 256-byte window (51 total) has entropy 7.08-7.31 — uniform, no low-entropy plaintext header (the earlier 0x3200 "7.12" was typical, not special) | **No plaintext header region** |
| XOR against sibling `RecvSlic` payloads at all alignments 0..2000 | no `PAR2\0PKT` magic appears in any XOR result; best entropy only 7.938/7.939 vs 7.986 baseline (negligible reduction) | **Excluded** as a simple XOR of sibling recovery data |
| PAR2 slice-exponent probe | sibling `RecvSlic` bodies start with a small u32 exponent (53/58/59) then 384,000 bytes of slice data; PHYSICS.PHS starts with u32 1,615,901,797 | **Excluded** as a bare PAR2 recovery slice (no plausible exponent) |

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
- **FileDesc metadata**: PAR2 FileDesc body layout is fileid(16)/hash16k(16)/hashfull(16)/length(u64)/filename; `GTL_Update_0901.exe` length is 294,316,896 bytes (767 slices of 384,000; final slice 172,896). PHYSICS.PHS (13,064 bytes) is not a simple fraction of that file or of a slice.
- **Arbitrary-offset window test**: scanned all 7 recovery slices at 64-byte steps for a 13,064-byte window matching PHYSICS.PHS (sampling every 16th byte): best 12/816 matches — chance level. It is not a window of any slice.
- **Recovery-slice exponent test**: the 7 `RecvSlic` bodies carry 4-byte PAR2 exponents; PHYSICS.PHS's
  leading u32 (0x6050b465) matches none of them, so it is not a bare recovery-slice body from that set.
- **Uniqueness**: sha256 over all 2,510 loose files and all archive members in `GTLSteam` finds PHYSICS.PHS only at its original `Physics2.gtl` member — no duplicate or embedded copy elsewhere.
- **Single-byte XOR scan**: all 256 keys give 0.387-0.393 printable fraction on the first 4 KB — random data, not obfuscated text.
- **Distribution comparison**: PHYSICS.PHS byte entropy 7.986 (chi2 0.993 vs uniform) is statistically
  indistinguishable from the RecvSlic recovery-slice bodies (7.984-7.985, chi2 1.04-1.11), supporting a
  parity/recovery-data classification without proving exact slice identity.
- **Interpretation**: the UI source-MAS loader likely opens these archives looking for
  UI/localization assets and finds none relevant; the PHS members are not dispatched
  to any physics consumer by name. Strong evidence PHS data is **unused by GTL
  gameplay** — consistent with leftover update/recovery artifacts bundled in the
  install. This is a resource-identification result, not a decoded consumer routine.

## GTL.exe reverse-engineering pass (2026-11-26)

At the user's suggestion, the executable itself was examined directly:

| Check | Result |
|---|---|
| `strings` (ASCII) in `GTL.exe`, `GTLDedicated.exe`, `GTLConfig.exe`, `GTLReporter.exe`, all DLLs for `.phs`, `PHYSICS.PHS`, `Physics2.gtl`, `CARS.PHS`, etc. | **Zero hits**; only `gtlui.mnu` / `SOURCE_MAS` appear in both main executables |
| UTF-16LE `strings -el` for `phs` | Zero hits |
| Packer detection (`file`, rabin2, UPX strings) | Unpacked, unstripped PE32 i386 — earlier string searches were not hidden by packing |
| Raw byte search for `53 48 50` (little-endian "PHS") with radare2 | 9 hits, all false positives: data inside strings like `CATEGORYFINISHPOINTS` or instruction-boundary coincidences such as `8b 53 48` (`mov edx,[ebx+0x48]`) followed by `50` (`push eax`). Prior `50 53 48` ("PSH") hits were likewise shader strings |
| Search for a 3-byte extension compare (`PH` word + `S` byte) in `.text` | Zero hits |
| `PhysicsInfoChunkProcessor1` string neighborhood | It belongs to model/node physics-chunk parsing ("ScaleMax", "phoneme sets", "Physics object type = %d"), **not** a `.phs` file reader |
| `Source_MAS="Physics2.gtl"` in `UIData/gtlui.mnu` lines 22–27 | The archive is opened as a generic UI MAS source (`Could Not Load MAS file %s (line %d)`, `SOURCE_MAS` strings), not via any PHS-named consumer |

Conclusion: reverse engineering confirms there is no PHS-specific file loader or extension dispatch in the GTL binaries. The PHS members are reached, if at all, through the generic MAS/UI loader; no operation on `PHYSICS.PHS` can be identified statically, and the earlier offline blocker stands.

## User-requested "open the encryption" campaign (2026-11-25)

Fresh attempts beyond every earlier negative, all ending in documented failure:

| Attempt | Result |
|---|---|
| Web search for the exact MD5/SHA256, the 13,064-byte size, `PHYSICS.PHS`, SimBin PHS format | No public spec or matching artifact; search results are unrelated domains (Port-Hamiltonian systems, crystallography, other games' ragdoll `.phs` files) |
| Repeating-XOR / add / subtract with every sibling PAR2 identifier (3 set IDs, file ID, hash16k, packet hash, the blob's own first 8 bytes) | Best printability 0.394 vs 0.384 baseline; entropy unchanged; no `PAR2\0PKT` |
| Known-plaintext: force the first 8 bytes to `PAR2\0PKT`, derive the 8-byte key, apply it everywhere and at every 8-byte-aligned offset | Header length/set ID/type fields remain random; no hit |
| Bit transforms: reverse bits, nibble swap, byte reverse, whole-stream rotations 1–7 | Best printability 0.392; no structure |
| RC4 with 14 game/file-derived keys; raw JCA Blowfish with all versions/keys | Best 0.392; no known prefix |
| Position-dependent keystreams (`c ^ (i*K)`, `(i>>8)*K`, additive variants, K=0..255) | Best 0.399; no PAR2 magic |
| Hash-manifest hypothesis: MD5/SHA1/SHA256 prefixes of all 28,965 GTL loose files and archive members searched in the blob | Zero matches |
| ZIP/7z/RAR/MSCF central-directory/trailing-index scan | Zero signatures; 0/64 trailing u32 values point inward |

**Genuine blocker**: with no public format spec, no consumer routine, no key material in the corpus, and bytes statistically indistinguishable from uniform PAR2 parity data, the blob cannot be decoded from local evidence alone. It is not demonstrably encrypted physics: four siblings are provably PAR2 update data, and no gameplay consumer references any PHS file. To make further progress one would need `GTL_Update_0901.exe` (the PAR2 target), a complete matching PAR2 slice set, the updater/consumer executable with its key material, or a source-level tool spec. None exist in `../`.

## Recommendation

**Defer further decoding.** The recovery-data hypothesis is structurally validated;
the remaining high-entropy bytes are parity data whose "decoding" would only
reconstruct `GTL_Update_0901.exe`, which is not part of the game's gameplay assets.
`PHYSICS.PHS` needs no action unless a consumer is found. Revisit only if GTL runtime
tracing shows PHS members being read by a named subsystem.
