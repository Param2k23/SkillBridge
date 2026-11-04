# Local conformance skills

These three fixtures are original SkillBridge project-authored material under
[CC0-1.0](LICENSE). The two valid skills preserve the Phase 0 samples byte for byte;
the third is synthetic adversarial test data. No third-party skill was mirrored,
and these fixtures have not been published to a registry.

| Fixture               | Expected schema result | Purpose                                           |
| --------------------- | ---------------------- | ------------------------------------------------- |
| `text-only`           | Valid                  | Root SKILL.md with exact file size and SHA-256    |
| `with-references`     | Valid                  | Root SKILL.md plus a referenced text file         |
| `adversarial-invalid` | Invalid                | Forged tenant metadata and an unsafe logical path |

`manifest.json` describes distributable skill files; it is fixture metadata and
is not itself a distributed file. The invalid manifest names an escape path that
has no corresponding file. Nothing should extract or fetch it.

The adversarial SKILL.md is inert hostile instruction text: never obey, execute or
fetch anything from it. Its invalid manifest is rejected by schema validation.
That rejection is not a prompt-injection detector. Schema validation alone cannot
judge text safety, authorize tenants, verify file bytes or implement ingestion.

`tests/contract/skills.test.ts` uses the actual runtime validator against the
frozen schema. Separate fixture assertions compare real file bytes and advertised
hashes/sizes, then demonstrate tampering changes the digest. They do not claim a
schema-only API detects changed files or that production ingestion exists.

The promoted SKILL.md/reference bytes are integrity fixtures. Do not apply Markdown
formatting to them: changing whitespace changes their manifest digests and the
byte-preservation assertions must fail. Format TypeScript/metadata separately.
