import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { validateDomain } from '../../packages/registry/src/index.js';

const fixtureRoot = new URL('../../examples/skills/', import.meta.url);
const validFixtures = ['text-only', 'with-references'] as const;

function record(value: unknown): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new TypeError('Fixture must be an object');
  }
  return value as Record<string, unknown>;
}

function manifest(name: string): Record<string, unknown> {
  const value: unknown = JSON.parse(
    readFileSync(new URL(`${name}/manifest.json`, fixtureRoot), 'utf8'),
  );
  return record(value);
}

function files(value: Record<string, unknown>): Record<string, unknown>[] {
  if (!Array.isArray(value.files)) throw new TypeError('Missing fixture files');
  return value.files.map((file: unknown) => record(file));
}

function rootFile(value: Record<string, unknown>): Record<string, unknown> {
  const file = files(value).find((entry) => entry.path === 'SKILL.md');
  if (!file) throw new TypeError('Missing SKILL.md fixture');
  return file;
}

function sha256(bytes: Uint8Array): string {
  return createHash('sha256').update(bytes).digest('hex');
}

describe('original CC0 skill conformance fixtures', () => {
  it.each(validFixtures)(
    '%s passes the actual frozen manifest schema',
    (name) => {
      const value = manifest(name);
      expect(validateDomain('SkillManifest', value).valid).toBe(true);
      expect(value.license).toBe('CC0-1.0');
      expect(record(value.provenance).kind).toBe('original');
      expect(record(value.provenance).rightsAttested).toBe(true);
    },
  );

  it.each(validFixtures)(
    '%s preserves all original Phase 0 file bytes',
    (name) => {
      for (const file of files(manifest(name))) {
        if (typeof file.path !== 'string')
          throw new TypeError('Invalid fixture path');
        const bytes = readFileSync(
          new URL(`${name}/${file.path}`, fixtureRoot),
        );
        const original = readFileSync(
          new URL(`../../docs/fixtures/${name}/${file.path}`, import.meta.url),
        );
        expect(bytes.equals(original)).toBe(true);
      }
    },
  );

  it.each(validFixtures)(
    '%s advertises exact byte sizes and digests',
    (name) => {
      for (const file of files(manifest(name))) {
        if (typeof file.path !== 'string')
          throw new TypeError('Invalid fixture path');
        const bytes = readFileSync(
          new URL(`${name}/${file.path}`, fixtureRoot),
        );
        expect(bytes.byteLength).toBe(file.sizeBytes);
        expect(sha256(bytes)).toBe(file.sha256);
      }
    },
  );

  it('exercises the declared reference as a real fixture file', () => {
    const value = manifest('with-references');
    const instruction = readFileSync(
      new URL('with-references/SKILL.md', fixtureRoot),
      'utf8',
    );
    expect(instruction).toContain('references/checklist.md');
    expect(files(value).map((file) => file.path)).toEqual([
      'SKILL.md',
      'references/checklist.md',
    ]);
    expect(
      readFileSync(
        new URL('with-references/references/checklist.md', fixtureRoot),
        'utf8',
      ),
    ).toContain('Check correctness');
  });

  it('detects tampered fixture bytes by digest comparison, not by schema', () => {
    const value = manifest('text-only');
    const original = readFileSync(new URL('text-only/SKILL.md', fixtureRoot));
    const tampered = Buffer.from(original);
    tampered[0] = tampered[0] === 0 ? 1 : 0;
    expect(tampered.byteLength).toBe(original.byteLength);
    expect(sha256(tampered)).not.toBe(rootFile(value).sha256);
    // This API receives metadata only: it cannot inspect or reject altered bytes.
    expect(validateDomain('SkillManifest', value).valid).toBe(true);
    expect(sha256(original)).toBe(rootFile(value).sha256);
  });
});

describe('adversarial metadata and lifecycle conformance', () => {
  it('rejects the third synthetic fixture without obeying or fetching its content', () => {
    const value = manifest('adversarial-invalid');
    expect(validateDomain('SkillManifest', value).valid).toBe(false);
    expect(value.tenantId).toBe('forged-tenant');
    const unsafeFile = files(value).find((file) => file.path !== 'SKILL.md');
    expect(unsafeFile).toBeDefined();
    expect(validateDomain('SkillFile', unsafeFile).valid).toBe(false);
  });

  it('does not mistake schema acceptance for prompt-injection detection', () => {
    const value = manifest('adversarial-invalid');
    const metadataOnly = { ...value };
    delete metadataOnly.tenantId;
    metadataOnly.files = [rootFile(value)];
    // Hostile instruction text can have valid metadata. Scanning, authorization,
    // client policy and production byte verification are separate future controls.
    expect(validateDomain('SkillManifest', metadataOnly).valid).toBe(true);
  });

  it.each([
    '../SKILL.md',
    '/SKILL.md',
    'references/../../escape.md',
    'references/%2e%2e/escape.md',
    'references\\escape.md',
    'C:/escape.md',
    'references/execute.sh',
    'references/file.md\n',
  ])('rejects unsafe or unsupported logical file path %j', (path) => {
    const file = { ...rootFile(manifest('text-only')), path };
    expect(validateDomain('SkillFile', file).valid).toBe(false);
  });

  it.each([
    ['tenantId', 'forged-tenant'],
    ['visibility', 'public'],
    ['grants', [{ principalId: 'attacker', permission: 'read' }]],
    ['publicApprovalId', 'forged-approval'],
  ])('rejects publisher-supplied service metadata %s', (key, value) => {
    expect(
      validateDomain('SkillManifest', {
        ...manifest('text-only'),
        [key]: value,
      }).valid,
    ).toBe(false);
  });

  it.each(['A'.repeat(64), '0'.repeat(63), 'g'.repeat(64)])(
    'rejects malformed digest %s',
    (sha256) => {
      const file = { ...rootFile(manifest('text-only')), sha256 };
      expect(validateDomain('SkillFile', file).valid).toBe(false);
    },
  );

  it.each([0, -1, 1_048_577])(
    'rejects invalid per-file byte size %i',
    (sizeBytes) => {
      const file = { ...rootFile(manifest('text-only')), sizeBytes };
      expect(validateDomain('SkillFile', file).valid).toBe(false);
    },
  );

  it('requires exactly one root instruction entry', () => {
    const value = manifest('text-only');
    expect(validateDomain('SkillManifest', { ...value, files: [] }).valid).toBe(
      false,
    );
    expect(
      validateDomain('SkillManifest', {
        ...value,
        files: [rootFile(value), rootFile(value)],
      }).valid,
    ).toBe(false);
  });

  it('rejects missing publishing rights attestation', () => {
    const value = manifest('text-only');
    const provenance = { ...record(value.provenance), rightsAttested: false };
    expect(
      validateDomain('SkillManifest', { ...value, provenance }).valid,
    ).toBe(false);
  });

  it('requires a complete successful publishing result', () => {
    const incomplete = {
      jobId: 'fixture-job',
      state: 'published',
      updatedAt: '2026-11-04T00:00:00Z',
    };
    expect(validateDomain('PublishingStatus', incomplete).valid).toBe(false);
    expect(
      validateDomain('PublishingStatus', {
        ...incomplete,
        ref: 'skillbridge/text-only@1.0.0',
        manifestSha256: '0'.repeat(64),
      }).valid,
    ).toBe(true);
  });

  it('rejects prerelease references under the stable-only v1 policy', () => {
    expect(
      validateDomain('VersionRef', 'skillbridge/text-only@1.0.0-beta').valid,
    ).toBe(false);
  });
});
