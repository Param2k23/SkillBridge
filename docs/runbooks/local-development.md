# Local dependency stack

This stack is for disposable development data on a single workstation. It has
PostgreSQL and **Adobe S3Mock**, a local subset of S3 without production access
control or AWS durability guarantees. No MCP service or SQS emulator is included.
Nothing in these scripts provisions AWS, reads AWS credentials, or contacts AWS.

Use an already approved Docker Engine with Compose v2 and Python 3.11 or newer.
The Compose file is JSON (a YAML-compatible format supported by Compose), which
allows static checking with Python's standard library without installing tools.
No global package installation is required. The pinned image index digests were
verified with Docker Hub's public tag API on 2026-11-04:

- `postgres:18.6-alpine3.24`, index `sha256:10a5c69a83035ab5239f5620d708520e8b28f5aa1f2b20143e6024532edadfb5`.
- `adobe/s3mock:5.2.3`, index `sha256:ab01a6946750f451ca215a47e91030695b260e4003b8a5a6201d25029b8fca92`.

Sources: [official PostgreSQL image](https://hub.docker.com/_/postgres),
[PostgreSQL tag metadata](https://hub.docker.com/v2/repositories/library/postgres/tags/18.6-alpine3.24),
[S3Mock release documentation](https://github.com/adobe/S3Mock/tree/5.2.3), and
[S3Mock tag metadata](https://hub.docker.com/v2/repositories/adobe/s3mock/tags/5.2.3).
Image pullability, healthcheck binaries and actual startup still require Docker
execution; documentation and digest lookup are not runtime verification.

## Linux and WSL

From the checkout root:

```bash
python3 deploy/local/manage.py check
python3 -m unittest discover -s deploy/local -p 'test_*.py' -v
python3 deploy/local/manage.py config
python3 deploy/local/manage.py up
python3 deploy/local/manage.py smoke
python3 deploy/local/manage.py down
```

`check` and the unit tests only validate local configuration/failure behavior.
`config` invokes real Compose parsing. `up` first requires a local Docker
socket/named-pipe context and reachable engine, then starts both dependencies with
a bounded readiness wait and performs the real smoke check. It may download the
two pinned images. `smoke` does not start services; it requires the running stack.
No success is reported if Docker, PostgreSQL, or S3Mock is unavailable.

Ports are bound only to `127.0.0.1`: PostgreSQL **15432**, S3Mock HTTP **19090**.
The internal service network has no external routing. PostgreSQL uses database
and user `skillbridge`; `local-only-disposable` is a deliberately public local
test password, never a production secret. Do not reuse it or put private data here.
PostgreSQL 18 data is mounted at `/var/lib/postgresql` in the named project volume.
S3Mock data is ephemeral and may disappear when the container stops.

The smoke check creates a PostgreSQL session-local temporary table inside a
transaction, verifies read/write and rolls back. It uses a unique random
`skillbridge-smoke-*` S3Mock bucket, verifies exact object bytes, then deletes only
that invocation's object and bucket. HTTP requests use a fixed loopback origin,
no proxies, no redirects and no credential lookup. It never enumerates/deletes
existing data or Compose volumes. Failed smoke does not automatically stop the
stack so it remains inspectable. `down` stops containers and preserves PostgreSQL
volumes; there is no automated reset/data deletion command. Volume deletion or
migration of valuable data requires separate explicit authorization.

If Docker reports that this WSL distro is not integrated, or the Desktop Linux
engine named pipe is absent, startup is BLOCKED. A human must make the approved
engine available and enable the distro's Docker Desktop integration. These scripts
do not start Desktop, change settings, install Docker or select another context.
Do not replace a failed startup with a static-check pass.

## Windows PowerShell

Use a native Windows checkout and approved Windows Python/Docker Desktop:

```powershell
py -3 deploy/local/manage.py check
py -3 -m unittest discover -s deploy/local -p "test_*.py" -v
py -3 deploy/local/manage.py config --docker docker.exe
py -3 deploy/local/manage.py up --docker docker.exe
py -3 deploy/local/manage.py smoke --docker docker.exe
py -3 deploy/local/manage.py down --docker docker.exe
```

Inside WSL use the Linux `docker` integration instead. Passing Linux checkout
paths directly to Windows `docker.exe compose` is not supported by this runner.
No commands alter Windows settings or use external credentials.

## Current evidence boundary

Fresh authoring-environment checks found no reachable Docker daemon. The installed
Windows Compose CLI parsed this real file successfully using its WSL UNC path;
static policy and ten unit tests also passed. Linux/WSL Compose startup and smoke
failed at the missing integration, and Windows Docker reported the absent engine
pipe. These results do not verify startup/readiness/database/object round trips.
P1-05 remains BLOCKED until actual fresh startup and both round trips pass and
independent QA confirms the results. No cloud deployment or Terraform plan exists
or is needed for this local-only task.
