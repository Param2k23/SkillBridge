#!/usr/bin/env python3
"""Fail closed on known credential formats in Git-indexed and untracked sources.

This bounded high-confidence scanner is a baseline, not proof that content has no
secrets. Findings report locations/rule identifiers, never matched values.
"""
from pathlib import Path
import re
import subprocess
import sys

from safe_paths import checked_path

MAX_BYTES = 10 * 1024 * 1024
PATTERNS = {
    'aws-access-key': re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'github-token': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{36,255}|github_pat_[A-Za-z0-9_]{22,255})\b'),
    'private-key': re.compile(r'-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----'),
    'bearer-token': re.compile(r'(?i)\bauthorization\s*[:=]\s*[\"\x27]?Bearer\s+[A-Za-z0-9_.~+/=-]{20,}'),
    'assigned-secret': re.compile(r'''(?i)\b(?:aws_secret_access_key|client_secret|api_key|access_token)\s*["']?\s*[:=]\s*["']?[A-Za-z0-9_+/=-]{24,}(?=["'\s,}\]]|$)'''),
}


def findings(text):
    return [(rule, text.count('\n', 0, match.start()) + 1)
            for rule, pattern in PATTERNS.items() for match in pattern.finditer(text)]


def scan_file(path, root):
    path = checked_path(root, path)
    if path.stat().st_size > MAX_BYTES:
        raise ValueError('source exceeds secret-scan size limit')
    return findings(path.read_bytes().decode('utf-8', errors='replace'))


def main():
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'],
                            cwd=root, check=True, capture_output=True)
    paths = sorted(set(result.stdout.decode().split('\0')) - {''})
    failures = 0
    for name in paths:
        path = root / name
        try:
            matches = scan_file(path, root)
            for rule, line in matches:
                print(f'{name}:{line}: {rule}', file=sys.stderr)
            failures += len(matches)
        except (OSError, ValueError):
            print(f'{name}: unable to scan source safely', file=sys.stderr)
            failures += 1
    if failures:
        print(f'FAIL: secret scan has {failures} findings/errors', file=sys.stderr)
        return 1
    print(f'PASS: secret scan inspected {len(paths)} source files')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
