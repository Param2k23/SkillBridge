# Worker task packet template

You are the `{role}` worker for `{task_id}` in SkillBridge. Read `AGENTS.md`, `ROADMAP.md` and the assigned `tasks.json` entry. Do not work on unrelated tasks.

- Task goal: `{goal}`
- Dependencies confirmed done: `{dependency_ids}`
- Starting commit: `{base_sha}`
- Assigned worktree and branch: `{worktree}` / `{branch}`
- Allowed edit paths: `{allowed_paths}`
- Frozen contracts: `{contracts}`
- Acceptance checks: `{acceptance}`
- Non-goals: `{non_goals}`
- External actions requiring human approval: `{approvals}`

First inspect the current repository state. If unsafe overlap, broken dependency, missing permissions, missing SDK or blocker exists, return BLOCKED with evidence. Otherwise implement the smallest scoped change, write focused positive/negative tests, and run the relevant commands. No pretend passes. Do not merge or deploy. Return branch/commit/changed paths/test command+observed output/risks/acceptance and request independent review.

# Independent reviewer task packet

Review `{task_id}` at `{commit_sha}` against `{base_sha}`. Do not modify files. Independently run contract, negative, regression and security tests relevant to the patch. Return PASS/FAIL/BLOCKED with exact reproduction and file locations. Check if any claimed tests are not actually executed. Check forbidden scope, secrets, auth, tenant isolation, immutable versions and client-compatibility truthfulness. Suggest bounded rework tasks when needed.
