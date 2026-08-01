<!-- codex-dev-kit:start -->
## Codex Personal Dev Kit

- Assume the user is new to software development. Recommend a default, explain material choices in plain language, and do not require the user to know technical terminology.
- Analyze adjacent requirements broadly, but implement only the accepted scope. Classify discoveries as required now, recommended, later, or excluded.
- For fuzzy or high-risk work, use `$prepare-codex-goal` before editing. Use the other `codex-personal-dev-kit` skills for onboarding, orchestration, development, continuity, and audits.
- In a managed existing project, use the bundled current change guard before edits and complete its feature regression evidence before a checkpoint or final answer.
- One Codex task owns one coherent outcome. In a managed project, always restore `PROJECT`, `FEATURES`, and `STATUS`; load architecture and ADRs only when relevant. Start a new task when the outcome, branch, deliverable, or major module changes. Keep durable facts in code, tests, Git, `AGENTS.md`, and concise current docs, not old chat transcripts.
- Use subagents for bounded, independent exploration, documentation checks, tests, or review. Keep one writer per checkout. Use separate Git Worktrees and branches for parallel writers.
- You may automatically create local branches and verified checkpoint commits. Preserve user changes and stage only task-owned files.
- Never automatically push, pull, merge, rebase, tag, release, deploy, publish packages, run production migrations, apply infrastructure, rewrite Git history, or discard unconfirmed work.
- Ask before adding production dependencies, accessing data outside the selected project, changing global Codex settings, or installing/updating plugins, hooks, rules, agents, and global tools.

If the Dev Kit skills are missing, read `$CODEX_HOME/codex-dev-kit/source.json`. Only propose installation when it contains a fixed Git tag or commit. Show the exact `codex plugin marketplace add <source> --ref <fixed-ref>` and `codex plugin add codex-personal-dev-kit@<marketplace-name>` commands and obtain permission before running them. Never install from an unpinned `main` branch or execute a remote script. After plugin install or update, start a new Codex task so skills and hooks reload.
<!-- codex-dev-kit:end -->
