import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

// Import-only dependency verification. No server is constructed or connected.
const root = dirname(fileURLToPath(import.meta.url));
const pins = {server:'2.4.0', client:'2.4.0', core:'2.4.0', node:'2.1.2', 'server-legacy':'2.4.0'};
const packages = [];
const modules = {};
assert.equal(process.versions.node, '24.21.0');
for (const [name, version] of Object.entries(pins)) {
  const metadata = JSON.parse(readFileSync(join(root, 'node_modules', '@modelcontextprotocol', name, 'package.json'), 'utf8'));
  assert.equal(metadata.version, version);
  assert.equal(metadata.engines.node, '>=20');
  const loaded = await import(`@modelcontextprotocol/${name}`);
  assert.ok(Object.keys(loaded).length > 0);
  modules[name] = loaded;
  packages.push({name: metadata.name, version, nodeEngine: metadata.engines.node});
}
for (const [name, symbol] of [['server','McpServer'],['client','Client'],['node','NodeStreamableHTTPServerTransport'],['server-legacy','SSEServerTransport']]) {
  assert.equal(typeof modules[name][symbol], 'function', `${name}:${symbol}`);
}
assert.equal(typeof modules.core.ClientRequestSchema.safeParse, 'function');
assert.ok(modules.server.SUPPORTED_PROTOCOL_VERSIONS.includes('2026-07-28'));
assert.ok(modules.server.SUPPORTED_PROTOCOL_VERSIONS.includes('2025-11-25'));
const skills = {};
for (const name of ['server','client','core']) {
  skills[name] = await import(`@modelcontextprotocol/${name}/ext/skills`);
  assert.equal(skills[name].SKILLS_EXTENSION_ID, 'io.modelcontextprotocol/skills');
}
assert.equal(typeof skills.server.SkillsExtension, 'function');
assert.equal(typeof skills.server.SkillCatalog, 'function');
assert.equal(typeof skills.client.SkillsClient, 'function');
assert.equal(typeof skills.core.SkillSchema.safeParse, 'function');
console.log(JSON.stringify({status:'PASS', node:process.versions.node, packages, imports:8,
  profiles:['2026-07-28','2025-11-25'], extension:'io.modelcontextprotocol/skills',
  scope:'ESM imports and installed export/engine compatibility only; no endpoint, auth, wire or client E2E test',
  optionalLegacyWarning:'server-legacy is deprecated v1 SSE/OAuth migration code; not needed by default for legacy Streamable HTTP profile'}, null, 2));
