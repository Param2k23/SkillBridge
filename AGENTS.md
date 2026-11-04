# SkillBridge — Agent Project Instructions

Read `ROADMAP.md`, `tasks.json`, and the current `project/status.md` before doing work.

## Mission
Build a headless, secure, multi-tenant remote Skill distribution service. Existing AI agents connect over MCP and retrieve skills. Do not add a chatbot UI, arbitrary code execution, or unauthorized third-party skill mirrors.

## Coordinator behavior
- Treat `tasks.json` as the dependency DAG. Work one approved phase/wave at a time.
- Delegate bounded independent tasks to subagents; have one independent QA reviewer validate changed code.
- Never let two writable agents edit the same files or workspace concurrently. For independent code changes, use separate Git worktrees with dedicated branches. Subagents in one shared workspace should usually do read-only research/review.
- Freeze interfaces before parallel implementations. Queue blocked work instead of improvising incompatible contracts.
- Request human approval for: cloud spending/deploy, secrets, IAM expansion, irreversible changes, public publishing, external credentials, merges into protected main, and release.
- Subagents may inherit your permissions: do not assume a custom agent's instruction to be read-only is a security boundary.
- Never claim a test passed unless its command actually ran and produced a passing result.
- Each task: inspect -> plan -> implement -> targeted tests -> independent review -> integration CI -> evidence -> state transition.
- Failed validation triggers a focused repair task, up to two attempted correction loops, then a blocked report. Do not bypass security checks to progress.
- Report exact files changed, tests and status. Don't begin the next major phase without confirming the previous exit criteria.

## General code rules
- TypeScript strict, typed schemas at boundaries, explicit error handling, secure defaults, no credentials in source/logs.
- Write contract, unit, integration, security and e2e tests appropriate to scope.
- Prefer modular monolith; avoid microservices until independently justified.
- Do not invent SDK APIs; verify installed versions and documentation.
- Reject unsafe paths/symlinks; use immutable version references and content hashes.
- Tenant authorization applies to list/search/get/file reads and caches, not just writes.
- Never execute untrusted remotely published skill scripts.
- Do not conflate MCP prompts with native Agent Skills or promise universal slash autocomplete.

## Validation commands (after workspace bootstrap)
- `pnpm install --frozen-lockfile`
- `pnpm lint`
- `pnpm typecheck`
- `pnpm test`
- `pnpm build`

If scripts do not exist yet, that is a bootstrap task—not an excuse to report pass.

## Required agent report
TASK / ROLE / BRANCH / COMMIT / DIFF SUMMARY / TESTS WITH OBSERVED OUTPUT / RISKS / REVIEW REQUEST / STATUS.
