# Standards research — 2026-11-03

Research agent: read-only official-document review. No package installed or
client/auth session run. These are documentation findings, not runtime evidence.

| Area | Finding | Official source |
| --- | --- | --- |
| MCP | Latest resolves to 2026-07-28 | [Specification](https://modelcontextprotocol.io/specification/2026-07-28) |
| Transport | POST, per-request metadata, server/discover; modern profile removes sessions and GET stream | [Streamable HTTP](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http) |
| SDK | 2.4.0 server/client/core/server-legacy; node adapter 2.1.2, prospective exact pins; verify imports locally in P1 | [Release](https://github.com/modelcontextprotocol/typescript-sdk/releases/tag/v2.4.0) |
| Skills | Released Beta, SEP-2640 Final; `io.modelcontextprotocol/skills` | [Official repository](https://github.com/modelcontextprotocol/ext-skills) |
| Skills wire | skills/list, skills/get, resources/read; complete frontmatter and file manifest, sizes and sha256-prefixed digests; cache fields required | [Beta specification](https://github.com/modelcontextprotocol/ext-skills/blob/main/specification/beta/skills.mdx), [overview](https://modelcontextprotocol.io/extensions/skills/overview) |
| OAuth | Protected resource, issuer and audience binding, CIMD preferred; DCR deprecated compatibility | [Authorization](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization) |

Search snippets for Skills said Stable, while the fetched normative repository
identified Beta. Prefer fetched normative content. These sources are mutable;
P2 must pin the reviewed extension commit plus wire fixtures. SDK APIs in release
notes do not substitute for installed-version import and protocol tests.

The seed roadmap's initialize-centric P2 acceptance is valid for legacy profile
only; modern profile acceptance must include server/discover and independent
concurrent request handling. Both profiles need negative version/header tests.
