# SkillBridge multi-agent development starter pack

This is a **planning and orchestration seed**, not an implementation of SkillBridge. It is designed to be copied into a newly created Git repository and used with Codex's built-in agent orchestration. No AWS or GitHub resources have been created.

## Contents
- `ROADMAP.md` — full multi-phase implementation plan, quality gates, architecture, task state, parallel waves.
- `AGENTS.md` — durable constraints Codex reads in the repo.
- `tasks.json` — machine-readable dependency DAG and acceptance checks.
- `.codex/config.toml` — conservative subagent concurrency config (3).
- `.codex/agents/` — project-scoped role definitions.
- `KICKOFF_PROMPT.md` — copy into Codex at repo root to initiate Phase 0.
- `PHASE_TASK_PROMPT_TEMPLATE.md` — bounded worker/reviewer tasks.
- `scripts/validate_task_graph.py` — checks dependency references and cycles.

## Suggested start (Windows with WSL Ubuntu or local Linux)

```bash
mkdir -p ~/skillbridge && cd ~/skillbridge
git init
# Copy pack contents, including hidden .codex/ directory, into ~/skillbridge
python3 scripts/validate_task_graph.py
# Ensure Git identity is set on your machine
git add .
git commit -m "chore: seed SkillBridge agent execution plan"
codex login
codex
```

Paste `KICKOFF_PROMPT.md` into the Codex chat. Use `/subagents` to inspect actual delegated threads. For coding tasks that write files in parallel, create separate branches/worktrees, or use distinct Codex Worktree chats. Do not conflate subagents with Git worktree isolation.

## Live docs to confirm before coding
- https://learn.chatgpt.com/docs/agent-configuration/subagents
- https://learn.chatgpt.com/docs/environments/git-worktrees
- https://learn.chatgpt.com/docs/codex/cli
- https://modelcontextprotocol.io/specification
- https://skills.extensions.modelcontextprotocol.io/
- https://agentskills.io/
- https://openai.com/index/open-source-codex-orchestration-symphony/

**Usage:** ChatGPT Plus supports Codex tasks within plan allowance. Multiple subagents use more allowance. OpenAI API/Agents API is billed separately. AWS credits eligibility and costs must be verified before deployment.
