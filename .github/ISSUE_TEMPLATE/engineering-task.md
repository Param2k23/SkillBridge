---
name: Engineering task
about: Bounded implementation or focused correction packet
---

## Task packet

- Task ID and approved phase:
- Owner/role:
- Dependencies and evidence that they are DONE:
- Reviewed base commit, dedicated branch/worktree:
- Exclusive allowed files and frozen interfaces:
- Goal and non-goals:
- Acceptance commands and expected observable behavior:
- Required positive/negative cases:
- Risk level and approval boundaries:
- Independent reviewer:

## Evidence and status

Record TASK / ROLE / BRANCH / COMMIT / DIFF SUMMARY / TESTS WITH OBSERVED OUTPUT /
RISKS / REVIEW REQUEST / STATUS. Include actual exit codes and sanitized logs;
separate local checks, hosted CI and client compatibility. Workers request
REVIEW_PENDING; only the coordinator records DONE.

For failed validation, identify the exact reproduction and focused correction.
Allow at most two correction loops, then report BLOCKED. Do not start dependent
work or weaken checks to avoid a failure. No cloud, credentials, public publishing,
protected merge or release authorization is implied by this issue.
