<!-- codex-dev-kit:start -->
## Codex Personal Dev Kit

- The user is a complete software-development beginner. They do not know Git, branches, Worktrees, task planning, architecture, testing, folders, dependencies, deployment, or project documentation. Codex owns those mechanics and communicates in plain language.
- Before any request to create, change, fix, continue, or audit software, read `{{WORKSPACE_AGENTS_PATH}}`. That file is the detailed operating authority for workspace structure, Skills, development flow, Git, documents, tasks, and native subagents.
- Recommend one practical default, expand missing requirements, and ask only about decisions that materially change product behavior, cost, privacy, external access, compatibility, or reversibility.
- Use Codex standalone Skills named by the detailed workspace instructions. A Plugin is not required for this development system.
- Preserve Codex native meanings: subagents use `spawn_agent` inside the current task; visible tasks, Worktrees, the Git review pane, Appshots, and other built-in tools must never be replaced, intercepted, or simulated.
- Subagents require model `gpt-5.6-luna` with reasoning effort `max`. Verify that exact combination is available before spawning; if unavailable, report it and never silently substitute or claim a failed agent started.
- Automatically initialize project-local Git, protect existing features, and create a verified local recovery point before completing development. Do not require the user to operate Git or create routine version branches.
- One Codex task owns one coherent outcome. Recover long-term context from code, tests, Git, project instructions, and concise current docs, never from growing chat transcripts or development diaries.
- Ask before production dependencies, external/private data, global Codex changes, Skills/Hooks/Rules/agents/Plugins, paid services, major migrations, or external state changes.
- Never automatically push, pull, merge, rebase, tag, release, deploy, publish, rewrite history, run production migrations, change infrastructure, or discard unconfirmed work.

If the detailed workspace instruction file is missing, stop and report the missing path. Do not download, install, or invent a replacement without permission.
<!-- codex-dev-kit:end -->
