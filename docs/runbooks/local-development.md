# Local dependency stack

This stack is for disposable development data on a single workstation. It has
PostgreSQL and **Adobe S3Mock**, a local subset of S3 without production access
control or AWS durability guarantees. A fixed TCP proxy supplies loopback host
access while both data services stay on an internal-only network. No MCP service
or SQS emulator is included.
Nothing in these scripts provisions AWS, reads AWS credentials, or contacts AWS.

Use an already approved Docker Engine with Compose v2 and Python 3.11 or newer.
The Compose file is JSON (a YAML-compatible format supported by Compose), which
allows static checking with Python's standard library without installing tools.
No global package installation is required. The pinned image index digests were
verified with Docker Hub's public tag API on 2026-11-04:

- `postgres:18.6-alpine3.24`, index `sha256:10a5c69a83035ab5239f5620d708520e8b28f5aa1f2b20143e6024532edadfb5`.
- `adobe/s3mock:5.2.3`, index `sha256:ab01a6946750f451ca215a47e91030695b260e4003b8a5a6201d25029b8fca92`.
- `haproxy:3.2.26-alpine3.24`, index `sha256:5893840576071e6217cd52ebdcc14f454c6f7a631056fa6f4e0f40d3cac4215b`.

Sources: [official PostgreSQL image](https://hub.docker.com/_/postgres),
[PostgreSQL tag metadata](https://hub.docker.com/v2/repositories/library/postgres/tags/18.6-alpine3.24),
[S3Mock release documentation](https://github.com/adobe/S3Mock/tree/5.2.3), and
[S3Mock tag metadata](https://hub.docker.com/v2/repositories/adobe/s3mock/tags/5.2.3),
[HAProxy tag metadata](https://hub.docker.com/v2/repositories/library/haproxy/tags/3.2.26-alpine3.24),
and [HAProxy configuration manual](https://docs.haproxy.org/3.2/configuration.html).
Metadata and documentation alone do not prove image pullability, healthcheck
binaries, or startup. The Docker-backed checks below provide the observed runtime
evidence.

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
socket/named-pipe context and reachable engine, then starts the two dependencies and fixed proxy with
a bounded readiness wait and performs the real smoke check. The guard permits
only canonical absolute Unix socket URIs (`unix:///path/to/socket`) and these
reviewed local Windows pipes: `npipe:////./pipe/docker_engine` and
`npipe:////./pipe/dockerDesktopLinuxEngine`. Other authorities, remote named pipes,
noncanonical paths, percent escapes and unreviewed pipe names are rejected.
`DOCKER_HOST` is checked before any CLI call, then the selected context before
engine access. Unit tests of this guard use mocks and do not prove startup.
Starting the stack may download the three pinned images. `smoke` does not start services; it requires the running stack.
No success is reported if Docker, PostgreSQL, or S3Mock is unavailable.

Ports are bound only to `127.0.0.1`: PostgreSQL **15432**, S3Mock HTTP **19090**.
The data services have no host port publication and no external routing. Only
HAProxy joins both the internal backend network and a normal edge bridge; its
host port bindings remain explicit loopback-only. The edge bridge gives the
proxy an outbound route, not the database/S3Mock. This is a dedicated TCP relay
to the two fixed service names, not a general forward proxy. It runs as UID/GID
65534 with a read-only filesystem, all capabilities dropped and only its reviewed
configuration mounted read-only. Policy rejects symlinks in that mount or its
ancestors, arbitrary backend destinations, admin directives, command overrides,
host sockets and unrelated volumes.

Docker does not activate host port publication for containers attached only to
internal networks: their default-gateway network is absent. The original real
startup reproduced healthy containers with empty published-port bindings and a
host HTTP refusal. The fixed proxy supplies publication without changing the
data services to an external network. See the
[maintainer explanation](https://github.com/moby/moby/discussions/53256) and
[Docker port-publication guidance](https://docs.docker.com/engine/network/port-publishing/).
The runner checks actual published bindings and a host PostgreSQL protocol probe
before smoke tests; container health alone is insufficient. PostgreSQL uses database
and user `skillbridge`; `local-only-disposable` is a deliberately public local
test password, never a production secret. Do not reuse it or put private data here.
PostgreSQL 18 data is mounted at `/var/lib/postgresql` in the named project volume.
S3Mock data is ephemeral and may disappear when the container stops.

The smoke check creates a PostgreSQL session-local temporary table inside a
transaction, authenticates through the fixed proxy, verifies read/write and
rolls back. It uses a unique random
`skillbridge-smoke-*` S3Mock bucket, verifies exact object bytes, then deletes only
that invocation's object and bucket. It requires HTTP404 for the deleted object
and bucket, rather than inferring cleanup from a delete request alone. HTTP requests use a fixed loopback origin,
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

## Full host SQL and persistence acceptance check

The core runner uses Python standard-library HTTP and Docker's existing `psql`.
For a full host-originated authenticated SQL session and persistence across two
complete down/up cycles, use the optional lifecycle verifier. Its two exact driver
packages are pinned separately; they do not change product dependencies or install
global tooling:

```bash
python3 -m venv /tmp/skillbridge-pg-validation
/tmp/skillbridge-pg-validation/bin/python -m pip --isolated install --index-url https://pypi.org/simple --only-binary=:all: -r deploy/local/requirements-validation.txt
/tmp/skillbridge-pg-validation/bin/python deploy/local/verify_lifecycle.py
```

Psycopg 3.3.8 is pinned from [official package metadata](https://pypi.org/pypi/psycopg/3.3.8/json);
its [documented SQL API](https://www.psycopg.org/psycopg3/docs/basic/usage.html)
is used. The verifier connects explicitly to 127.0.0.1:15432, commits an own
randomly named table/marker, shuts down and recreates containers without deleting
the volume, verifies the marker, then drops only that own table. Each startup runs
real S3 object write/read/delete/not-found checks. Successful validation finishes
with containers stopped and the PostgreSQL volume retained. On failure services
remain inspectable and the JSON failure event identifies only its own marker for
recovery. No unrelated tables, buckets or volumes are removed. Native Windows
users can create an equivalent local venv and invoke the same verifier with
`--docker docker.exe`; no host or context settings are changed.

## Current Docker-backed evidence

The earlier environment-only blocker was resolved. With Docker Engine 29.6.2,
Docker Desktop 4.84.0 and Compose 5.3.1, the original internal-only topology pulled
its images and reached healthy containers but did not publish the requested host
ports. That failed run and empty runtime-port inspection remain preserved.

The focused proxy repair now passes static policy, 21 unit/negative tests, actual
Compose parsing and the native HAProxy configuration checker. All three pinned
images were pulled. Real verification completed two healthy startup/shutdown
cycles. The host driver authenticated to 127.0.0.1:15432 and performed committed
SQL read/write; its uniquely owned marker survived full container removal and
recreation, then was dropped and verified absent. Both startups and an additional
smoke ran real loopback S3 write/read/delete checks and required 404 responses for
the deleted object and bucket. Final checks found no project containers while
the PostgreSQL named volume remained. Backend services stayed internal-only;
only the fixed proxy published the two loopback ports.

These are observed development-environment results, not production AWS or
cross-platform certification. Independent QA and the coordinator's combined
integration/hosted checks remain separate gates; the worker does not mark its
own task DONE. No Terraform plan, cloud provisioning, global tooling installation,
host-setting change or unrelated data deletion was involved.
