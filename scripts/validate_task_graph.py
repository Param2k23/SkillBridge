#!/usr/bin/env python3
"""Validate the task DAG and evidence references without third-party packages.

This validates a snapshot, not historical transitions or the truth of test logs.
Only the coordinator may authorize state changes after independent review.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any

VALID_STATUSES = {
    'BACKLOG', 'READY', 'CLAIMED', 'RUNNING', 'REVIEW_PENDING',
    'INTEGRATION_PENDING', 'INTEGRATED', 'DONE', 'REWORK', 'BLOCKED',
}
DEPENDENCY_GATED = VALID_STATUSES - {'BACKLOG', 'BLOCKED'}
VALID_OWNERS = {
    'coordinator', 'platform_engineer', 'protocol_engineer', 'registry_engineer',
    'security_engineer', 'qa_reviewer', 'integration_engineer', 'research_agent',
}
REQUIRED_FIELDS = {
    'id', 'phase', 'owner', 'depends_on', 'title', 'acceptance', 'owned_paths',
    'status', 'evidence',
}


class GraphValidationError(ValueError):
    """The task snapshot violates a graph, ownership or evidence requirement."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise GraphValidationError(message)


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _logical_path(value: Any) -> bool:
    if not _nonempty_string(value):
        return False
    return (
        not value.startswith('/')
        and '\\' not in value
        and ':' not in value
        and not any(ord(char) < 32 for char in value)
        and all(part not in {'', '.', '..'} for part in value.rstrip('/').split('/'))
    )


def _evidence_file(root: Path, value: str) -> bool:
    """Evidence must stay in the repo and cannot follow any symlink component."""
    relative = PurePosixPath(value)
    target = root
    for part in relative.parts:
        target = target / part
        if target.is_symlink():
            return False
    return target.is_file() and target.resolve().is_relative_to(root)


def validate_graph(data: Any, root: Path) -> list[dict[str, Any]]:
    """Return validated tasks, raising GraphValidationError on the first issue."""
    root = root.resolve()
    _require(isinstance(data, dict), 'Task document must be an object')
    _require(data.get('schema_version') == '1.0', 'Unsupported schema_version')
    _require(_nonempty_string(data.get('project')), 'Missing project name')
    tasks = data.get('tasks')
    _require(isinstance(tasks, list) and bool(tasks), 'tasks must be a nonempty array')
    by_id: dict[str, dict[str, Any]] = {}
    for task in tasks:
        _require(isinstance(task, dict), 'Each task must be an object')
        missing = REQUIRED_FIELDS - task.keys()
        _require(not missing, f'Missing task fields: {sorted(missing)}')
        task_id = task['id']
        _require(isinstance(task_id, str) and re.fullmatch(r'P[0-9]+-[0-9]{2}', task_id) is not None,
                 f'Invalid task ID: {task_id!r}')
        _require(task_id not in by_id, f'Duplicate task ID: {task_id}')
        phase = task['phase']
        _require(type(phase) is int and phase >= 0, f'Invalid phase: {task_id}')
        _require(task_id.startswith(f'P{phase}-'), f'Phase/ID mismatch: {task_id}')
        _require(isinstance(task['owner'], str) and task['owner'] in VALID_OWNERS,
                 f'Unknown owner: {task_id}')
        _require(isinstance(task['status'], str) and task['status'] in VALID_STATUSES,
                 f'Unknown status: {task_id}')
        for field in ('title', 'acceptance'):
            _require(_nonempty_string(task[field]), f'Empty {field}: {task_id}')
        for field in ('depends_on', 'owned_paths', 'evidence'):
            values = task[field]
            _require(isinstance(values, list) and all(_nonempty_string(v) for v in values),
                     f'{field} must be a string array: {task_id}')
            _require(len(values) == len(set(values)), f'Duplicate {field} entry: {task_id}')
        _require(bool(task['owned_paths']), f'No owned paths: {task_id}')
        _require(all(_logical_path(p) for p in task['owned_paths']), f'Unsafe owned path: {task_id}')
        _require(all(_logical_path(p) for p in task['evidence']), f'Unsafe evidence path: {task_id}')
        if 'risk_level' in task:
            _require(task['risk_level'] in ('low', 'medium', 'high', 'critical'),
                     f'Unknown risk_level: {task_id}')
        if task['status'] == 'DONE':
            _require(bool(task['evidence']), f'DONE task lacks evidence: {task_id}')
            for evidence in task['evidence']:
                _require(_evidence_file(root, evidence),
                         f'Missing, unsafe or non-file evidence for {task_id}: {evidence}')
        by_id[task_id] = task

    for task in tasks:
        for dependency in task['depends_on']:
            _require(dependency in by_id, f'Missing dependency {dependency} for {task["id"]}')
            _require(by_id[dependency]['phase'] <= task['phase'],
                     f'Later-phase dependency {dependency} for {task["id"]}')

    # Iterative DFS handles long valid DAGs without Python recursion-limit failures.
    colors = {task_id: 0 for task_id in by_id}
    for task_id in by_id:
        stack = [(task_id, False)]
        while stack:
            node, leaving = stack.pop()
            if leaving:
                colors[node] = 2
                continue
            _require(colors[node] != 1, f'Cycle containing {node}')
            if colors[node] == 2:
                continue
            colors[node] = 1
            stack.append((node, True))
            stack.extend((dep, False) for dep in reversed(by_id[node]['depends_on']))

    for task in tasks:
        if task['status'] in DEPENDENCY_GATED:
            for dependency in task['depends_on']:
                _require(by_id[dependency]['status'] == 'DONE',
                         f'{task["status"]} task {task["id"]} has incomplete dependency {dependency}')
    return tasks


def ready_candidates(tasks: list[dict[str, Any]]) -> list[str]:
    """List eligible backlog tasks; never mutate states or authorize execution."""
    by_id = {task['id']: task for task in tasks}
    return [task['id'] for task in tasks if task['status'] == 'BACKLOG'
            and all(by_id[dependency]['status'] == 'DONE' for dependency in task['depends_on'])]


def _unique_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        _require(key not in result, f'Duplicate JSON key: {key}')
        result[key] = value
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    default_root = Path(__file__).resolve().parents[1]
    parser.add_argument('path', nargs='?', type=Path, default=default_root / 'tasks.json')
    parser.add_argument('--root', type=Path, help='Evidence root (default: task document directory)')
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.path.read_text(encoding='utf-8'), object_pairs_hook=_unique_keys)
        tasks = validate_graph(data, args.root or args.path.resolve().parent)
    except (OSError, UnicodeError, json.JSONDecodeError, GraphValidationError) as error:
        print(f'FAIL: {error}', file=sys.stderr)
        return 1
    print(f'PASS: {len(tasks)} tasks; unique IDs; valid dependencies; DAG is acyclic; states and DONE evidence valid')
    candidates = ready_candidates(tasks)
    print('Eligible BACKLOG tasks (coordinator approval required): ' + (', '.join(candidates) or 'none'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
