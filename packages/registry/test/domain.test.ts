import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { domainDefinitions, validateDomain } from '../src/index.js';

interface ContractCase {
  name: string;
  definition: (typeof domainDefinitions)[number];
  value: unknown;
  valid: boolean;
}
const fixtureRoot = new URL('../../../docs/fixtures/', import.meta.url);
const cases = JSON.parse(
  readFileSync(new URL('contract-cases.json', fixtureRoot), 'utf8'),
) as ContractCase[];
const schema = JSON.parse(
  readFileSync(
    new URL(
      '../../../docs/protocol/skillbridge-v1.schema.json',
      import.meta.url,
    ),
    'utf8',
  ),
) as { $defs: Record<string, unknown> };

describe('approved domain schemas', () => {
  it('binds every named definition to the unmodified approved bundle', () => {
    expect([...domainDefinitions].sort()).toEqual(
      Object.keys(schema.$defs).sort(),
    );
    expect(cases).toHaveLength(57);
  });
  it.each(cases)('$name', ({ definition, value, valid }) => {
    expect(validateDomain(definition, value).valid).toBe(valid);
  });
  it('does not coerce values, add defaults or remove unknown properties', () => {
    const input = { items: [], total: 42 };
    expect(validateDomain('SearchResult', input).valid).toBe(false);
    expect(input).toEqual({ items: [], total: 42 });
    expect(validateDomain('Version', 1).valid).toBe(false);
  });
  it('does not put rejected values or property names in diagnostics', () => {
    const secret = 'synthetic-do-not-log';
    const result = validateDomain('ErrorResponse', {
      code: secret,
      token: secret,
    });
    expect(result.valid).toBe(false);
    expect(JSON.stringify(result)).not.toContain(secret);
    expect(JSON.stringify(result)).not.toContain('token');
  });
});
