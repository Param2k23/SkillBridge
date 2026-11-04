# Client capability matrix

As of official-document review 2026-11-03. **No SkillBridge client E2E run exists.**
Verified documentation means only that a vendor documents a feature. It does not
mean compatibility was observed. Client binary versions are not pinned yet.

| Client | Documented transport/auth | Documented retrieval/UX | Native remote Skills | SkillBridge E2E |
| --- | --- | --- | --- | --- |
| Claude Code | HTTP MCP, OAuth | tools/resources, MCP prompt commands | Unestablished / provisional | Untested |
| Codex CLI | Streamable HTTP, bearer/OAuth, mcp login | MCP tools; /mcp status | Unestablished / provisional | Untested |
| Cursor | Streamable HTTP, OAuth | tools, prompts, resources | Unestablished / provisional | Untested |
| SDK generic client | Documented modern and legacy profiles | SkillsClient release API | Beta documented | Untested |

Claude documents `/servername:promptname (MCP)` and legacy prompt command syntax;
this does not establish uniform host slash completion or native Skills support.
Codex local `$skill` invocation does not imply arbitrary remote MCP registration.
No documentation evidence is treated as proof a host feature is unsupported;
mark unsupported only after explicit vendor evidence or a version-pinned test.

Sources: [Claude Code](https://code.claude.com/docs/en/mcp),
[Codex MCP](https://learn.chatgpt.com/docs/extend/mcp?surface=cli),
[Codex Skills](https://learn.chatgpt.com/docs/build-skills),
[Cursor](https://cursor.com/docs/mcp),
[extension matrix](https://modelcontextprotocol.io/extensions/client-matrix).

Promotion to runtime-verified requires client version/OS, server commit, protocol
revision, auth path, sanitized request trace, retrieval+reference integrity,
update behavior, unsupported-extension fallback and cross-tenant negatives.
No external credentials are required or authorized for Phase 0.
