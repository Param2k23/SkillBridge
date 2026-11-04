# SkillBridge — Multi-Agent Engineering Implementation Plan

**Status:** implementation plan, not an existing deployment  
**Revision:** 2026-11-03  
**Owner:** human product owner; execution: Codex coordinator and specialist agents  
**Target:** production-capable multi-tenant, headless AI Skill registry and remote distribution platform.

## 0. Product contract and immutable principles

**Product:** A developer configures one MCP connection in their existing agent application and remotely discovers and retrieves approved Agent Skills. SkillBridge is **not** a new chatbot, standalone agent, or general remote code execution platform.

**Supported surfaces:** Streamable HTTP MCP, native Skills extension where clients implement it, MCP tools/prompts/resources for compatibility, eventually optional minimal client adapters. `/skill` invocation and autocomplete are host-client behaviors; do not claim uniform support. Test each client explicitly.

**Boundaries:** SkillBridge hosts and distributes instructions, metadata, and reference files. The consuming AI agent decides whether and how to use them, subject to client capabilities and authorization. Running arbitrary publisher-provided code is out of scope for initial public release.

**Quality rules:** multi-tenant isolation from the beginning; versioned and immutable publishes; content integrity; provenance and licensing; failure recovery; observable operations; least privilege; CI-proven behavior; no unverified user-facing claims. Provide graceful behavior for unavailable client features.

**Architecture:** TypeScript monorepo (pnpm), modular monolith serving MCP over stateless Streamable HTTP, PostgreSQL + S3, SQS background workers, ECS/Fargate on AWS, IaC (Terraform), OIDC/OAuth-compatible protected MCP resources. Separate *control plane* (publish/permissions) from *read path* (authorized skill retrieval) logically, even if initially sharing deployment.

**Early excluded scope:** chatbot UI, hosted LLM inference, arbitrary third-party script execution, one-click enterprise SSO, complex AI-based recommender, paid marketplace, multi-region active-active.

## 1. Team topology and task ownership

| Role | Primary responsibility | Owned boundaries |
|---|---|---|
| Coordinator / Architect | own DAG, freeze contracts, delegate, monitor, review, integrate and report | `docs/`, `project/`, ADRs; may coordinate code changes but should avoid parallel edits |
| Protocol Engineer | MCP server, capability negotiation, native Skills + tools/prompts/resources | `apps/mcp-server/`, `packages/protocol/` |
| Registry Engineer | schema, immutable skill versions, publish/read, manifest integrity | `packages/registry/`, `packages/storage/`, `packages/db/` |
| Security Engineer | OAuth, authorization, policy, threats and ingestion validation | `packages/auth/`, `packages/security/`, security tests |
| Platform Engineer | containers, IaC, CI, deploy, monitoring and recovery | `infra/`, `deploy/`, `.github/workflows/` |
| QA / Reviewer | independent integration tests, adversarial tests, evidence and regressions | `tests/`, review reports; read-only review by default |
| Integration Engineer | real-client compatibility, examples, version negotiation, CLI UX | `integrations/`, `examples/`, compatibility tests |
| Research Agent | verify current standards and vendor APIs, capture versioned decisions | `docs/research/` only |

**Default active concurrency on Plus:** coordinator + 2 implementation agents + 1 read-only reviewer/researcher. Increase only after measuring allowance, conflicts and throughput. Subagents in one session may share files; assign simultaneous **writes only to separate worktrees or disjoint directories with explicit locks**. Separate Codex worktree chats are a straightforward editing workflow.

**Human-only approvals:** spending or creating cloud resources, billing changes, production deploys, broad IAM or secret changes, domain/DNS, repo visibility, public publishing, deleting data, and merging to protected `main`. Tests and human signoff remain required; agent review is not an authorization substitute.

## 2. Task state and orchestration rules

All work lives in `tasks.json` or equivalent issue tracker. A task contains ID, owner, scope, dependencies, touched paths, artifacts, acceptance checks, risk level, and evidence links.

State machine:

```
BACKLOG -> READY -> CLAIMED -> RUNNING -> REVIEW_PENDING
  -> (PASS) INTEGRATION_PENDING -> INTEGRATED -> DONE
  -> (FAIL) REWORK -> RUNNING
  -> (BLOCKED) BLOCKED -> READY
```

Only the coordinator marks a task `READY` after dependency verification. No agent can mark its own work `DONE`. The independent QA role performs validation and the coordinator checks integration evidence. A deterministic CI result is the source of truth for build/test pass, not an agent summary.

Recommended orchestration loop:
1. Read `ROADMAP.md`, `AGENTS.md`, `tasks.json`, current Git state, and CI summary.
2. Select unblocked tasks based on dependency DAG, ownership and concurrency limit.
3. Give each worker a **bounded task packet** (goal, allowed files, non-goals, contracts, tests, acceptance, branch/worktree).
4. Worker implements + runs local focused checks, then reports commit SHA, diff summary, checks run, and risks.
5. QA independently checks changes, runs integration/security/contract tests and returns PASS/FAIL with evidence.
6. On FAIL, create targeted rework task; retry a maximum of 2 automated loops before escalating.
7. On PASS, integrate through reviewed PR, run complete CI in clean environment; only then mark DONE.
8. Select next unblocked wave; checkpoint status in durable repository files after each integrated batch.

If any action requires approval unavailable in noninteractive mode, stop and report `BLOCKED`; never bypass approvals. Never share credentials in prompts, commits, or logs. Do not silently skip tests.

## 3. Execution phases and waves

### PHASE 0 — Discovery, decisions, and contracts (single coordinator + parallel read-only research)
**Objective:** make the product testable on paper before coding.

- P0-01 Architecture decision records: headless product, trust boundary, single endpoint, compatibility strategy, chosen technology and scope.
- P0-02 Verify 2026 MCP transport, Skills extension, prompts, tools, resources, OAuth and Codex/Claude/Cursor behaviors against **official current docs**; pin protocol/SDK versions in ADR.
- P0-03 Write JSON schemas for: canonical skill ID, `SkillManifest`, `SkillVersion`, `SkillFile`, search result, error response and publishing status.
- P0-04 Tenant security threat model and risk inventory: malicious SKILL.md, exfiltration, OAuth confusion, traversal, cross-tenant access, cache leaks, provenance, licenses.
- P0-05 Client capability matrix distinguishing verified, provisional, not supported and untested.

**Parallel:** research, threat modeling, schema exploration. **Sequenced:** coordinator freezes public interfaces.  
**Exit gate:** architecture and schemas approved, representative sample skills legally usable, all P1 tasks defined, no unresolved product-blocking ambiguity.

### PHASE 1 — Repository and agent engineering harness
**Objective:** create an agent-friendly repo with deterministic checks before product features.

- P1-01 pnpm workspace, strict TypeScript, typecheck, ESLint, Prettier, Vitest, build/test scripts, version pinning, lockfile.
- P1-02 Project `AGENTS.md`, specialist TOML roles, task DAG, issue template, PR template, contribution guide, decision log, architecture docs.
- P1-03 GitHub Actions checks: install, lint, typecheck, unit tests, secret scan, dependency audit, reproducible build.
- P1-04 Docker development stack: PostgreSQL, local S3-compatible storage or test mocks, optional SQS emulator. Cross-platform WSL/Windows commands.
- P1-05 Conformance test fixtures: 3 permitted example skills (text-only, references, invalid/adversarial).

**Parallel:** CI, repo scaffold, test fixtures once package conventions are frozen.  
**Exit gate:** clean clone boots locally, CI green, no credentials in repo, test fixtures validated, worktrees can be created safely.

### PHASE 2 — End-to-end remote MCP vertical slice
**Objective:** demonstrate one-time connection -> remote skill retrieval -> agent uses instructions.

- P2-01 Stateless Streamable HTTP MCP endpoint, proper request lifecycle and meaningful error messages.
- P2-02 Native Skills extension discovery/retrieval, file manifest and `resources/read`; verify actual SDK methods instead of guessing.
- P2-03 Compatibility tools (`search_skills`, `get_skill`, `read_skill_file`, `list_my_skills`) with stable schemas.
- P2-04 MCP prompts (`prompts/list`, `prompts/get`) and explicit behavior for slash command host support; do not assume all clients render commands.
- P2-05 Integration and protocol conformance tests against a real MCP client, including unsupported extension fallback.

**Parallel:** native Skills and fallback tools on frozen registry interface; QA contract tests independently.  
**Exit gate:** one client retrieves remotely stored `SKILL.md` and references; no per-skill installation; tests distinguish native prompts from client-side invocation. No user-facing assertions beyond verified clients.

### PHASE 3 — Durable, multi-tenant registry and publishing
**Objective:** move beyond in-memory fixtures to immutable, reproducible content delivery.

- P3-01 PostgreSQL schema + migrations: organizations, principals, memberships, publishers, skills, versions, files, aliases, grants, audit events, ingestion jobs.
- P3-02 Content-addressed S3 object keys, checksums and manifest validation; private bucket. Structured file limits and safe path normalization.
- P3-03 Publish job pipeline (SQS + worker): receive upload/import, quarantine, validate, license/provenance, security scan, index, atomic state transition to published.
- P3-04 Versioned reads, alias resolution (`stable` / pinned), deprecate/disable/rollback, ETag/cache rules. No mutation of published file contents.
- P3-05 Publisher CLI commands: validate, package, publish, versions, deprecate; public publishing requires human approval.
- P3-06 Consistency/failure tests for duplicate publishes, worker retries, partial upload, digest mismatch, failed alias update.

**Parallel:** schema/storage, publisher CLI contract, retry test design. **Sequenced:** publishing after schema and storage contracts are stable.  
**Exit gate:** publish -> discover -> retrieve -> verify -> rollback works across process restarts; retry/idempotency tests green.

### PHASE 4 — Authentication, authorization and supply-chain security
**Objective:** make private and organization-scoped skills genuinely private.

- P4-01 OAuth/OIDC discovery and token validation: issuer, audience, expiry, scopes, resource indicators, revocation strategy as supported.
- P4-02 Authorization policy: public/unlisted/org/private, principals, organizations, grants, minimum privilege, tenant scoping.
- P4-03 Enforce authorization consistently on list, search, get, files, aliases, errors and cache hits.
- P4-04 Harden publisher input: traversal, symlinks, oversized archives, recursive references, malicious scripts, prompt injection warnings, secret scanning, provenance and licensing.
- P4-05 Audit actions, privacy-safe logs, quotas/rate limits, malicious-client tests, threat-model review.

**Parallel:** identity implementation and ingestion scanners with explicit shared policy interface.  
**Exit gate:** cross-tenant retrieval tests and unauthorized enumeration tests fail closed; OAuth negative cases and scanner failure cases covered; independent security review completed.

### PHASE 5 — Discovery, indexing and skill lifecycle policy
**Objective:** high-quality fast discovery without overloading model context.

- P5-01 Exact canonical-name and alias search; PostgreSQL FTS with safe tenant/visibility filtering.
- P5-02 Query pagination, sort/rank, metadata filters, publisher reputation **with evidence**, compatibility filtering.
- P5-03 Optional semantic indexing behind a feature flag after a labeled retrieval benchmark exists; pgvector if useful.
- P5-04 Reference resolution and skill selection: explicit skill name always wins over recommendations; version pin/allowlist policy.
- P5-05 Search evaluation suite: Recall@5, MRR, unauthorized-result rate, latency; protect against search poisoning.

**Exit gate:** task benchmark results recorded, no unauthorized search results, direct-name resolution deterministic, baseline latency measured.

### PHASE 6 — AWS infrastructure, environments, CI/CD
**Objective:** secure, repeatable deployment under AWS credits.

- P6-01 Terraform modules for networking, ECS/Fargate, ECR, RDS PostgreSQL, S3, SQS/DLQ, IAM, Secrets Manager/KMS, logging/alarms. Begin with staging; validate costs before deploy.
- P6-02 OCI container, health/readiness checks, stateless service startup, graceful shutdown, retry-safe workers.
- P6-03 GitHub Actions -> AWS via short-lived OIDC credentials; migration and deployment sequencing, staged rollouts/rollback.
- P6-04 Backups/restores, RPO/RTO targets, runbooks, abuse handling, budget alerts, secret rotation exercise.
- P6-05 Load testing; monitor p50/p95/p99, errors, queue depth, database load, tenant failures and cache hit rates.

**Parallel:** infra IaC, production readiness/runbooks, load harness. **Human approval required before any AWS resource creation or costs.**  
**Exit gate:** staging deployment from a clean checkout, recoverability demonstrated, restore verified, no publicly exposed database/bucket, rollback rehearsed.

### PHASE 7 — Verified client compatibility and beta quality
**Objective:** real people can connect once and use the service from supported agents.

- P7-01 Claude Code E2E: MCP connect, auth, prompt command behavior, skill fetch, update behavior, negative cases.
- P7-02 Codex CLI E2E: MCP connect, tool discovery, native extension availability, fallback invocation, skill use, update behavior.
- P7-03 Cursor E2E: MCP connect, supported discovery paths, host slash/autocomplete behavior; label unsupported cases clearly.
- P7-04 Host-independent client compatibility fixtures; test error handling and progressive enhancement.
- P7-05 Beta onboarding via README, copyable connection snippets, support/runbook docs, privacy and acceptable use notices.
- P7-06 Security/performance regression and final release-candidate checklist.

**Parallel:** client tests and onboarding docs after staging exists.  
**Exit gate:** at least two independently verified client paths (including one native Skills or prompt experience if supported); client matrix updated with measured results, not assumed behavior; private beta approved by human.

### PHASE 8 — Public launch readiness, organization governance
**Objective:** make the platform sustainable for real developer teams.

- P8-01 Org administration through CLI/API; enterprise approval and version policy; automated compliance/audit export.
- P8-02 Integrity status, provenance badges backed by evidence, abuse reports, suspend/disable, takedown procedure.
- P8-03 SLOs and incident playbooks; load/chaos tests, failure injection, vulnerability reporting and secret rotation.
- P8-04 Usage metering, quota enforcement, data retention/privacy policy, documentation and API contract version policy.
- P8-05 Pricing/billing decisions only after validated cost and usage; optional paid tier behind feature flag.

**Exit gate:** reviewed public-use policies, incident response, abuse process, security signoff, adequate capacity and costs approved.

### PHASE 9 — Differentiation (post-validation; don't block initial public beta)
- Verified GitHub source sync and release verification.
- Trusted skill bundles with conflict detection and context budget management.
- Recommendation engine built on measurable downstream task outcomes.
- Organization-wide skill rollout policies and approvals.
- Optional thin IDE/client adapters where standards don't provide `/`, `@`, `#` autocomplete.
- Independently designed sandboxed execution service only if justified, behind separate trust and pricing model.

## 4. Engineering quality gates and non-negotiable tests

### Required per PR
- [ ] Follows frozen interfaces/ADRs; touched paths match assigned ownership.
- [ ] Targeted tests reproduced in CI; command, exit status, and log evidence recorded.
- [ ] `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build` run in a clean integration branch (once configured).
- [ ] New domain behavior has positive and negative tests.
- [ ] No secrets, wildcard IAM, unlicensed third-party content, or unsafe `eval`/shell execution.
- [ ] No silent widening of permissions or public interface breaking changes.
- [ ] Reviewer independent of author; no self-approval.
- [ ] Documentation and task state updated with commit/PR and results.

### Security probes
- Cross-tenant ID and alias enumeration; auth bypass on nested references; wrong-audience token.
- `../` and encoded traversal; links/symlinks; Unicode canonicalization; giant files; decompression bombs.
- Prompt-injection samples, hidden instructions, outbound exfiltration suggestions, malicious scripts.
- Cache keys include tenant/principal authorization context or bypass cache for protected resources.
- Source license provenance and immutability/digest changes.

### Correctness and reliability probes
- MCP initialization / protocol negotiation; stateless concurrent requests and tool errors.
- Idempotent job retries, partial upload rollback, duplicate name collision, rename/version handling.
- S3 outage and DB outage behavior, bad digest, stale cache, stopped worker, DLQ reconciliation.
- Private skill update and revoked grant reflected correctly.
- Client compatibility verified by actual clients, not mock-only.

### Initial service objectives (targets; benchmark before promising)
- p95 cached small-skill retrieval < 300 ms inside selected AWS region.
- p95 normal search < 500 ms with chosen index size.
- 99.9% monthly availability **target**, not claim, after HA hardening.
- 100% integrity verification at publish and on retrieval of files when requested.
- Zero known critical authorization findings at beta launch.

## 5. Repository conventions

```
skillbridge/
  AGENTS.md
  docs/{architecture,adr,protocol,security,runbooks,research}/
  project/{tasks.json,decisions.md,status.md}
  apps/{mcp-server,worker,cli}/
  packages/{protocol,core,db,registry,storage,auth,security,search,observability}/
  integrations/{claude-code,codex,cursor,generic-mcp}/
  examples/skills/
  tests/{contract,integration,security,load,e2e}/
  infra/terraform/{modules,environments}/
  .codex/{config.toml,agents/*.toml}/
  .github/workflows/
```

Treat the included files in this starter pack as a **seed**. On PR #1, incorporate them into the real repository, adapt paths and tests to existing code if any, and keep a single source of truth rather than copying conflicting task lists.

## 6. Agent execution packet (required input and output)

### Input
```
TASK: P2-03
OWNER: protocol-engineer
BASE: latest passing integration commit
WORKTREE: ../skillbridge-p2-03
SCOPE: packages/protocol/** and specific allowed tests
GOAL: Add fallback MCP tools consistent with frozen skill schemas
DEPENDENCIES: P0-03, P1-01, P2-01
NON-GOALS: OAuth, S3, UI, unapproved schema changes
ACCEPTANCE: contract tests + real MCP call demo
APPROVALS: local code edits allowed, cloud changes not allowed
```

### Required output
```
status: REVIEW_PENDING | BLOCKED
branch_or_worktree: ...
commit: ...
changed_files: ...
acceptance_met: ...
tests: command -> observed result (or NOT_RUN + why)
risks: ...
proposed_followups: ...
```

## 7. Integration pattern for parallel workers

**Preferred when workers write code:** one Git worktree and branch per worker task, e.g. `feature/p2-03-mcp-fallback`. Merge sequentially into `integration/phase-2` only after independent QA. In Codex app, use separate Worktree chats. In CLI, manually create worktrees or use supported `codex exec --worktree` for independent tasks. Do not assume subagent spawning automatically creates a separate checkout.

**Preferred when workers inspect/review:** spawn Codex subagents directly and give them read-only tasks in the shared checkout. They can run concurrently without modification conflicts.

**Automatic task manager progression:** Codex's main agent can handle one bounded task wave and report next steps. For reliable unattended polling, retries and PR queue management, add a deterministic external scheduler (e.g. GitHub Actions + issues or the Symphony pattern). ChatGPT Plus alone is not an unlimited or guaranteed continuous agent daemon. The API route would have separate billing.

## 8. Suggested 4-wave opening sequence

**Wave A / contracts (P0):** Research Agent examines latest MCP SDK/protocol; Security Agent drafts threat model; Coordinator freezes schema and client truth table. No code mutation.

**Wave B / foundation (P1):** Platform Agent sets up repo/CI; QA sets up fixtures and checks. Integrate and get green build.

**Wave C / core (P2 and P3 contracts):** Protocol Agent implements MCP server in own worktree; Registry Agent develops immutable file manifest/registry service behind frozen interfaces in another worktree; QA writes independent conformance tests. Integrate only after both pass.

**Wave D / hardening:** Security Agent adds auth/ACL and publisher scanners after read/publish contracts; Platform Agent develops AWS IaC in separate worktree (do not deploy until approval); Integration Agent performs real-client tests.

## 9. What the human should inspect every wave

1. Is the feature actually present, or just a mock?
2. Did tests execute, or are we being shown expected output?
3. Did the agents change public contracts or widen permissions?
4. Is the scope small enough to review and roll back?
5. Does client behavior match the advertised one-time integration experience?
6. Are spending/deployment/public publishing actions awaiting explicit approval?

**Success for the first major milestone:** connect an unmodified supported AI client to the MCP endpoint; invoke an available remote skill through a verified host-supported mechanism; return and apply correct instructions/reference files; update the server-side skill and see the new approved version without a per-skill local install.
