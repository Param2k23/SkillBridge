# Engineering workflow

Use one approved phase/wave at a time. `tasks.json` defines task IDs, dependencies,
owner, allowed paths, acceptance, evidence and state; the coordinator alone changes
states. Validate it with `python3 scripts/validate_task_graph.py`.

## Assignment and isolation

Before assigning a task, verify its dependencies are DONE with valid evidence.
Freeze shared interfaces before parallel implementation. Every writable task gets
its own Git branch and worktree from the reviewed integration commit:

```bash
git worktree add /tmp/skillbridge-TASK -b feature/TASK REVIEWED_COMMIT
```

Replace the placeholders; this is a local setup example, not permission to merge,
push or deploy. The coordinator records the exact base, branch, worktree, owner
and exclusive file list. Writers work only in their assigned checkout. Root tool
configuration and shared contracts have one writer at a time. Worktree isolation
does not itself authorize conflicting ownership. Research/QA may run read-only
checks concurrently; generated output must stay local and must not alter sources.

## Task lifecycle and evidence

```text
BACKLOG -> READY -> CLAIMED -> RUNNING -> REVIEW_PENDING
  -> INTEGRATION_PENDING -> INTEGRATED -> DONE
  -> REWORK -> RUNNING
  -> BLOCKED -> READY
```

The coordinator authorizes READY after dependency checks. Workers inspect, plan,
implement, run targeted tests and request review. The independent reviewer reports
PASS, FAIL or BLOCKED with exact reproductions. A FAIL creates a bounded repair
assignment; after two unsuccessful correction loops, stop that task and report its
blocker. Do not weaken checks or advance dependents to evade a failure.

Integration follows inspection of the actual diff and independent PASS. Integrate
sequentially into an unprotected local integration branch; protected merges still
need human approval. Run the complete available integration checks from a clean
checkout, record the actual commit and results, then mark DONE. The coordinator
recomputes eligible tasks after each milestone; eligibility is not permission to
start a new phase. Queue work with unmet dependencies.

Each report includes TASK / ROLE / BRANCH / COMMIT / DIFF SUMMARY / TESTS WITH
OBSERVED OUTPUT / RISKS / REVIEW REQUEST / STATUS. Evidence belongs under
`project/evidence/` or another explicit repository path. Never put credentials,
auth headers, publisher content or personal data in logs. Every DONE evidence
link must be an existing regular repository file with no symlink component.
Evidence existence does not prove the contained claims; QA must inspect them.

## Validation and negative cases

After bootstrap, run the five required pnpm commands from `AGENTS.md`: frozen
install, lint, typecheck, test and build. Run task-DAG tests as well:

```bash
python3 scripts/validate_task_graph.py
python3 -m unittest discover -s scripts -p 'test_validate_task_graph.py' -v
```

An alternate task document can be checked with
`python3 scripts/validate_task_graph.py /path/to/tasks.json --root /path/to/repo`.
The root defaults to the document's directory. The CLI exits 0 on valid input, 1
on validation/read/JSON failure and 2 on invalid command usage. Importing the
module runs no CLI actions. Eligible BACKLOG IDs are informational; validation
never changes task states or authorizes work.

The validator checks document fields, ownership paths, IDs, dependencies, phases,
cycles, dependency-gated states and DONE evidence. Its negative tests cover
missing/duplicate/cyclic dependencies, premature READY or DONE, unknown states,
unsafe/missing evidence and symlink components. It validates a snapshot, not the
history of transitions, branch protection or the truth of test logs. It does not
reject overlapping owned paths across BACKLOG tasks; the coordinator enforces
exclusive assignments for concurrently active worktrees.

Distinguish these evidence categories in every milestone:

- **Local:** observed commands with exit codes, OS/runtime and commit, including
  clean-checkout/frozen-lockfile validation. No network-dependent check is a pass
  if the network request failed.
- **Hosted CI:** an actual provider run URL and commit. A workflow YAML file or
  locally passing checks do not establish hosted CI. If no remote exists, report
  hosted CI unavailable; do not fabricate a run or credentials.
- **Client compatibility:** version-pinned real client connection/auth/retrieval
  traces. Unit tests or generic SDK clients do not verify Claude, Codex or Cursor.

## Approval boundaries

No AWS resources, deployment, spending, secret changes, credential use, expanded
IAM, irreversible action, public skill publishing, protected merge or release
without explicit human approval. Local smoke tests must not contact cloud APIs.
External service absence is a blocker or a recorded unrun check, not permission
to replace real validation with a mock success. Tests using permitted mocks must
be labeled as such.
