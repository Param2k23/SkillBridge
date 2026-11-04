# CI helper scope

`secret_scan.py` scans indexed and untracked nonignored source files for known
credential formats. It never prints matching values and fails on unreadable,
oversized or symlink sources, including paths with symlink ancestors. Named
secret assignments are recognized with or without quotes (for example INI/YAML). Detection is deliberately a documented baseline;
it does not prove all arbitrary secrets are absent. Synthetic tokens in tests
are assembled at runtime and never usable credentials.

`check_reproducible.py` removes only generated `dist` directories beneath known
workspace packages, runs the real build twice, and compares hashes of every emitted
file. Before any cleanup, it validates every package manifest and output path
for symlink ancestors and resolved containment under the trusted repository.
It rejects empty results and symlinks. This checks reproducibility within
one environment; it does not claim independent cross-platform reproducibility.

Local commands (using the pinned package manager, without a global installation):

```bash
python3 -m unittest discover -s .github/scripts -p 'test_*.py' -v
python3 .github/scripts/secret_scan.py
corepack pnpm audit --audit-level=low
python3 .github/scripts/check_reproducible.py
```

The workflow pins official action commit SHAs. Pins were resolved from official
`actions/{checkout,setup-node,setup-python}` v6 refs using `git ls-remote` on
2026-11-04. Source documentation:
https://github.com/actions/checkout, https://github.com/actions/setup-node,
https://github.com/actions/setup-python. `persist-credentials: false`, read-only
repository permissions, no secret inputs, no pull_request_target, no deployment.
Hosted CI has not run in this repository; a workflow file is not a passing run.
