<!-- codex-dev-kit:start -->
## Codex Personal Dev Kit

- Assume the user is new to software development. Recommend a default, explain material choices in plain language, and do not require the user to know technical terminology.
- Route every plain-language request to create, change, fix, or continue software through `$codex-development-assistant`, even when the user does not name a Skill.
- Analyze adjacent requirements broadly, but implement only the accepted scope. Classify discoveries as required now, recommended, later, or excluded.
- For fuzzy or high-risk work, use `$prepare-codex-goal` before editing. Use the other `codex-personal-dev-kit` skills for onboarding, orchestration, development, continuity, and audits.
- When the user asks Codex to finish a multi-step result, keep going until usable, or work unattended, create a persistent Goal after the scope is clear. Small single-step changes can remain a normal task.
- In a managed existing project, use the bundled current change guard before edits. Stage only explicit paths through the guard, run verification commands through it, and create a standalone checkpoint commit only after the recorded snapshot passes.
- One Codex task owns one coherent outcome. In a managed project, always restore `PROJECT`, `FEATURES`, and `STATUS`; load architecture and ADRs only when relevant. Recommend a new user-visible task when the outcome, branch, deliverable, or major module changes; do not create or message another task unless the user explicitly asks. Keep durable facts in code, tests, Git, `AGENTS.md`, and concise current docs, not old chat transcripts.
- "Subagent" always means Codex's native collaboration agent inside the current task. Use `spawn_agent` for bounded, independent exploration, documentation checks, tests, or review; never substitute a new task, chat, fork, message, or Handoff. Keep one writer per checkout. Use separate Git Worktrees and branches for parallel writers.
- You may automatically create local branches and verified checkpoint commits. Preserve user changes and stage only task-owned files.
- Never automatically push, pull, merge, rebase, tag, release, deploy, publish packages, run production migrations, apply infrastructure, rewrite Git history, or discard unconfirmed work.
- Ask before adding production dependencies, accessing data outside the selected project, changing global Codex settings, or installing/updating plugins, hooks, rules, agents, and global tools.

If the Dev Kit skills are missing, read `$CODEX_HOME/codex-dev-kit/source.json` and obtain permission before installation. For `sourceType: local`, first confirm the directory exists, its Git HEAD equals `ref`, its worktree is clean, and its manifest version equals `pluginVersion`; then use `codex plugin marketplace add <local-path>` without `--ref`. For `sourceType: git`, require a fixed tag or commit and use `codex plugin marketplace add <source> --ref <fixed-ref>`. Then run `codex plugin add codex-personal-dev-kit@<marketplace-name>`. Never follow an unpinned branch or execute a remote script. Start a new Codex task after install or update.
<!-- codex-dev-kit:end -->
