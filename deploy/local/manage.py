#!/usr/bin/env python3
"""Local dependency runner. No cloud endpoints, SDK credential lookup or reset."""
from __future__ import annotations
import argparse
import json
import os
import re
from pathlib import Path
import subprocess
import sys
from urllib import request, error
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ROOT / 'deploy/compose.json'
S3_BASE = 'http://127.0.0.1:19090'
SQL = "BEGIN; CREATE TEMP TABLE skillbridge_smoke(value text) ON COMMIT DROP; INSERT INTO skillbridge_smoke VALUES ('roundtrip-ok'); SELECT value FROM skillbridge_smoke; ROLLBACK;"


def validate_config(path: Path = COMPOSE) -> dict:
    for component in (path.absolute(), *path.absolute().parents):
        if component.is_symlink():
            raise ValueError('Compose config must not traverse a symlink')
    config = json.loads(path.read_text())
    if config.get('name') != 'skillbridge-local' or set(config['services']) != {'postgres', 's3mock'}:
        raise ValueError('Unexpected local project/services')
    for service in config['services'].values():
        image = service.get('image', '')
        if not re.fullmatch(r'[a-z0-9/]+:[A-Za-z0-9.\-]+@sha256:[0-9a-f]{64}', image):
            raise ValueError('Images require an exact version and SHA-256 digest')
        if any(port.get('host_ip') != '127.0.0.1' for port in service['ports']):
            raise ValueError('Only loopback port bindings are permitted')
        if service.get('networks') != ['local'] or not service.get('healthcheck'):
            raise ValueError('Local isolation and bounded health checks required')
        if service.get('privileged') or service.get('network_mode') or service.get('env_file'):
            raise ValueError('Unexpected privilege/network/credential configuration')
    if config['networks']['local'].get('internal') is not True:
        raise ValueError('Local service network must be internal')
    return config


def run(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=ROOT, timeout=kwargs.pop('timeout', 30), check=True, **kwargs)


def require_local_docker(binary: str) -> None:
    host = os.environ.get('DOCKER_HOST')
    if host is not None and not host.startswith(('unix://', 'npipe://')):
        raise ValueError('Remote DOCKER_HOST is forbidden for local smoke checks')
    context = run([binary, 'context', 'inspect', '--format', '{{json .Endpoints.docker.Host}}'],
                  text=True, capture_output=True)
    endpoint = json.loads(context.stdout)
    if not isinstance(endpoint, str) or not endpoint.startswith(('unix://', 'npipe://')):
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


def smoke(binary: str) -> None:
    result = compose(binary, 'exec', '-T', 'postgres', 'psql', '-qAt', '-v',
                     'ON_ERROR_STOP=1', '-U', 'skillbridge', '-d', 'skillbridge',
                     input=SQL, text=True, capture_output=True)
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
            s3_request('DELETE', bucket)
    print('PASS: PostgreSQL transaction and S3Mock object round trips')


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
