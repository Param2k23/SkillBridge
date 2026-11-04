# SkillBridge

SkillBridge is a headless, multi-tenant skill distribution service being built for
existing AI agents over MCP. The current repository contains reviewed domain
contracts and the engineering foundation. It does not yet provide a running MCP
service, hosted deployment, or verified client integration.

Read [AGENTS.md](AGENTS.md), [the roadmap](ROADMAP.md), [tasks.json](tasks.json)
and [current status](project/status.md) before contributing. Task IDs and
prerequisites in `tasks.json` are authoritative.

The foundation uses Node **24.21.0** and pnpm **10.34.9**, pinned in repository
configuration. With the installed Corepack launcher, use `corepack pnpm` in place
of `pnpm`; enabling global shims is unnecessary:

```bash
corepack pnpm install --frozen-lockfile
corepack pnpm lint
corepack pnpm typecheck
corepack pnpm test
corepack pnpm build
python3 scripts/validate_task_graph.py
python3 -m unittest discover -s scripts -p test_validate_task_graph.py -v
```

The standalone Phase 0 Python checks require
[scripts/requirements-phase0.txt](scripts/requirements-phase0.txt). The product
TypeScript tests exercise the same approved JSON Schema cases with the actual
runtime validator. Schema validation does not implement tenant authorization,
content scanning, or the additional semantic ingestion rules.

See [contribution instructions](CONTRIBUTING.md),
[architecture](docs/architecture.md), [accepted ADRs](docs/adr/), and
[engineering workflow](docs/runbooks/engineering-workflow.md). Local checks,
hosted CI, and real-client compatibility have separate evidence requirements.
Cloud spending/deployment, credentials, public publishing, protected branch
merges and releases require explicit human approval.
