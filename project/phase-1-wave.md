# First implementation wave (prepared, not started)

Scope: P1 only. Phase 0 gate must pass before these packets become READY.
No cloud deployment, credentials, public publishing or protected branch merge.

## First three unblocked assignments after the Phase 0 gate

1. **P1-01 / platform engineer** — dedicated `feature/p1-01-bootstrap`
   worktree from the reviewed integration snapshot. Own root package/lock/tool
   config, `apps/`, `packages/`; no service features. Pin Node/pnpm/dependencies,
   strict ESM TypeScript, lint/typecheck/test/build scripts. Include a meaningful
   domain contract test and frozen-lockfile install. Acceptance: all five required
   pnpm commands actually pass in a clean worktree with logs. Freeze root scripts
   and test conventions before dependent writers start.
2. **P1-02 / coordinator** — branch `feature/p1-02-harness`, separate worktree
   if concurrent with P1-01. Own templates, contribution/runbook docs, DAG validator
   and project evidence. Validate task states/dependencies and repair workflow;
   no package or application edits. Acceptance: DAG negative cases and review
   practice documented and tested. Final integration evidence depends on P1-01.
3. **P1-QA-PLAN / independent QA** — read-only preparation of the P1 clean-checkout
   verification and negative-test plan, including worktree/ownership and acceptance
   checks. This is an operational preparation assignment, not a new implementation
   dependency. P1 has only two dependency-ready implementation tasks; do not label
   a third P1 task unblocked.

## Following bootstrap milestone (queued)

- P1-03 platform: `.github/workflows/` only, isolated worktree. Install/lint/
  typecheck/test/build, secret scan, audit; actual hosted CI needs a configured
  remote. Report local checks separately from hosted CI.
- P1-04 fixture implementer (integration engineer): `examples/skills/`,
  `tests/contract/` only, isolated worktree; promote the original CC0 samples and
  exercise valid and adversarial paths against actual runtime validators.
  A separate QA reviewer must review this work (avoid self-review).
- P1-05 platform: `deploy/`, `docs/runbooks/local-development.md`, isolated
  worktree; local PostgreSQL/S3 mocks and smoke tests; no AWS credentials.

The DAG deliberately gates these three on P1-01. Create worktrees only when
assigning writable tasks. Integrate sequentially on an unprotected integration
branch after independent review; preserve each worker commit. Up to two focused
repair loops per failed validation, then report BLOCKED.
