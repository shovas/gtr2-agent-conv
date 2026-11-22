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

## Recommendation

**Defer further decoding.** The recovery-data hypothesis is structurally validated;
the remaining high-entropy bytes are parity data whose "decoding" would only
reconstruct `GTL_Update_0901.exe`, which is not part of the game's gameplay assets.
`PHYSICS.PHS` needs no action unless a consumer is found. Revisit only if GTL runtime
tracing shows PHS members being read by a named subsystem.
