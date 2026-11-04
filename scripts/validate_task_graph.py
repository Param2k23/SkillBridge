#!/usr/bin/env python3
"""Validate SkillBridge's task dependency DAG without third-party packages."""
from pathlib import Path
import json, sys
path=Path(__file__).resolve().parents[1]/'tasks.json'
data=json.loads(path.read_text())
tasks=data['tasks']
ids=[t['id'] for t in tasks]
if len(ids)!=len(set(ids)):
    raise SystemExit('Duplicate task ID')
by_id={t['id']:t for t in tasks}
valid_status={'BACKLOG','READY','CLAIMED','RUNNING','REVIEW_PENDING','INTEGRATION_PENDING','INTEGRATED','DONE','REWORK','BLOCKED'}
for t in tasks:
    if not t['id'].startswith(f"P{t['phase']}-"):
        raise SystemExit(f"Phase/ID mismatch {t['id']}")
    if t['status'] not in valid_status:
        raise SystemExit(f"Unknown status {t['id']}: {t['status']}")
    for d in t['depends_on']:
        if d not in by_id:
            raise SystemExit(f"Missing dependency {d} for {t['id']}")
        if by_id[d]['phase'] > t['phase']:
            raise SystemExit(f"Later-phase dependency {d} for {t['id']}")
seen=set(); visiting=set()
def visit(id_):
    if id_ in visiting:
        raise SystemExit(f'Cycle containing {id_}')
    if id_ in seen:return
    visiting.add(id_)
    for d in by_id[id_]['depends_on']:visit(d)
    visiting.remove(id_);seen.add(id_)
for id_ in ids:visit(id_)
print(f'PASS: {len(tasks)} tasks; unique IDs; valid dependencies; DAG is acyclic')
