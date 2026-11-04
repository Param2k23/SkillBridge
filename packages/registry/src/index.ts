import { readFileSync } from 'node:fs';
import { Ajv2020 } from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';
import type { AnySchema, ValidateFunction } from 'ajv';

// This list is checked against the approved schema in tests. The schema remains
// authoritative; these names do not assert handwritten domain object types.
export const domainDefinitions = [
  'CanonicalSkillId',
  'Version',
  'VersionRef',
  'Digest',
  'Identifier',
  'Timestamp',
  'SkillFile',
  'Provenance',
  'SkillManifest',
  'SkillVersion',
  'SkillSummary',
  'SearchResult',
  'ErrorResponse',
  'PublishingStatus',
  'Alias',
  'Grant',
  'AccessPolicy',
] as const;
export type DomainDefinition = (typeof domainDefinitions)[number];
export type ValidationResult =
  | { readonly valid: true; readonly value: unknown }
  | {
      readonly valid: false;
      readonly issues: readonly { readonly keyword: string }[];
    };

const schema: unknown = JSON.parse(
  readFileSync(
    new URL(
      '../../../docs/protocol/skillbridge-v1.schema.json',
      import.meta.url,
    ),
    'utf8',
  ),
);
// Frozen schemas use conditional required/type contexts; these two strict-mode
// lint restrictions do not alter JSON Schema validation semantics.
const ajv = new Ajv2020({
  strict: true,
  strictRequired: false,
  strictTypes: false,
  allErrors: false,
  coerceTypes: false,
  useDefaults: false,
  removeAdditional: false,
});
addFormats.default(ajv);
ajv.addSchema(schema as AnySchema);
const validators = new Map<DomainDefinition, ValidateFunction>();
for (const definition of domainDefinitions) {
  validators.set(
    definition,
    ajv.compile({
      $ref: `https://skillbridge.invalid/schemas/v1#/$defs/${definition}`,
    }),
  );
}

/** Schema validation only: callers must also enforce contracts.md semantic rules.
 * This never authorizes a principal or certifies content safe for execution.
 */
export function validateDomain(
  definition: DomainDefinition,
  value: unknown,
): ValidationResult {
  const validator = validators.get(definition);
  if (!validator) throw new TypeError('Unknown domain definition');
  if (validator(value)) return { valid: true, value };
  return {
    valid: false,
    issues: (validator.errors ?? []).map(({ keyword }) => ({ keyword })),
  };
}
