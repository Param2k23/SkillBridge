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
        self.assertEqual(set(manage.validate_config()['services']), {'postgres', 's3mock', 'proxy'})

    def mutated_config(self, mutate):
        data = json.loads(manage.COMPOSE.read_text())
        mutate(data)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'compose.json'
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                manage.validate_config(path)

    def test_rejects_public_binding(self):
        self.mutated_config(lambda c: c['services']['proxy']['ports'][0].update(host_ip='0.0.0.0'))

    def test_rejects_unpinned_image(self):
        self.mutated_config(lambda c: c['services']['s3mock'].update(image='adobe/s3mock:latest'))

    def test_rejects_external_network(self):
        self.mutated_config(lambda c: c['networks']['local'].update(internal=False))

    def test_data_services_cannot_join_edge_or_publish_ports(self):
        for name in ('postgres', 's3mock'):
            with self.subTest(service=name):
                self.mutated_config(lambda c: c['services'][name].update(networks=['local', 'edge']))
                self.mutated_config(lambda c: c['services'][name].update(
                    ports=[{'target': 1234, 'published': '1234', 'host_ip': '127.0.0.1'}]))

    def test_proxy_privileges_and_mounts_are_fixed(self):
        for update in ({'read_only': False}, {'user': '0:0'}, {'cap_drop': []},
                       {'cap_add': ['NET_ADMIN']}, {'network_mode': 'host'},
                       {'volumes': ['/var/run/docker.sock:/var/run/docker.sock:ro']}):
            with self.subTest(update=update):
                self.mutated_config(lambda c: c['services']['proxy'].update(update))

    def test_unrelated_volumes_host_sockets_and_command_overrides_are_rejected(self):
        self.mutated_config(lambda c: c['volumes']['postgres-data'].update(external=True, name='unrelated'))
        for name in ('postgres', 's3mock', 'proxy'):
            with self.subTest(service=name):
                self.mutated_config(lambda c: c['services'][name].update(
                    volumes=['/var/run/docker.sock:/var/run/docker.sock']))
                self.mutated_config(lambda c: c['services'][name].update(command=['sh', '-c', 'false']))

    def test_proxy_config_symlink_and_parent_rejected_before_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'real').mkdir()
            actual = root / 'real/haproxy.cfg'
            actual.write_text(manage.PROXY_CONFIG.read_text())
            (root / 'direct.cfg').symlink_to(actual)
            (root / 'parent').symlink_to(root / 'real', target_is_directory=True)
            for path in (root / 'direct.cfg', root / 'parent/haproxy.cfg'):
                with self.subTest(path=path), patch.object(Path, 'read_text', side_effect=AssertionError('must not read')):
                    with self.assertRaisesRegex(ValueError, 'symlink'):
                        manage.validate_proxy_config(path)

    def test_proxy_cannot_forward_arbitrary_destinations_or_expose_admin(self):
        original = manage.PROXY_CONFIG.read_text()
        for content in (original.replace('postgres:5432', 'example.invalid:5432'),
                        original + '\nlisten admin\n bind :9999\n stats enable\n',
                        original.replace('mode tcp', 'mode http')):
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / 'haproxy.cfg'
                path.write_text(content)
                with self.assertRaises(ValueError):
                    manage.validate_proxy_config(path)

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
        with patch.object(manage, 'require_published_ports'), patch.object(manage, 'compose', return_value=response), patch.object(manage, 's3_request') as s3:
            with self.assertRaisesRegex(ValueError, 'PostgreSQL'):
                manage.smoke('docker')
            s3.assert_not_called()

    def test_missing_runtime_port_fails_before_socket_or_sql(self):
        response = subprocess.CompletedProcess([], 0, stdout='')
        with patch.object(manage, 'compose', return_value=response), patch.object(manage.socket, 'create_connection') as connect:
            with self.assertRaisesRegex(ValueError, 'actually published'):
                manage.require_published_ports('docker')
            connect.assert_not_called()

    def test_cleanup_requires_not_found(self):
        from urllib.error import HTTPError
        absent = HTTPError('http://127.0.0.1:19090/test', 404, 'not found', {}, None)
        with patch.object(manage, 's3_request', side_effect=absent):
            manage.require_s3_absent('/test')
        with patch.object(manage, 's3_request', return_value=b'remains'):
            with self.assertRaisesRegex(ValueError, 'remains'):
                manage.require_s3_absent('/test')
        denied = HTTPError('http://127.0.0.1:19090/test', 403, 'denied', {}, None)
        with patch.object(manage, 's3_request', side_effect=denied):
            with self.assertRaises(HTTPError):
                manage.require_s3_absent('/test')


if __name__ == '__main__':
    unittest.main(verbosity=2)
