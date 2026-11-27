# Reverse-engineering playbook

Concrete techniques that produced verified decoders in this project, distilled
from the RaceGMT breakthrough (a container-only format became 574 convertible
meshes) and the preceding negative results. Apply these in order when facing a
new binary format or an undecoded field. The full experiment log is
`docs/open-issues-research.md`; verified findings are in
`docs/format-findings.md`.

## 1. Start from near-duplicate assets, not raw statistics

Find two files that are the same asset with a small intentional difference
(a shifted instance, a wet variant, a different LOD). Diff them and look at
where the differing bytes land. In RaceGMT, `PEOPLE_STAND_01` vs `02` put every
difference on a **36-byte grid**, which exposed the record stride after byte
histograms and float plausibility scans had failed. Same-size pairs are even
better: `race_gmt.diff_strides()` grew out of this.

**Apply next:** CUBE MTS 4.10/4.20 meshes, HAT files with the same layout
signature, replay files of the same session.

## 2. Decode counts and ordinals first

In an unknown table, the first fields worth decoding are the ones that *count*
or *order* things. The opening RaceGMT records had a group field and a
sequential ordinal; group counts 8/12/8/14/6 times three matched submesh vertex
counts 24/36/24/42/18 exactly, which is what resolved what the u16 indices
addressed. In HAT, the three header counts unlocked the grid and record table.

**Rule:** if a field is monotonic, small, and repeats per record, test it as an
ordinal or count before treating it as data.

## 3. When you fit a constant, search the file for it

A least-squares fit of RaceGMT's column 0 gave `0.1805*x + 0.9836*y`. Dumping
the bytes immediately after the records showed those exact coefficients stored
on disk as `[cos, 0, sin, 0]` per record, upgrading a 4.5e-4 approximation into
an 8e-6 exact decoder (`read_texture_axes()`). A clean fitted constant usually
means the producer stored it somewhere — go find it.

**Apply next:** GMT `f0` family associations, replay `small_b` and u16 units,
HAT's opaque per-record u32.

## 4. When coverage is low, inspect one failing file and name the assumption

Track a coverage number after every change (RaceGMT went 11 → 34 → 69 → 231 →
574 files). Each jump came from finding a specific over-strict assumption by
opening one failing sample:

- required an opening triangle table — absent in some files;
- required padding to be exactly zero — really ~1e-7 or 0.006;
- required a horizontal axis — it is a **unit normal**, including `(0,1,0)` for
  upward faces;
- required index count == vertex count — they are triangle lists, often 1.5x.

Relax to the *actual* invariant and re-measure. Do not accumulate special cases
for individual files; that produces a decoder that works on the corpus you
happened to inspect and nowhere else.

## 5. Use distribution-preserving controls for every statistical hit

A plain shuffle keeps the multiset and therefore cannot test whether a value
distribution is special. It created a false f0/material signal. Use:

- byte shuffle preserving the histogram (HAT phase test, node-index windows);
- fresh random-u32 baseline (replay packed-u16 "small float" test);
- shuffled column values within each mesh (f0 extra-stream pattern).

Record the control number next to the observed number; a result without a
control is a hypothesis, not a finding.

## 6. Decode only what the target format needs

RaceGMT converted without decoding column 4: positions, UVs, indices and
computed normals were sufficient. Ask which fields the target writer actually
reads, decode those, and leave the rest documented as unassigned. This avoids
spending weeks on a field that does not block conversion.

## 7. Reuse a validated writer

`to_gtr2_gmt()` feeds decoded RaceGMT data into `vrl_to_gmt.build_gmt()` rather
than implementing a new GMT writer. Conversion is usually *decode + adapt + feed
into an existing verified path*, not a from-scratch serializer.

## 8. Preserve the original bytes

Keep the raw blob in `Entry.data` and add decoded views (`Entry.decoded`,
`read_racegmt_submeshes()`). Round-trips stay byte-identical while new
capabilities are layered on top. Never edit a source file in place to "fix" it.

## 9. Lock in each gain with a full-corpus test

Every decoder now has a corpus-wide full-tier test (e.g.
`test_racegmt_corpus_converts_to_gtr2`: 574 decoded == 574 converted). Coverage
assertions make silent regressions visible and force the next investigator to
confront the same invariants.

## 10. Distinguish "must convert" from "can copy"

Before building a converter, measure identity against the target corpus. GTL
25/26 and BMW 26/26 same-name `.gmt` files are byte-identical to GTR2 (copy is
safe), while every shared text config differs. Race07/Volvo meshes are not
identical. A cheap hash comparison can eliminate most conversion work.

## Repeatable loop

1. Pick a source format and a target field the writer needs.
2. Find near-duplicate samples; diff for strides.
3. Decode counts/ordinals and the table layout.
4. Fit suspicious constants, then hunt for them in the file.
5. Measure a coverage number; open one failing sample per plateau.
6. Relax exactly one over-strict assumption; re-measure.
7. Run a distribution-preserving control on any correlation.
8. Feed the decoded data into an existing verified writer.
9. Add a full-corpus regression test and document the verified facts plus the
   remaining unknowns.

## Worked example of steps 5/7 (f0 vs previous mesh size)

Probe: is the mesh-1+ f0 low byte the previous mesh's vertex count minus two?
On 3,002 mesh pairs it matched 32.3% of the time versus 10.4% for a seeded
shuffled control — a real but partial association, **not** a decoder. This is
the form a result should take before anyone claims a rule: observed rate,
control rate, sample count, and an explicit non-claim.
