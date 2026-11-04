# ESLint minimatch security override

The Phase 1 network audit reported moderate advisory
[GHSA-g3hv-75wg-m249](https://github.com/isaacs/minimatch/security/advisories/GHSA-g3hv-75wg-m249)
for `eslint > minimatch@10.2.6`. The maintainer identifies pattern amplification
when `optimizationLevel >= 2` and lists `11.0.1` as patched. The
[maintainer release](https://github.com/isaacs/minimatch/releases/tag/v11.0.1)
provides that version.

On 2026-11-04, bounded public npm metadata checks returned ESLint `10.14.0` as
latest, still depending on `minimatch ^10.2.6`. There is therefore no available
ESLint update that removes this finding. An initial direct-edge-only
`eslint>minimatch` override did not clear the real audit: the audit then identified
`eslint > @eslint/config-array > minimatch@10.2.6`, and the installed dependency
tree also retained that version under `@typescript-eslint/typescript-estree`.

The first focused correction pins exactly these three observed consumers to
`11.0.1`: `eslint>minimatch`, `@eslint/config-array>minimatch`, and
`@typescript-eslint/typescript-estree>minimatch`. It does not override unrelated
consumers, change audit severity, mute the advisory, or exclude development
dependencies. Original failed audit and tree evidence must remain available.

The patched package's declared engine range is `18 || 20 || >=22`, which includes
the repository's pinned Node `24.21.0`. This override crosses a dependency major
version, so API inspection and the actual ESLint run are compatibility gates.
The full frozen install, lint, typecheck, tests, build and network audit must pass
before integration; command results belong in the task evidence, not inferred
from this configuration change.

Remove each selector when an available compatible release of its parent declares
a safe minimatch range itself. Regenerate the lockfile and repeat the same checks,
including an actual network `pnpm audit --audit-level=low`. Keep exact direct
dependency pins and the frozen-lockfile requirement. No approved domain schema,
protocol profile or tenant-security policy changes as part of this repair.

R1 validation observed on the repaired lockfile: all three consumers resolve
`minimatch 11.0.1`. ESLint and `@eslint/config-array` use `Minimatch.match`;
`@typescript-eslint/typescript-estree` uses `minimatch()`. Positive/negative
smoke checks passed for both actual API paths. `pnpm why minimatch` contains
no other version. Frozen install, actual ESLint/Prettier, typecheck,
92 tests and emitted build passed. The real network audit exited 0 with zero
advisories and an empty muted list, using the unchanged `--audit-level=low`.
These are local results; independent review and integration remain separate
requirements, and this repair establishes no hosted CI or client compatibility.
