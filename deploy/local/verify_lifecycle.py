#!/usr/bin/env python3
"""Real local lifecycle acceptance check; never substitutes mocked backend results."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from uuid import uuid4

import manage


def event(check: str, **details) -> None:
    print(json.dumps({'check': check, **details}), flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--docker', choices=['docker', 'docker.exe'], default='docker')
    args = parser.parse_args(argv)
    try:
        import psycopg
        from psycopg import sql
    except ImportError:
        print('FAIL: install requirements-validation.txt in an isolated validation venv first', file=sys.stderr)
        return 1

    # Explicit fixed local connection parameters, no service/credential-file or
    # environment lookup. Only this test process's environment is changed.
    for key in list(os.environ):
        if key.startswith('PG'):
            del os.environ[key]

    def connect():
        return psycopg.connect(host='127.0.0.1', hostaddr='127.0.0.1', port=15432,
                               dbname='skillbridge', user='skillbridge',
                               password='local-only-disposable', passfile=os.devnull,
                               sslmode='disable', connect_timeout=5,
                               options='-c statement_timeout=5000',
                               application_name='skillbridge-lifecycle-validation')

    def action(name: str) -> None:
        if manage.main([name, '--docker', args.docker]) != 0:
            raise RuntimeError('Local lifecycle action failed: ' + name)
        event(name, result='PASS')

    def health(label: str) -> None:
        result = manage.compose(args.docker, 'ps', '--format', '{{.Service}} {{.State}} {{.Health}}',
                                text=True, capture_output=True)
        rows = [line.split() for line in result.stdout.splitlines() if line.strip()]
        if {row[0] for row in rows} != {'postgres', 's3mock', 'proxy'} or any(
                len(row) != 3 or row[1:] != ['running', 'healthy'] for row in rows):
            raise RuntimeError('Not all three real services are healthy')
        event(label, services=rows, result='PASS')

    table = 'skillbridge_persistence_' + uuid4().hex
    marker = uuid4().hex
    created = False
    try:
        manage.validate_config()
        action('up')
        health('first-health')
        with connect() as conn:
            identity = conn.execute('SELECT current_database(), current_user, inet_server_port()').fetchone()
            if identity != ('skillbridge', 'skillbridge', 5432):
                raise RuntimeError('Host PostgreSQL server identity mismatch')
            conn.execute(sql.SQL('CREATE TABLE {} (value text NOT NULL)').format(sql.Identifier(table)))
            conn.execute(sql.SQL('INSERT INTO {} VALUES (%s)').format(sql.Identifier(table)), (marker,))
            if conn.execute(sql.SQL('SELECT value FROM {}').format(sql.Identifier(table))).fetchone() != (marker,):
                raise RuntimeError('Host PostgreSQL transaction read/write mismatch')
        created = True
        event('host-authenticated-sql', driver=psycopg.__version__, host='127.0.0.1', port=15432,
              table=table, committed=True, result='PASS')

        action('down')
        stopped = manage.compose(args.docker, 'ps', '--all', '--format', 'json', text=True, capture_output=True)
        if stopped.stdout.strip() not in ('', '[]'):
            raise RuntimeError('Project containers remain after first shutdown')
        volume = manage.run([args.docker, 'volume', 'inspect', 'skillbridge-local_postgres-data',
                             '--format', '{{.Name}}'], text=True, capture_output=True)
        if volume.stdout.strip() != 'skillbridge-local_postgres-data':
            raise RuntimeError('Project PostgreSQL volume was not retained')
        event('first-shutdown', containers_removed=True, postgres_volume_retained=True, result='PASS')

        action('up')
        health('second-health')
        with connect() as conn:
            if conn.execute(sql.SQL('SELECT value FROM {}').format(sql.Identifier(table))).fetchone() != (marker,):
                raise RuntimeError('Committed marker did not survive shutdown/startup')
            conn.execute(sql.SQL('DROP TABLE {}').format(sql.Identifier(table)))
        created = False
        with connect() as conn:
            if conn.execute('SELECT to_regclass(%s)', ('public.' + table,)).fetchone() != (None,):
                raise RuntimeError('Own persistence marker table remains after cleanup')
        event('host-sql-persistence-and-cleanup', table=table, result='PASS')
        action('smoke')
        action('down')
        stopped = manage.compose(args.docker, 'ps', '--all', '--format', 'json', text=True, capture_output=True)
        if stopped.stdout.strip() not in ('', '[]'):
            raise RuntimeError('Project containers remain after final shutdown')
        manage.run([args.docker, 'volume', 'inspect', 'skillbridge-local_postgres-data'],
                   text=True, capture_output=True)
        event('final-shutdown', containers_removed=True, postgres_volume_retained=True, result='PASS')
        print('PASS: two real startup/shutdown cycles, host-authenticated SQL, persisted marker and S3 round trips/cleanup')
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError,
            subprocess.TimeoutExpired, psycopg.Error) as exc:
        # Values/connection strings are not logged; the marker name is own test
        # metadata needed for recovery. Failed services stay available to inspect.
        event('lifecycle-failure', error_type=type(exc).__name__, marker_table=table,
              marker_created=created, result='FAIL')
        print('FAIL: real local lifecycle validation did not complete; inspect captured command evidence', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
