# ADR 0001: Headless modular monolith and trust boundaries

Status: accepted by coordinator after independent Phase 0 QA PASS (2026-11-03).

SkillBridge distributes approved instructions and reference files to existing agents.
It does not host inference, execute publisher scripts, mirror third-party libraries,
or provide a chatbot. Client-side execution and use remain subject to host policy.

Use a strict TypeScript pnpm monorepo with a modular monolith. Expose one `/mcp`
Streamable HTTP endpoint; separate control-plane publishing from authorized reads
logically. PostgreSQL is authoritative for identity, policy and lifecycle; private
S3 holds immutable content; SQS carries retry-safe jobs. These are design choices,
not provisioned resources. Local fixtures precede durable adapters.

Every read receives server-derived principal/tenant context, including list,
search, prompts, resources, aliases and cache hits. Resolve authorization before
returning metadata or bytes. Never trust tenant IDs or grants inside skill content.
Public visibility does not authorize publication: public publishing needs human
approval. Unlisted means absent from discovery, not bypassing grants.

Published content is immutable. Service lifecycle policy can disable retrieval
without rewriting content. Resolve aliases to immutable version references and
authorize the resolved version; revocations must take effect on cached reads.
Use generic not-found responses for absent and unauthorized objects.

Initial files are UTF-8 text: root `SKILL.md` plus `.md`, `.txt`, `.json` files
under `references/`. Reject archives with symlinks/hardlinks, unsafe paths,
duplicate normalized paths, invalid encoding, oversized content or secrets.
No remote URL fetching or script delivery in the initial policy.

Original local sample instructions in `docs/fixtures/` are dedicated under CC0-1.0.
They may be reused in P1 fixtures; they are not public registry publications.

Consequences: conservative file/version policy reduces initial compatibility;
extensions require a reviewed schema revision. A local no-auth prototype must
bind to loopback and serve only non-sensitive fixtures. Shared/network deployment
and private content require fail-closed authentication and tenant enforcement.
