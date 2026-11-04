from pathlib import Path
import tempfile
import unittest

from check_reproducible import assert_identical, snapshot, preflight_outputs, clean_outputs
from secret_scan import findings, scan_file


class SecretScanTests(unittest.TestCase):
    def test_detects_known_formats_without_reporting_values(self):
        samples = [
            ('aws-access-key', 'AK' + 'IA' + 'X' * 16),
            ('github-token', 'gh' + 'p_' + 'a' * 36),
            ('private-key', '-----BEGIN ' + 'PRIVATE KEY-----'),
            ('bearer-token', 'Authorization: Bearer ' + 'a' * 40),
            ('assigned-secret', 'client_secret="' + 'a' * 40 + '"'),
            ('assigned-secret', 'aws_secret_access_key=' + 'a' * 40),
            ('assigned-secret', 'client_secret: ' + 'b' * 40),
        ]
        for rule, value in samples:
            with self.subTest(rule=rule):
                result = findings('\n' + value)
                self.assertIn((rule, 2), result)
                self.assertNotIn(value, repr(result))

    def test_safe_examples_and_short_placeholders(self):
        self.assertEqual(findings('api_key="example"\nNo credentials supplied.'), [])

    def test_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'target'
            target.write_text('safe')
            link = Path(tmp) / 'link'
            link.symlink_to(target)
            with self.assertRaises(ValueError):
                scan_file(link, Path(tmp))


    def test_rejects_symlink_parent_before_reading(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
            root = Path(tmp)
            (Path(outside) / 'credentials').write_text('client_secret=' + 'a' * 40)
            (root / 'linked').symlink_to(outside, target_is_directory=True)
            with patch.object(Path, 'read_bytes', side_effect=AssertionError('must not read')):
                with self.assertRaises(ValueError):
                    scan_file(root / 'linked' / 'credentials', root)
            with self.assertRaises(ValueError):
                scan_file(Path(outside) / 'credentials', root)


class ReproducibilityTests(unittest.TestCase):
    def test_changed_missing_and_added_artifacts_fail(self):
        for second in ({'a': 'changed'}, {}, {'a': 'same', 'b': 'new'}):
            with self.subTest(second=second):
                with self.assertRaises(ValueError):
                    assert_identical({'a': 'same'}, second)

    def test_identical_artifacts_pass(self):
        assert_identical({'a': 'same'}, {'a': 'same'})

    def test_empty_or_symlink_artifacts_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'dist'
            output.mkdir()
            with self.assertRaises(ValueError):
                snapshot([output])
            (output / 'file.js').symlink_to(Path(tmp) / 'outside')
            with self.assertRaises(ValueError):
                snapshot([output])


    def test_whole_set_preflight_preserves_inside_and_outside_markers(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
            root, external = Path(tmp), Path(outside)
            safe = root / 'packages' / 'a-safe'
            safe.mkdir(parents=True)
            (safe / 'package.json').write_text('{}')
            (safe / 'dist').mkdir()
            (safe / 'dist' / 'keep.txt').write_text('inside')
            (external / 'package.json').write_text('{}')
            (external / 'dist').mkdir()
            sentinel = external / 'dist' / 'keep.txt'
            sentinel.write_text('outside')
            (root / 'packages' / 'z-linked').symlink_to(external, target_is_directory=True)
            with self.assertRaises(ValueError):
                preflight_outputs(root)
            with self.assertRaises(ValueError):
                clean_outputs(root, [safe / 'dist', root / 'packages' / 'z-linked' / 'dist'])
            self.assertEqual(sentinel.read_text(), 'outside')
            self.assertEqual((safe / 'dist' / 'keep.txt').read_text(), 'inside')

    def test_symlink_manifest_and_outside_outputs_fail(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
            root = Path(tmp)
            package = root / 'packages' / 'sample'
            package.mkdir(parents=True)
            target = Path(outside) / 'package.json'
            target.write_text('{}')
            (package / 'package.json').symlink_to(target)
            with self.assertRaises(ValueError):
                preflight_outputs(root)
            with self.assertRaises(ValueError):
                clean_outputs(root, [Path(outside) / 'dist'])


if __name__ == '__main__':
    unittest.main()
