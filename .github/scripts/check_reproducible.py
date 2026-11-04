#!/usr/bin/env python3
"""Build twice from clean generated-output directories and compare every byte."""
from hashlib import sha256
from pathlib import Path
import shutil
import subprocess

from safe_paths import checked_path


def snapshot(outputs):
    result = {}
    for output in outputs:
        if output.is_symlink():
            raise ValueError('symlink output directory')
        for path in sorted(output.rglob('*')):
            if path.is_symlink():
                raise ValueError('symlink generated artifact')
            if path.is_file():
                result[str(path)] = sha256(path.read_bytes()).hexdigest()
    if not result:
        raise ValueError('build produced no artifacts')
    return result


def assert_identical(first, second):
    if first != second:
        changed = sorted(key for key in first.keys() | second.keys() if first.get(key) != second.get(key))
        raise ValueError('non-reproducible artifacts: ' + ', '.join(changed))


def preflight_outputs(root):
    packages = sorted([*root.glob('packages/*/package.json'), *root.glob('apps/*/package.json')])
    if not packages:
        raise ValueError('no workspace packages')
    outputs = []
    for package in packages:
        checked_path(root, package)
        outputs.append(checked_path(root, package.parent / 'dist', must_exist=False))
    return outputs


def clean_outputs(root, outputs):
    # Validate the complete set before deleting even the first output directory.
    checked = [checked_path(root, output, must_exist=False) for output in outputs]
    for output in checked:
        if output.exists():
            shutil.rmtree(output)


def main():
    root = Path(__file__).resolve().parents[2]
    outputs = preflight_outputs(root)
    builds = []
    for _ in range(2):
        clean_outputs(root, outputs)
        subprocess.run(['corepack', 'pnpm', 'build'], cwd=root, check=True)
        builds.append(snapshot(outputs))
    assert_identical(*builds)
    print(f'PASS: two clean builds have identical {len(builds[0])} artifact hashes')


if __name__ == '__main__':
    main()
