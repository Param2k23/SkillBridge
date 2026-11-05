#!/usr/bin/env python3
"""Local dependency runner. No cloud endpoints, SDK credential lookup or reset."""
from __future__ import annotations
import argparse
import json
import os
import re
import socket
import struct
from pathlib import Path
import subprocess
import sys
from urllib import request, error
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ROOT / 'deploy/compose.json'
PROXY_CONFIG = ROOT / 'deploy/local/haproxy.cfg'
S3_BASE = 'http://127.0.0.1:19090'
SQL = "BEGIN; CREATE TEMP TABLE skillbridge_smoke(value text) ON COMMIT DROP; INSERT INTO skillbridge_smoke VALUES ('roundtrip-ok'); SELECT value FROM skillbridge_smoke; ROLLBACK;"


def require_regular_config(path: Path) -> None:
    for component in (path.absolute(), *path.absolute().parents):
        if component.is_symlink():
            raise ValueError('Configuration must not traverse a symlink')
    if not path.is_file() or path.stat().st_size > 16384:
        raise ValueError('Configuration must be a bounded regular file')


def validate_proxy_config(path: Path = PROXY_CONFIG) -> None:
    require_regular_config(path)
    # Deliberately accept only this reviewed topology, rather than arbitrary
    # HAProxy directives, destinations, admin sockets or dynamic forwarding.
    expected = {
        'global': ['log stdout format raw local0', 'maxconn 128'],
        'defaults': ['mode tcp', 'timeout connect 5s', 'timeout client 30s', 'timeout server 30s'],
        'resolvers docker': ['nameserver docker 127.0.0.11:53', 'resolve_retries 3',
                             'timeout resolve 1s', 'timeout retry 1s', 'hold valid 10s'],
        'frontend postgres_local': ['bind :15432', 'default_backend postgres_backend'],
        'backend postgres_backend': ['server postgres postgres:5432 check resolvers docker init-addr libc,none'],
        'frontend s3_local': ['bind :19090', 'default_backend s3_backend'],
        'backend s3_backend': ['server s3mock s3mock:9090 check resolvers docker init-addr libc,none'],
    }
    actual = {}
    section = None
    for raw in path.read_text(encoding='utf-8').splitlines():
        line = ' '.join(raw.split('#', 1)[0].split())
        if not line:
            continue
        if line in expected:
            if line in actual:
                raise ValueError('Duplicate proxy configuration section')
            section = line
            actual[section] = []
        elif section is None:
            raise ValueError('Unexpected proxy configuration')
        else:
            actual[section].append(line)
    if list(actual) != list(expected) or actual != expected:
        raise ValueError('Proxy permits only the reviewed fixed TCP destinations')


def validate_config(path: Path = COMPOSE, proxy_path: Path = PROXY_CONFIG) -> dict:
    require_regular_config(path)
    config = json.loads(path.read_text())
    if config.get('name') != 'skillbridge-local' or set(config['services']) != {'postgres', 's3mock', 'proxy'}:
        raise ValueError('Unexpected local project/services')
    for service in config['services'].values():
        image = service.get('image', '')
        if not re.fullmatch(r'[a-z0-9/]+:[A-Za-z0-9.\-]+@sha256:[0-9a-f]{64}', image):
            raise ValueError('Images require an exact version and SHA-256 digest')
        if any(port.get('host_ip') != '127.0.0.1' for port in service.get('ports', [])):
            raise ValueError('Only loopback port bindings are permitted')
        if not service.get('healthcheck') or service.get('security_opt') != ['no-new-privileges:true']:
            raise ValueError('Bounded health checks and privilege restriction required')
        if any(service.get(key) for key in ('privileged', 'network_mode', 'env_file', 'cap_add',
                                            'command', 'entrypoint', 'secrets', 'configs')):
            raise ValueError('Unexpected privilege/network/credential configuration')
    if set(config['networks']) != {'local', 'edge'} or config['networks']['local'] != {'internal': True}:
        raise ValueError('Local service network must be internal')
    if config.get('volumes') != {'postgres-data': {}}:
        raise ValueError('Only the project-owned PostgreSQL volume is permitted')
    for name in ('postgres', 's3mock'):
        backend = config['services'][name]
        if backend.get('networks') != ['local'] or backend.get('ports'):
            raise ValueError('Data services must remain internal-only without host ports')
    if config['services']['postgres'].get('volumes') != ['postgres-data:/var/lib/postgresql'] or config['services']['s3mock'].get('volumes'):
        raise ValueError('Data services cannot mount host paths or unrelated volumes')
    edge = config['networks']['edge']
    if edge.get('internal') is not False or edge.get('driver_opts') != {
            'com.docker.network.bridge.host_binding_ipv4': '127.0.0.1'}:
        raise ValueError('Proxy edge network must default to loopback publication')
    proxy = config['services']['proxy']
    if proxy.get('networks') != ['local', 'edge']:
        raise ValueError('Only the fixed proxy may join the edge network')
    if proxy.get('user') != '65534:65534' or proxy.get('read_only') is not True or proxy.get('cap_drop') != ['ALL']:
        raise ValueError('Proxy must be unprivileged, read-only and drop all capabilities')
    expected_ports = [{'target': port, 'published': str(port), 'host_ip': '127.0.0.1'}
                      for port in (15432, 19090)]
    if proxy.get('ports') != expected_ports or proxy.get('volumes') != [
            './local/haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg:ro']:
        raise ValueError('Proxy permits only fixed local ports and read-only configuration')
    validate_proxy_config(proxy_path)
    return config


def run(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=ROOT, timeout=kwargs.pop('timeout', 30), check=True, **kwargs)


def is_local_docker_endpoint(endpoint: object) -> bool:
    # Named pipes can address other Windows hosts. Only these reviewed local
    # Docker Engine/Desktop pipe names and the literal dot authority are allowed.
    if not isinstance(endpoint, str):
        return False
    if endpoint in {
        'npipe:////./pipe/docker_engine',
        'npipe:////./pipe/dockerDesktopLinuxEngine',
    }:
        return True
    if not endpoint.startswith('unix:///'):
        return False
    # Require an absolute canonical path: no authority, percent escapes, query,
    # fragment, empty/dot segments, Windows separators or whitespace.
    segments = endpoint[len('unix:///'):].split('/')
    return all(segment not in {'', '.', '..'} and
               re.fullmatch(r'[A-Za-z0-9_.-]+', segment) is not None
               for segment in segments)


def require_local_docker(binary: str) -> None:
    host = os.environ.get('DOCKER_HOST')
    if host is not None and not is_local_docker_endpoint(host):
        raise ValueError('Remote DOCKER_HOST is forbidden for local smoke checks')
    context = run([binary, 'context', 'inspect', '--format', '{{json .Endpoints.docker.Host}}'],
                  text=True, capture_output=True)
    endpoint = json.loads(context.stdout)
    if not is_local_docker_endpoint(endpoint):
        raise ValueError('Remote Docker context is forbidden for local smoke checks')
    run([binary, 'info'], text=True, capture_output=True)


def compose(binary: str, *args: str, **kwargs) -> subprocess.CompletedProcess:
    return run([binary, 'compose', '--project-name', 'skillbridge-local', '-f', str(COMPOSE), *args], **kwargs)


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Redirect refused by local-only S3 smoke')


def s3_request(method: str, path: str, data: bytes | None = None) -> bytes:
    # Fixed loopback origin, disabled proxies, and no redirect following. No AWS
    # credentials are read: S3Mock explicitly supports anonymous local requests.
    opener = request.build_opener(request.ProxyHandler({}), NoRedirect())
    req = request.Request(S3_BASE + path, data=data, method=method)
    with opener.open(req, timeout=5) as response:
        if response.status not in (200, 204):
            raise ValueError('Unexpected local S3 response status')
        return response.read(1024 * 1024)


def require_s3_absent(path: str) -> None:
    try:
        s3_request('GET', path)
    except error.HTTPError as exc:
        exc.close()
        if exc.code == 404:
            return
        raise
    raise ValueError('Disposable S3 resource remains after deletion')


def require_published_ports(binary: str) -> None:
    for port in (15432, 19090):
        result = compose(binary, 'port', 'proxy', str(port), text=True, capture_output=True)
        if result.stdout.strip() != f'127.0.0.1:{port}':
            raise ValueError('Expected loopback port was not actually published')
    # Verify that the host TCP publication reaches PostgreSQL, not just a generic
    # listening socket. SQL authentication/query validation follows through proxy.
    with socket.create_connection(('127.0.0.1', 15432), timeout=5) as connection:
        connection.sendall(struct.pack('!II', 8, 80877103))  # PostgreSQL SSLRequest
        if connection.recv(1) not in {b'N', b'S'}:
            raise ValueError('Published PostgreSQL endpoint failed its protocol probe')


def smoke(binary: str) -> None:
    require_published_ports(binary)
    result = compose(binary, 'exec', '-T', '-e', 'PGPASSWORD', 'postgres', 'psql', '-qAt', '-w', '-v',
                     'ON_ERROR_STOP=1', '-U', 'skillbridge', '-d', 'skillbridge',
                     '-h', 'proxy', '-p', '15432', input=SQL, text=True, capture_output=True,
                     env={**os.environ, 'PGPASSWORD': 'local-only-disposable'})
    if result.stdout.strip() != 'roundtrip-ok':
        raise ValueError('PostgreSQL transaction read/write mismatch')
    s3_request('GET', '/favicon.ico')
    bucket = '/skillbridge-smoke-' + uuid4().hex
    key = bucket + '/roundtrip.txt'
    created = False
    try:
        s3_request('PUT', bucket, b'')
        created = True
        body = b'skillbridge-local-smoke\n'
        s3_request('PUT', key, body)
        if s3_request('GET', key) != body:
            raise ValueError('Local S3 object round-trip mismatch')
    finally:
        # Delete only this invocation's random disposable test resources. Never
        # enumerate or remove existing buckets, tables or Compose volumes.
        if created:
            s3_request('DELETE', key)
            require_s3_absent(key)
            s3_request('DELETE', bucket)
            require_s3_absent(bucket)
    print('PASS: host PostgreSQL publication, authenticated SQL and S3Mock round trips/cleanup')


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['check', 'config', 'up', 'smoke', 'down'])
    parser.add_argument('--docker', choices=['docker', 'docker.exe'], default='docker')
    args = parser.parse_args(argv)
    try:
        validate_config()
        if args.action == 'check':
            print('PASS: static local configuration policy (not Docker startup)')
            return 0
        if args.action == 'config':
            compose(args.docker, 'config', '--quiet')
            return 0
        require_local_docker(args.docker)
        if args.action == 'up':
            compose(args.docker, 'up', '-d', '--wait', '--wait-timeout', '120', timeout=180)
            smoke(args.docker)
        elif args.action == 'smoke':
            smoke(args.docker)
        else:
            compose(args.docker, 'down', '--timeout', '20', timeout=60)
        return 0
    except subprocess.CalledProcessError as exc:
        # Fixed CLI invocations contain only disposable local configuration.
        print(f'FAIL: local command exited {exc.returncode}', file=sys.stderr)
        if exc.stdout:
            print(exc.stdout.strip(), file=sys.stderr)
        if exc.stderr:
            print(exc.stderr.strip(), file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired, error.URLError) as exc:
        print(f'FAIL: {type(exc).__name__}: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
