#!/usr/bin/env python3
"""Positive and adversarial task-DAG tests; uses only the Python standard library."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from validate_task_graph import GraphValidationError, ready_candidates, validate_graph

SCRIPT = Path(__file__).with_name('validate_task_graph.py')


def task(task_id='P0-01', **changes):
    value = dict(id=task_id, phase=int(task_id.split('-')[0][1:]), owner='coordinator',
                 depends_on=[], title='Test task', acceptance='Observed acceptance',
                 owned_paths=['docs/'], status='BACKLOG', evidence=[])
    value.update(changes)
    return value


def graph(*tasks):
    return dict(schema_version='1.0', project='SkillBridge', tasks=list(tasks))


class TaskGraphTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='skillbridge-dag-test-')
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / 'evidence.log').write_text('observed test output\n')

    def invalid(self, data, message):
        with self.assertRaisesRegex(GraphValidationError, message):
            validate_graph(data, self.root)

    def test_valid_graph_and_ready_candidates(self):
        data = graph(task(status='DONE', evidence=['evidence.log']),
                     task('P1-01', depends_on=['P0-01']),
                     task('P1-02', depends_on=['P1-01']))
        tasks = validate_graph(data, self.root)
        self.assertEqual(ready_candidates(tasks), ['P1-01'])
        self.assertEqual(data['tasks'][1]['status'], 'BACKLOG')

    def test_valid_current_repository(self):
        root = SCRIPT.resolve().parents[1]
        tasks = validate_graph(json.loads((root / 'tasks.json').read_text()), root)
        self.assertGreater(len(tasks), 0)

    def test_duplicate_id(self):
        self.invalid(graph(task(), task()), 'Duplicate task ID')

    def test_missing_dependency(self):
        self.invalid(graph(task(depends_on=['P0-99'])), 'Missing dependency')

    def test_self_cycle(self):
        self.invalid(graph(task(depends_on=['P0-01'])), 'Cycle')

    def test_multi_node_cycle(self):
        self.invalid(graph(task(depends_on=['P0-02']), task('P0-02', depends_on=['P0-01'])), 'Cycle')

    def test_shared_dependency_is_not_cycle(self):
        validate_graph(graph(task(), task('P0-02', depends_on=['P0-01']),
                             task('P0-03', depends_on=['P0-01', 'P0-02'])), self.root)

    def test_later_phase_dependency(self):
        self.invalid(graph(task(depends_on=['P1-01']), task('P1-01')), 'Later-phase dependency')

    def test_phase_id_mismatch(self):
        self.invalid(graph(task(phase=1)), 'Phase/ID mismatch')

    def test_boolean_phase_rejected(self):
        self.invalid(graph(task(phase=False)), 'Invalid phase')

    def test_unknown_state(self):
        self.invalid(graph(task(status='SUCCESS')), 'Unknown status')

    def test_unknown_owner(self):
        self.invalid(graph(task(owner='anyone')), 'Unknown owner')

    def test_required_fields(self):
        for field in ('title', 'acceptance', 'owned_paths', 'owner', 'evidence'):
            with self.subTest(field=field):
                value = task()
                del value[field]
                self.invalid(graph(value), 'Missing task fields')

    def test_empty_ownership(self):
        self.invalid(graph(task(owned_paths=[])), 'No owned paths')

    def test_unsafe_ownership(self):
        for value in ('../elsewhere', '/etc/passwd', 'C:/secrets', 'docs\\file', 'docs//file'):
            with self.subTest(path=value):
                self.invalid(graph(task(owned_paths=[value])), 'Unsafe owned path')

    def test_unknown_risk_level(self):
        self.invalid(graph(task(risk_level='whatever')), 'Unknown risk_level')

    def test_duplicate_dependencies(self):
        self.invalid(graph(task(depends_on=['P0-02', 'P0-02']), task('P0-02')), 'Duplicate depends_on')

    def test_dependency_gated_states(self):
        for state in ('READY', 'CLAIMED', 'RUNNING', 'REVIEW_PENDING',
                      'INTEGRATION_PENDING', 'INTEGRATED', 'DONE', 'REWORK'):
            with self.subTest(state=state):
                self.invalid(graph(task(), task('P0-02', status=state,
                             depends_on=['P0-01'], evidence=['evidence.log'])), 'incomplete dependency')

    def test_blocked_task_can_have_incomplete_dependency(self):
        validate_graph(graph(task(), task('P0-02', depends_on=['P0-01'], status='BLOCKED')), self.root)

    def test_done_requires_evidence(self):
        self.invalid(graph(task(status='DONE')), 'DONE task lacks evidence')

    def test_done_evidence_missing(self):
        self.invalid(graph(task(status='DONE', evidence=['absent.log'])), 'Missing, unsafe or non-file evidence')

    def test_done_evidence_directory(self):
        (self.root / 'logs').mkdir()
        self.invalid(graph(task(status='DONE', evidence=['logs/'])), 'non-file evidence')

    def test_evidence_traversal(self):
        for value in ('../evidence.log', '/etc/passwd', 'docs/../../secret'):
            with self.subTest(path=value):
                self.invalid(graph(task(status='DONE', evidence=[value])), 'Unsafe evidence path')

    def test_evidence_symlink_file_and_parent(self):
        outside = self.root / 'outside'
        outside.mkdir()
        (outside / 'real.log').write_text('evidence')
        (self.root / 'file-link').symlink_to(outside / 'real.log')
        (self.root / 'dir-link').symlink_to(outside, target_is_directory=True)
        for value in ('file-link', 'dir-link/real.log'):
            with self.subTest(path=value):
                self.invalid(graph(task(status='DONE', evidence=[value])), 'unsafe or non-file evidence')

    def test_document_shape_and_field_types(self):
        for data in ([], {}, graph(), graph(task(depends_on='P0-02')),
                     graph(task(status=[])), graph(task(owner=[])),
                     dict(graph(task()), schema_version='2.0')):
            with self.subTest(data=data):
                self.invalid(data, '.')

    def test_import_has_no_cli_side_effect(self):
        result = subprocess.run([sys.executable, '-c', 'import validate_task_graph'],
                                cwd=SCRIPT.parent, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, '')
        self.assertEqual(result.stderr, '')

    def test_cli_path_and_exit_codes(self):
        fixture = self.root / 'tasks.json'
        fixture.write_text(json.dumps(graph(task(status='DONE', evidence=['evidence.log']))))
        good = subprocess.run([sys.executable, str(SCRIPT), str(fixture)], text=True, capture_output=True)
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertIn('PASS: 1 tasks', good.stdout)
        fixture.write_text('{broken json')
        bad = subprocess.run([sys.executable, str(SCRIPT), str(fixture)], text=True, capture_output=True)
        self.assertEqual(bad.returncode, 1)
        self.assertIn('FAIL:', bad.stderr)
        self.assertNotIn('Traceback', bad.stderr)

    def test_cli_duplicate_json_keys(self):
        fixture = self.root / 'duplicate.json'
        fixture.write_text('{"project":"SkillBridge","project":"other"}')
        result = subprocess.run([sys.executable, str(SCRIPT), str(fixture)], text=True, capture_output=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('Duplicate JSON key', result.stderr)

    def test_cli_missing_file(self):
        result = subprocess.run([sys.executable, str(SCRIPT), str(self.root / 'absent')],
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('FAIL:', result.stderr)
        self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
