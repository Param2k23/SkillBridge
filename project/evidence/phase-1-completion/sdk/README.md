# Isolated MCP SDK preflight

ADR0002's P1 engine/import obligation is verified without product dependencies or
Phase2 implementation. Exact server/client/core/server-legacy2.4.0 and node2.1.2
installed in a private scratch package; root manifest/lock unchanged. Engine-strict
Node24.21.0 and8ESM imports pass; p1_exit_qa independently reran the smoke exit0.
No server/listener/clientconnection is constructed. This is not wire/E2E proof.

Reproduce in a fresh temporary directory: copy package.json, pnpm-lock.yaml,
pnpm-workspace.yaml, .npmrc and sdk-import-smoke.mjs from this folder; use the
pinned local Corepack pnpm10.34.9, install --frozen-lockfile, then node
sdk-import-smoke.mjs. The script resolves dependencies next to itself, so copy it
into that temporary package rather than invoking it from this evidence directory.

Initial probe incorrectly assumed SUPPORTED_PROTOCOL_VERSIONS catalogued modern
versions. It is legacy negotiation only; initial failure/script are preserved.
Installed code separately declares2026-07-28 for the modern per-request handler.
Corrected probe verifies actual public handler/adapter/Skills exports, installed
revision marker/hash, legacy2025-11-25 compatibility metadata and exact versions.
Do not use the legacy constant to configure modern protocol dispatch.

Optional server-legacy is deprecated frozen v1SSE/OAuth migration code. Do not add
it by default for2025 StreamableHTTP fallback; the main handler supports the two
profiles. Phase2 must inspect installed types and test actual wire behavior,
Origin/Host guards, content types and context/auth boundaries before claims.
No Phase0 contract was changed and no Phase2 product code was written.
