# Contributing to SkillBridge

Read `AGENTS.md`, `ROADMAP.md`, `tasks.json` and `project/status.md` before changing
anything. The task graph is authoritative; roadmap bullet numbers are descriptive.
Follow the accepted [ADRs](docs/adr/) and [architecture](docs/architecture.md).

Claim only an approved, dependency-ready task. Work in its dedicated branch and
Git worktree with an explicit file list. Do not edit another task's files, root
configuration or frozen contracts without coordinator agreement. The coordinator
owns task states and integration. See the [engineering workflow](docs/runbooks/engineering-workflow.md).

Use the exact Node and pnpm versions committed by the bootstrap task. Do not
install global tooling. From the repository root, after bootstrap:

```bash
pnpm install --frozen-lockfile
pnpm lint
pnpm typecheck
pnpm test
pnpm build
python3 scripts/validate_task_graph.py
python3 -m unittest discover -s scripts -p 'test_validate_task_graph.py' -v
```

These commands must actually run; an absent script is a bootstrap failure, not a
pass. The Phase 0 Python validator additionally needs the dependencies documented
in `scripts/requirements-phase0.txt`; install them only in an approved local
virtual environment if not already available. Record exit codes and sanitized
logs. A local pass does not imply hosted CI, deployment or client compatibility.

Use strict TypeScript, runtime boundary validation, immutable version references
and content hashes. Authorize every tenant read, including search, files, aliases,
errors and cache hits. Never execute remotely published scripts or import skill
content as code. Include meaningful negative tests for changed boundaries.

Before review, inspect the diff and check that only assigned paths changed.
Independent QA must review and reproduce the checks. Failed validation receives a
focused repair task, with at most two correction loops before a blocked report.
Only the coordinator records DONE after integration evidence. A reviewer cannot
approve their own implementation.

No secrets or unlicensed third-party skill content may enter the repository.
Cloud spending/deployment, credentials, IAM expansion, irreversible changes,
public publishing, protected branch merges and releases require explicit human
approval. A task or pull-request checkbox does not grant that authorization.
