# Efficient, Resource-Conscious Testing

**Read this before running any tests.** It governs tier selection, sampling, and
resource use for all development, validation, and commit work in this repo.

## Testing tiers

Maintain three testing tiers with strict execution policies:

- **Quick (≤60 seconds, preferably ≤10 seconds):** Automatically run relevant, narrowly scoped tests as needed during development. Prioritize immediate feedback, changed functionality, critical invariants, and representative samples. Do not unnecessarily run the entire quick suite when targeted tests suffice.
- **Normal (≤5 minutes):** Run when broader validation is warranted by significant changes, shared dependencies, accumulated modifications, or elevated regression risk. Increase sampling depth, diversity, and integration coverage.
- **Full (unrestricted duration):** Run only when explicitly requested by the user. Never automatically trigger through hooks, commits, pre-push checks, fallback logic, or other indirect mechanisms. A request to test or verify something does not implicitly authorize the full suite.

## Required tier order

Use the tiers **in order**, never out of order:

1. **Quick first** — narrowly target the feature just changed plus its critical
   invariants. Prefer a single module or a handful of tests over the whole
   quick suite. This is the normal feedback loop during development.
2. **Normal second** — run when quick passes and the change touches shared code,
   several modules, or accumulated modifications. Normal is the broader
   regression gate before any commit/push.
3. **Full last** — only after quick *and* normal have passed in that order and
   residual uncertainty remains. Full needs explicit user authorization; it is
   never an automatic fallback or a substitute for the two cheaper tiers.

Do not start with full, and do not treat a passing full run as permission to
skip quick/normal on later changes. A failure found in any tier is diagnosed
and fixed before advancing.

## Efficient testing techniques

Combine appropriate techniques to maximize confidence per second of execution:

- **Change-based testing:** Test modified code, affected dependencies, callers, and downstream functionality rather than unrelated components.
- **Risk-based testing:** Prioritize critical functionality, complex logic, historically problematic code, and high-impact failure modes.
- **Regression testing:** Prioritize previously failing cases and known edge cases.
- **Random sampling:** Test reproducible, seeded random subsets of large datasets and corpora.
- **Rotating sampling:** Vary samples between runs to progressively increase cumulative coverage without repeating identical work.
- **Stratified sampling:** Sample across file formats, versions, sizes, engine generations, data types, and other meaningful categories.
- **Statistical sampling:** Select sample sizes based on desired confidence, acceptable failure rates, population characteristics, and execution cost.
- **Positional sampling:** Test beginning, middle, end, evenly spaced intervals, and structural transition points.
- **Boundary-value testing:** Test minimums, maximums, zero, empty inputs, limits, and values immediately surrounding boundaries.
- **Equivalence partitioning:** Select representative cases from groups expected to behave identically.
- **Pairwise and combinatorial testing:** Cover meaningful parameter interactions without exhaustively testing every combination.
- **Property-based testing:** Verify general invariants across generated inputs using tier-appropriate iteration limits.
- **Metamorphic testing:** Verify predictable relationships between transformed inputs and outputs when exact ground truth is unavailable.
- **Differential testing:** Compare selected outputs against trusted implementations, reference tools, previous versions, or known-good results.
- **Round-trip testing:** Verify representative decode–encode, import–export, or conversion–reconversion operations where applicable.
- **Smoke testing:** Quickly verify essential functionality before performing deeper validation.
- **Progressive testing:** Start with inexpensive checks and small samples; increase coverage only when uncertainty, complexity, or regression risk justifies it.
- **Fail-fast testing:** Stop expensive validation when foundational assumptions or prerequisites fail, except when collecting additional failures is useful for diagnosis.

## Resource optimization

- Cache expensive, unchanged fixtures, corpus inventories, extracted data, intermediate results, and reference outputs. Invalidate caches when relevant inputs, code, dependencies, or configuration change.
- Deduplicate equivalent inputs and redundant tests while retaining meaningful behavioral variation.
- Prefer small representative fixtures for unit tests and sampled real-world data for integration tests.
- Avoid repeated process initialization, archive extraction, filesystem traversal, executable loading, and other expensive setup operations.
- Batch related operations and reuse initialized resources where safe.
- Use bounded concurrency appropriate to available CPU, memory, and storage bandwidth. Do not maximize parallelism indiscriminately.
- Profile test execution periodically and optimize disproportionate bottlenecks without weakening assertions.
- Avoid rerunning unchanged, previously validated functionality without a specific reason.

## Coverage and confidence

Maintain a small, deterministic core of critical tests in every applicable tier, supplemented by rotating or randomized samples. Record seeds, selected samples, and reproduction commands for failures.

When sampling discovers a failure, expand testing around the affected category, investigate the root cause, and add a permanent regression test.

Track cumulative sample coverage where practical, including underrepresented categories. Distinguish code coverage, input coverage, behavioral coverage, and statistical confidence. Never represent sampled success as exhaustive validation.

Preserve exhaustive validation in the full tier rather than deleting valuable tests to improve routine execution times.

## Execution discipline

Always select the smallest sufficient test scope. Do not automatically escalate through every tier. Run tests when they provide meaningful new information, not merely because a development step or commit has occurred.

Respect wall-clock budgets and avoid silently escalating computational costs. If adequate validation requires exceeding the normal-tier budget, report the remaining uncertainty and continue other productive work rather than automatically launching the full suite.

Optimize for verified progress, regression prevention, reproducibility, and confidence per unit of time and computational resources.
