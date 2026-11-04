# Phase 0 evidence

Base `89b2e41a51e70a8eb14400d01f83feaac0c1b0c4`. Local integration branch:
`integration/phase-0`. No remote configured; no PR/hosted CI or protected merge.

Delegation (read-only, shared seed checkout):

- `standards` / research_agent: official current MCP, Skills Beta, OAuth, SDK pins,
  vendor-document capability matrix. No edits or runtime tests. Completed design
  report; coordinator incorporated into research, protocol matrix and ADR 0002.
- `threats` / security_engineer: 12 prioritized risks, read/cache/alias policy,
  test mapping and loopback-only pre-auth boundary. No edits. Observed existing
  graph validation PASS. Incorporated into threat model and ADR 0001.
- `contracts` / registry_engineer: JSON Schema design, stable-only versions,
  path/digest/semantic limits. No edits. Reported 18 regex design assertions PASS;
  this is not acceptance evidence for the final schema.

Coordinator owns all changes. Differences resolved explicitly: JCS manifest
canonicalization chosen over hashing arbitrary publisher JSON serialization;
stable-only SemVer, 1 MiB/file, 8 MiB total, 128 files, unlisted requires grant.
Product runtime validators must enforce the semantic requirements.

Coordinator targeted validation (2026-11-04 UTC / 2026-11-03 America/Phoenix):

- `python3 scripts/validate_phase0.py`: initial run FAIL, 1 failed subcase. The
  generated incomplete-publication fixture shared a mutable object with the later
  complete fixture. Focused repair P0-R1 removed the unintended ref/hash from the
  negative fixture. Rerun: 4 tests OK, 51 recorded schema cases plus semantic
  sample/integrity checks, exit 0. One correction loop used.
- `python3 scripts/validate_task_graph.py`: PASS, 48 tasks, unique IDs, valid
  dependencies, acyclic, exit 0.
- `git diff --check`: exit 0, no output. Final clean-snapshot checks also needed
  because this command alone does not inspect untracked artifacts.
- Runtime: Python 3.14.4, jsonschema 4.19.2, referencing 0.36.2; Node v24.21.0.
  `scripts/requirements-phase0.txt` records the standalone validator dependency.

Independent QA preliminary review: baseline commands pass; current official
MCP/SDK/Skills sources independently confirmed. Focused repair P0-R2:

- VersionRef now enforces the same 32-character version suffix as Version;
  added maximum-length positive and overlong negative cases.
- Organization policy now requires explicit owningOrganizationId plus trusted
  tenant binding in the mandatory semantic rules; added conditional schema cases.
- P2-01 authoritative acceptance now covers modern discover, legacy initialize,
  concurrency and invalid version/header metadata. P4-02 acceptance includes
  missing/mismatched organization binding denial.

Clean snapshot integration validation: `project/evidence/phase-0-validation.log`.
Both Python commands exit 0: 4 unittest methods / 57 recorded schema cases,
48-task DAG. A first whitespace sweep over every seed file reported existing
ROADMAP Markdown hard-break spaces. Final whitespace checking covers changed/new
files; none has diagnostics. Git no-index exit 1 with no diagnostics means a
file differs from /dev/null, not a whitespace failure.

No hosted CI is configured. This is local Phase 0 integration evidence only;
P1 owns reproducible package checks and hosted CI. Final independent QA: PASS
for every P0 task; see `phase-0-review.md`. Coordinator accepted ADRs and closed
P0 in dependency order, then readied only P1-01/P1-02. P1-04 implementation owner
is integration_engineer so its QA reviewer remains independent.
pnpm install/lint/typecheck/test/build: NOT RUN; no package manifest or pnpm
binary exists. These are P1-01 acceptance requirements, not Phase 0 passes.
