# SkillBridge domain contract v1

Validate a named `$defs` entry from `skillbridge-v1.schema.json`, with JSON Schema
2020-12 and date-time format checking enabled. The root is a definition library.
It is not an ingestion validator. No remote schema resolution is necessary.

Required semantic controls for runtime implementations:

- Slug components each have at most 63 characters. VersionRef components must
  match manifest skillId/version; tenant ownership comes from trusted service
  metadata. Reject invisible/control characters in human-readable metadata.
- File paths are unique, lexicographically sorted, with no case-fold collisions,
  Windows device names (CON, PRN, AUX, NUL, COM1–9, LPT1–9), links or special files.
  Root `SKILL.md` occurs exactly once. Do not URL-decode paths into filesystem paths.
- `.md` maps to `text/markdown`, `.txt` to `text/plain`, `.json` to
  `application/json`. Validate UTF-8, no NUL, JSON parsing for JSON files, exact byte
  length, per-file maximum 1 MiB, at most 128 files and total at most 8 MiB.
- `SKILL.md` must have valid Agent Skills frontmatter, with name matching the
  final skill slug, description matching manifest description, and no silent
  frontmatter rewriting. Native extension adapters preserve all frontmatter.
- Verify SHA-256 over exact stored file bytes. `manifestSha256` covers RFC 8785
  canonical JSON of the manifest only. Never include the digest in its own input.
- A nonempty license string is not proof of permission. Validate SPDX expression
  or approved license reference and inspect provenance/rights before publishing.
  No automatic import/fetch is authorized by a provenance source string.
- Alias target must belong to the same tenant/skill and refer to a published,
  enabled version. Update using compare-and-swap revision with audit evidence.
- Grant subject/membership, policy epoch and publicApprovalId must be resolved
  from trusted control-plane records. A syntactically valid caller-supplied
  approval ID does not approve publication. Unknown policy denies.
- Organization visibility requires `owningOrganizationId`. Verify that this
  organization belongs to the policy tenant and the principal has active
  membership in that organization or an explicit authorized read grant. The
  tenant/organization binding is mandatory for both access paths. A personal tenant cannot use organization
  visibility unless an explicit trusted organization binding exists. Missing or
  mismatched organization/tenant bindings deny; tenantId alone is not membership.
- Atomic publication: quarantine → validating → published or rejected/failed.
  Retries are bounded and tenant-idempotent; failed/rejected jobs are terminal.
  A retry is a new job. Duplicate exact bytes may succeed idempotently; different
  bytes at an existing reference conflict. No partial version becomes visible.
- Search authorizes before ranking/pagination. Bind opaque authenticated cursors
  to principal, tenant, query, order and policy epoch; stale/replayed cursors fail
  closed. Never expose unauthorized counts or existence through errors.
- Immutable storage bytes do not imply permanent access. Recheck policy at reads,
  conditional responses and cache hits, including resource URIs and resolved aliases.

Phase 0's validator exercises schemas, sample bytes and representative semantic
checks. It is engineering evidence, not production security implementation.
Tenant enforcement, archive scanning, full JCS vectors, frontmatter parsing,
transaction races and native wire adaptation remain required implementation tests.

P1 promotes the two valid original samples plus a synthetic adversarial sample
into executable conformance fixtures. The invalid cases here include traversal,
unknown tenant metadata, malformed digest, duplicate root and incomplete publish.
