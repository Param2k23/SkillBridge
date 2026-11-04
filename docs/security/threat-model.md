# Tenant and skill supply-chain threat model

Design review, not implemented controls. Risk remains open until mapped tests run.

Trust boundaries: untrusted client → credential validation → server-controlled
tenant policy → registry/cache/storage; publisher → quarantine → bounded validation
worker → atomic published registry; distributed instructions → consuming host.
A hash, resource URI, canonical ID or OAuth login never grants access by itself.

Policy: owner/explicit grant for private; active owning-organization membership or
grant for organization visibility. The organization policy must carry an explicit
owningOrganizationId with a trusted binding to its tenant; missing/mismatched
bindings deny, including personal tenants without an organization binding.
Unlisted excludes discovery and requires an
explicit grant/owner for direct reads. Public exposure needs recorded human
approval. Unknown policy denies; disabled versions deny all readers. Authenticate
before lookup. Missing and inaccessible authenticated objects share sanitized
not-found behavior. Auth challenges must not disclose object existence.

Authorize list/search before ranking, pagination and counts. Reauthorize aliases,
prompts, resources, files, ETags/304 and every cache hit. Bind result caches and
cursors to tenant/principal or permission fingerprint, policy epoch, query and
version. Immutable bytes may be cached by hash internally only if all release
paths reauthorize. Protected HTTP responses default to no-store. Membership,
grant and suspension changes advance epochs; token revocation has an issuer-specific
bounded-staleness decision before network exposure. Fail closed on policy outages.

| ID / priority | Abuse case and required control | Required acceptance / owner |
| --- | --- | --- |
| T01 Critical | Cross-tenant IDs, aliases, files, batch/concurrent context mixups; central server-derived policy | A cannot enumerate/read B through every surface, including concurrent warm caches; P4-02/04/05 |
| T02 Critical | OAuth confused deputy, forged/foreign tokens; validate configured issuer, signature, algorithm, audience/resource, expiry/nbf, scopes; no ID tokens/passthrough | Wrong issuer/audience/key/algorithm/time/scope fail closed; P4-01 |
| T03 Critical | Cache access after revocation; reauthorize hits and conditional responses | Warm as member, revoke, retry: no bytes, metadata, 304 or existence disclosure; P4-04 |
| T04 Critical | Traversal/links/ambiguous extraction; allowlisted logical paths, no links/special files or path-based storage keys | ../, encoded, drive/UNC, duplicates/case collisions, symlinks/hardlinks reject without escape; P3-02/P4-03 |
| T05 Critical | Publisher scripts/active content; UTF-8 text allowlist, never execute/import/render/install | No worker subprocess or outbound fetch driven by content; script upload rejected; P4-03 |
| T06 High | Prompt injection/exfiltration in valid text; provenance, warnings, approval, takedown | Retrieval preserves untrusted designation; hostile fixture cannot trigger server execution/fetch; P1-04/P4-03/P7 |
| T07 High | Digest substitution/partial publish/races; immutable hashes and atomic lifecycle | Corruption, conflicting duplicates, retries and concurrent alias changes expose no partial content; P3-02/03/04/06 |
| T08 High | Unauthorized mirrors/fabricated provenance; rights attestation plus reviewed license | Missing rights/license rejected; original fixture rights recorded; P1-04/P3-03 |
| T09 High | SSRF in imports/OAuth metadata; no arbitrary imports, trusted issuer config and redirect/destination checks | Loopback/link-local/private metadata/redirect/DNS rebinding cannot access internal targets; P4-01/03 |
| T10 High | Bombs/huge files/recursive references/noisy tenants; bounded bytes/files/decompression/jobs/concurrency | Declared limits reject within resource budget, no automatic recursive fetch; P4-03/05/P6 load gate |
| T11 High | Secrets/PII in skills/logs/errors; quarantine secret scan, redacted structured telemetry | Synthetic secrets block publication and never appear in logs, headers or errors; P4-03/05 |
| T12 High | ACL escalation/replayed jobs/public publish; separate control-plane permissions, tenant idempotency, publication recheck | Reader cannot publish/grant; cross-tenant replay denied; publisher metadata cannot approve public exposure; P3-03/P4-02 |

Residual risk: prompt injection cannot be eliminated by scanning. Attestations
record claims rather than proving legal rights. Never market scanned instructions
as safe for unrestricted client execution. Security policy/tenant context must be
designed in P2/P3; P4 provides production enforcement evidence. Until then P2 is
loopback-only synthetic content, with no private/shared service exposure.

Official grounding: [MCP authorization](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization)
and [legacy security guidance](https://modelcontextprotocol.io/docs/2025-11-25/tutorials/security/security_best_practices).
These controls are SkillBridge decisions, not guarantees supplied by MCP.
