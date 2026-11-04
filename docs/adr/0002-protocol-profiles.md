# ADR 0002: Versioned MCP and optional native Skills

Status: accepted by coordinator after independent Phase 0 QA PASS (2026-11-03). Source review: 2026-11-03.

Primary MCP profile: `2026-07-28`, with POST `/mcp`, per-request metadata and
`server/discover`. No protocol session or GET event stream in this profile.
Maintain an explicit `2025-11-25` compatibility profile for older clients using
initialize and its version-specific lifecycle. Never mix the two lifecycles.
Reject unsupported revisions explicitly and validate Origin/version metadata.

Prospective SDK pins, verified in official release notes but NOT installed:
`@modelcontextprotocol/server`, `client`, `core`, optional `server-legacy`:
`2.4.0`; `@modelcontextprotocol/node`: `2.1.2`. P1 must verify registry availability,
Node compatibility and actual imports in smoke tests before committing the lock.
If a pin fails verification, create a repair/ADR update, not an invented API.

Native Skills is the released **Beta** extension `io.modelcontextprotocol/skills`,
SEP-2640 Final. Offer it only when negotiated; implement its own `skills/list`,
`skills/get`, `resources/read`, complete frontmatter, file URI/size/digest manifest
and required cache fields using a tested adapter. Directory reading and experimental
SDK `attach` are excluded initially. The domain manifest is not its wire schema.

Tools `search_skills`, `get_skill`, `read_skill_file`, `list_my_skills`, MCP prompts
and resources remain compatibility surfaces. Host slash command/autocomplete and
local `$skill` UX are distinct from remote native Skills discovery. No host is
runtime-verified yet. Do not advertise universal native support or slash commands.

OAuth uses protected-resource metadata, configured issuer discovery and exact
audience/resource checks; no token passthrough. Current profile prefers CIMD;
deprecated DCR is optional legacy compatibility. Select issuer and revocation SLA
before shared exposure, not during local synthetic-fixture prototyping.

Official sources and limitations: [standards research](../research/standards.md).
If Beta wire contracts change, pin a reviewed extension commit and golden wire
fixtures before P2-02; do not follow a moving branch silently.
