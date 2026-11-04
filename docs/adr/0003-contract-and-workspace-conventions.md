# ADR 0003: Contract version 1 and implementation conventions

Status: accepted by coordinator after independent Phase 0 QA PASS (2026-11-03).

`docs/protocol/skillbridge-v1.schema.json` is the single JSON Schema 2020-12
definition bundle. P1 must generate strict TypeScript types or bind runtime schemas
to it with equivalence tests; handwritten drift is not acceptable. All object
boundaries reject unknown fields. Protocol-specific MCP wrappers do not change
these domain definitions. Domain schema version is independent of MCP version.

Canonical skill ID is `publisher/name`; immutable reference is that ID plus
`@major.minor.patch`. Lowercase ASCII slugs have at most 63 characters. Release
versions only in v1: no leading zeroes, prereleases or build metadata. Versions
do not encode tenant ownership. Tenant policy is service metadata, never authority
supplied by a manifest. IDs are opaque external identifiers, not storage paths.

The manifest hash is SHA-256 of RFC 8785 JCS canonical UTF-8 JSON of the manifest
only (no self-digest). Files have SHA-256 of exact stored bytes; file list order
is lexicographic by path. Verify bytes, sizes and manifest hash before publication
and on storage reads. No digest alone implies provenance or authorization.

Semantic invariants in `docs/protocol/contracts.md` are mandatory in addition to
JSON Schema. Phase 0 validates representative contracts, not a production
ingestion pipeline. Native MCP Skills wire schemas are supplied by the pinned
extension; use an explicit adapter, never send this domain manifest as native wire
data without translation and contract tests.

Workspace conventions for P1: Node 24 LTS, exact available patch selected at
bootstrap; exact pnpm 10 version in packageManager; exact direct dependencies,
committed lockfile. SDK release pin comes from ADR 0002. No package exists yet.
Packages: `@skillbridge/{protocol,registry,storage,db,auth,security}`; apps:
`mcp-server`, `worker`, `cli`. ESM, strict TypeScript, noUncheckedIndexedAccess,
explicit boundary validation. Freeze root tool configuration in P1-01 before
parallel writable P1-03/P1-04/P1-05 worktrees.

Errors use stable domain codes without tenant/object existence leakage. MCP
initialization/JSON-RPC failures use protocol errors; authenticated tool execution
failures use tool error results carrying the domain error. Never serialize stack
traces, tokens, raw storage keys or publisher content into logs/errors.
