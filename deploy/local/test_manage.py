import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('local_manage', Path(__file__).with_name('manage.py'))
manage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(manage)


class LocalPolicyTests(unittest.TestCase):
    def test_current_config(self):
        self.assertEqual(set(manage.validate_config()['services']), {'postgres', 's3mock'})

    def mutated_config(self, mutate):
        data = json.loads(manage.COMPOSE.read_text())
        mutate(data)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'compose.json'
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                manage.validate_config(path)

    def test_rejects_public_binding(self):
        self.mutated_config(lambda c: c['services']['postgres']['ports'][0].update(host_ip='0.0.0.0'))

    def test_rejects_unpinned_image(self):
        self.mutated_config(lambda c: c['services']['s3mock'].update(image='adobe/s3mock:latest'))

    def test_rejects_external_network(self):
        self.mutated_config(lambda c: c['networks']['local'].update(internal=False))

    def test_rejects_symlink_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'original.json'
            target.write_text(manage.COMPOSE.read_text())
            link = Path(tmp) / 'linked.json'
            link.symlink_to(target)
            with self.assertRaises(ValueError):
                manage.validate_config(link)

    def test_rejects_symlink_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / 'source').mkdir()
            (base / 'source/compose.json').write_text(manage.COMPOSE.read_text())
            (base / 'link').symlink_to(base / 'source', target_is_directory=True)
            with self.assertRaises(ValueError):
                manage.validate_config(base / 'link/compose.json')

    def test_remote_host_rejected_before_cli(self):
        with patch.dict(os.environ, {'DOCKER_HOST': 'tcp://remote.example:2375'}), patch.object(manage, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'Remote DOCKER_HOST'):
                manage.require_local_docker('docker')
            run.assert_not_called()

    def test_remote_context_rejected_before_info(self):
        response = subprocess.CompletedProcess([], 0, stdout='"ssh://remote.example"')
        with patch.dict(os.environ, {}, clear=True), patch.object(manage, 'run', return_value=response) as run:
            with self.assertRaisesRegex(ValueError, 'Remote Docker context'):
                manage.require_local_docker('docker')
            self.assertEqual(run.call_count, 1)

    def test_remote_named_pipe_host_rejected_before_cli(self):
        with patch.dict(os.environ, {'DOCKER_HOST': 'npipe:////remote-host/pipe/docker_engine'}), patch.object(manage, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'Remote DOCKER_HOST'):
                manage.require_local_docker('docker.exe')
            run.assert_not_called()

    def test_remote_named_pipe_context_rejected_before_info(self):
        response = subprocess.CompletedProcess([], 0, stdout='"npipe:////remote-host/pipe/docker_engine"')
        with patch.dict(os.environ, {}, clear=True), patch.object(manage, 'run', return_value=response) as run:
            with self.assertRaisesRegex(ValueError, 'Remote Docker context'):
                manage.require_local_docker('docker.exe')
            self.assertEqual(run.call_count, 1)

    def test_local_contexts_reach_info(self):
        # Unit guard coverage only. Mocking these commands does not prove that an
        # engine exists or that Compose/services can start.
        for endpoint in ('unix:///var/run/docker.sock',
                         'unix:///home/user/.docker/desktop/docker.sock',
                         'npipe:////./pipe/docker_engine',
                         'npipe:////./pipe/dockerDesktopLinuxEngine'):
            with self.subTest(endpoint=endpoint):
                responses = [subprocess.CompletedProcess([], 0, stdout=json.dumps(endpoint)),
                             subprocess.CompletedProcess([], 0, stdout='')]
                with patch.dict(os.environ, {}, clear=True), patch.object(manage, 'run', side_effect=responses) as run:
                    manage.require_local_docker('docker')
                    self.assertEqual(run.call_args_list[-1].args[0], ['docker', 'info'])

    def test_noncanonical_endpoint_forms_rejected(self):
        for endpoint in ('unix://remote/tmp/socket', 'unix:////tmp/socket',
                         'unix:///tmp/../socket', 'unix:///tmp/./socket',
                         'unix:///tmp/socket?x=1', 'unix:///tmp/socket#fragment',
                         'unix:///tmp/%73ocket', 'unix:///tmp/socket/',
                         'unix:///tmp/with space/socket', 'unix:///tmp/socket\\name',
                         'npipe:////localhost/pipe/docker_engine',
                         'npipe:////./pipe/unreviewed', None, [], {}):
            with self.subTest(endpoint=endpoint):
                self.assertFalse(manage.is_local_docker_endpoint(endpoint))

    def test_redirect_is_never_followed(self):
        with self.assertRaisesRegex(ValueError, 'Redirect refused'):
            manage.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://example.invalid')

    def test_database_mismatch_fails_before_s3(self):
        response = subprocess.CompletedProcess([], 0, stdout='unexpected')
        with patch.object(manage, 'compose', return_value=response), patch.object(manage, 's3_request') as s3:
            with self.assertRaisesRegex(ValueError, 'PostgreSQL'):
                manage.smoke('docker')
            s3.assert_not_called()


if __name__ == '__main__':
    unittest.main(verbosity=2)
