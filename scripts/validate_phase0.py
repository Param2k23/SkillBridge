#!/usr/bin/env python3
"""Standalone contract evidence, not the product ingestion/security validator."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
import unittest

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = json.loads((ROOT / 'docs/protocol/skillbridge-v1.schema.json').read_text())


def validate(name, value):
    schema = {**BUNDLE, '$ref': '#/$defs/' + name}
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(value)


def semantic_manifest(manifest, content):
    """Representative byte/path checks; production adds frontmatter/JCS/policy."""
    validate('SkillManifest', manifest)
    if any(len(part) > 63 for part in manifest['skillId'].split('/')):
        raise ValueError('slug length')
    files = manifest['files']
    paths = [f['path'] for f in files]
    if paths != sorted(paths) or len(set(p.casefold() for p in paths)) != len(paths):
        raise ValueError('duplicate, case collision or order')
    if set(content) != set(paths):
        raise ValueError('unlisted or missing content')
    if sum(f['sizeBytes'] for f in files) > 8 * 1024 * 1024:
        raise ValueError('total size')
    for file in files:
        path = file['path']
        for segment in path.split('/'):
            if re.fullmatch(r'(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])', segment.split('.')[0], re.I):
                raise ValueError('reserved device path')
        expected_mime = {'.md': 'text/markdown', '.txt': 'text/plain', '.json': 'application/json'}[Path(path).suffix]
        if file['mediaType'] != expected_mime:
            raise ValueError('MIME mismatch')
        raw = content[path]
        if len(raw) != file['sizeBytes'] or sha256(raw).hexdigest() != file['sha256']:
            raise ValueError('byte integrity')
        if '\0' in raw.decode('utf-8'):
            raise ValueError('NUL content')
        if file['mediaType'] == 'application/json':
            json.loads(raw)


def sample(name):
    base = ROOT / 'docs/fixtures' / name
    paths = sorted(p for p in base.rglob('*') if p.is_file())
    content = {p.relative_to(base).as_posix(): p.read_bytes() for p in paths}
    description = {'text-only': 'Summarize a supplied paragraph using three concise bullets.',
                   'with-references': 'Review a supplied change using the provided checklist.'}[name]
    manifest = dict(schemaVersion='1.0', skillId='skillbridge/' + name, version='1.0.0',
                    name=name, description=description, license='CC0-1.0',
                    provenance=dict(kind='original', source='project-authored', rightsAttested=True),
                    files=[dict(path=p, mediaType='text/markdown', sizeBytes=len(raw),
                                sha256=sha256(raw).hexdigest()) for p, raw in content.items()])
    return manifest, content


class Phase0Contracts(unittest.TestCase):
    def test_meta_schema(self):
        Draft202012Validator.check_schema(BUNDLE)
        for name in BUNDLE['$defs']:
            Draft202012Validator.check_schema({**BUNDLE, '$ref': '#/$defs/' + name})

    def test_recorded_contract_cases(self):
        cases = json.loads((ROOT / 'docs/fixtures/contract-cases.json').read_text())
        for case in cases:
            with self.subTest(case=case['name']):
                if case['valid']:
                    validate(case['definition'], case['value'])
                else:
                    from jsonschema import ValidationError
                    with self.assertRaises(ValidationError):
                        validate(case['definition'], case['value'])
        print(f'Validated {len(cases)} recorded positive/negative schema cases')

    def test_original_samples_and_integrity(self):
        for name in ('text-only', 'with-references'):
            manifest, content = sample(name)
            semantic_manifest(manifest, content)
            tampered = dict(content)
            tampered['SKILL.md'] += b' changed'
            with self.assertRaisesRegex(ValueError, 'byte integrity'):
                semantic_manifest(manifest, tampered)
            unlisted = dict(content, **{'references/unlisted.md': b'unlisted'})
            with self.assertRaisesRegex(ValueError, 'unlisted'):
                semantic_manifest(manifest, unlisted)

    def test_semantic_rejections(self):
        manifest, content = sample('with-references')
        changed = deepcopy(manifest)
        changed['files'][1]['mediaType'] = 'application/json'
        with self.assertRaisesRegex(ValueError, 'MIME'):
            semantic_manifest(changed, content)
        changed = deepcopy(manifest)
        changed['files'].append(deepcopy(changed['files'][1]))
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            semantic_manifest(changed, content)
        changed = deepcopy(manifest)
        changed['files'][1]['path'] = 'references/CON.md'
        renamed = {'SKILL.md': content['SKILL.md'], 'references/CON.md': content['references/checklist.md']}
        with self.assertRaisesRegex(ValueError, 'reserved'):
            semantic_manifest(changed, renamed)
        changed = deepcopy(manifest)
        changed['files'][1]['sizeBytes'] += 1
        with self.assertRaisesRegex(ValueError, 'integrity'):
            semantic_manifest(changed, content)


if __name__ == '__main__':
    unittest.main(verbosity=2)
