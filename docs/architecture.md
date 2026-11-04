# SkillBridge architecture

This is a summary of accepted Phase 0 decisions, not a new contract. The
[ADRs](adr/) and [domain contract](protocol/contracts.md) remain authoritative.

SkillBridge is a headless skill distribution service for existing AI clients.
It distributes approved instructions and reference text; it does not host a
chatbot, LLM inference, arbitrary execution or unauthorized skill mirrors.

Use a strict TypeScript/pnpm modular monolith. One `/mcp` Streamable HTTP endpoint
serves the read path; publishing and permission administration form a logically
separate control plane. PostgreSQL is authoritative for identity, policy and
lifecycle; private S3 stores immutable content; SQS carries retry-safe jobs.
These are target components, not a claim that infrastructure exists.

Every retrieval surface receives server-derived principal/tenant context and
checks policy, including search, prompts, resources, aliases, conditional requests
and caches. Published bytes are immutable, while disabling content or revoking
access must prevent future reads. Unknown authorization policy denies access.
Publisher manifests cannot grant tenant permissions or approve public exposure.

The [JSON Schema bundle](protocol/skillbridge-v1.schema.json) defines domain v1;
mandatory semantic checks add byte integrity, safe paths, text encoding,
frontmatter consistency, rights and lifecycle requirements. Never execute
publisher content. Original local CC0 samples are available for conformance work.

The [protocol ADR](adr/0002-protocol-profiles.md) separates modern and legacy MCP
lifecycles. Native Skills uses an explicit negotiated Beta adapter, while MCP
tools, prompts and resources provide compatibility paths. Native wire objects
must not be conflated with domain manifests. Installed SDK API and client-version
verification remain implementation gates; documentation is not runtime evidence.

The current phase is repository and engineering-harness preparation. Before tenant
security controls are implemented and verified, prototypes serve only synthetic
fixtures on loopback. Cloud deployment, credentials, public publishing and release
remain explicit human approval boundaries.
