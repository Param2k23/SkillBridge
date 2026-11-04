"""Containment checks for CI helper paths, before any source read/output cleanup."""
from pathlib import Path


def checked_path(root, path, *, must_exist=True):
    trusted = Path(root).resolve(strict=True)
    candidate = Path(path).absolute()
    try:
        parts = candidate.relative_to(trusted).parts
    except ValueError as exc:
        raise ValueError('path is outside trusted repository') from exc
    current = trusted
    for part in parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('symlink path component')
    resolved = candidate.resolve(strict=must_exist)
    if not resolved.is_relative_to(trusted):
        raise ValueError('resolved path is outside trusted repository')
    return candidate
