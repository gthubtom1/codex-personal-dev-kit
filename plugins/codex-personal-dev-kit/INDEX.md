# Codex Personal Dev Kit Index

This is the durable entry point for beginner-first software development. It coordinates Codex's native Skills, subagents, tasks, Worktrees, Git UI, Hooks, and project files. It does not replace any of those capabilities.

## User Contract

- The user describes the desired result in ordinary language and should not need to learn Git, branches, Worktrees, Skills, or test strategy first.
- Recommend one sensible default. Ask only about choices that materially change product behavior, cost, privacy, external access, or reversibility.
- Expand adjacent requirements broadly, but classify them as required now, recommended, later, or excluded before implementation.
- Unless the user asks only for analysis, continue through implementation, verification, independent review, and a local recovery point.

## Location Routing

- Mother folder: create, list, or archive independent projects only. New projects live under `projects/<name>/` and each has its own Git repository.
- Project folder: restore that project's current facts and work only inside it. Never scan sibling projects unless the user asks for a portfolio audit.
- After creating a project, the user opens that project folder in Codex and starts a new task so its local instructions and Hooks load.

## Native Skill Routing

Use the installed standalone Skills directly:

- `$codex-development-assistant`: default entry for create, change, fix, continue, or improve requests.
- `$onboard-codex-project`: prepare a new or existing project, Git baseline, folders, commands, and concise facts.
- `$prepare-codex-goal`: expand fuzzy, architectural, multi-step, high-risk, or unattended work into a bounded Goal.
- `$orchestrate-codex-team`: use Codex native collaboration subagents for bounded independent work.
- `$codex-safe-development`: implement with feature protection, tests, review, and automatic local recovery points.
- `$manage-project-continuity`: restore or hand off concise current state across tasks and compaction.
- `$audit-codex-kit`: read-only health, workflow, documentation, Git, and regression audits.

## Native Capability Boundary

- `subagent` means the native current-task collaboration tool (`spawn_agent`, wait, message, follow-up, interrupt). Never create or fork a visible task to simulate one.
- A visible Codex task is long-lived user context. Create or manage one only when the user explicitly asks.
- Worktrees are isolated Git checkouts for real parallel writers or experiments, not version history and not subagents.
- The review pane remains Codex's native staged/unstaged/commit interface. Appshots remain visual app-state inputs, not code snapshots.
- Dev Kit Hooks match only shell commands and file edits. They must never match `Agent`, `spawn_agent`, task tools, browser tools, or other native collaboration paths.
- Custom agent TOML files are optional role presets, not required runtime components. The default installation does not add them.

## Git And Recovery

- Every project automatically gets its own local Git repository and first baseline after generated files, secrets, and local data are excluded.
- Routine sequential work stays on the current branch. Do not create `codex/v1`, `codex/v2`, or similar branches as save points.
- Before editing accepted behavior, open the current change guard and declare changed and adjacent feature IDs.
- Stage only task-owned paths through the guard, run real verification through it, complete the contract, then run its `checkpoint` command before ending.
- A verified change without a matching local checkpoint is unfinished. The Stop Hook must require Codex to continue and save it.
- When the user says "return to the previous version", protect unsaved work and use the guard's reversible rollback. It creates a new commit and keeps both versions recoverable.
- Never automatically push, pull, merge, rebase, tag, release, deploy, rewrite history, use `reset --hard`, or discard unconfirmed work.

## Project Facts

At task start read `AGENTS.md`, `docs/PROJECT.md`, `docs/FEATURES.md`, and `docs/STATUS.md`. Read architecture, ADRs, roadmap, and runbook only when relevant.

- Code and tests: executable truth.
- Git: recoverable history.
- `docs/FEATURES.md` plus `docs/features/`: current user-visible capabilities with stable IDs and verification paths.
- `docs/STATUS.md`: current milestone, verified state, risks, and one next action. Overwrite current facts; do not append a diary.
- `docs/ARCHITECTURE.md`: current module boundaries, interfaces, and data flow. Split by domain only when navigation requires it.
- `docs/adr/`: only major, difficult-to-reverse decisions.
- `.codex/current-change.json` and `.codex/active-plan.md`: ignored temporary state, never permanent history.

Do not store chat transcripts, hidden reasoning, raw logs, full diffs, daily journals, or one permanent specification per small task.

## Execution Boundaries

- Automatic: project-local reads and edits, existing tests/builds, native read-only subagents, local Git initialization/checkpoints, concise current docs.
- Ask first: production dependencies, paid services, project-external or private data, global Codex changes, plugin/tool installation, major architecture replacement, database schema migration.
- Never automatic: remote Git mutation, release/deploy/publish, production migrations, infrastructure changes, destructive history or data operations.

One Codex task owns one coherent outcome. Start a new task when the outcome, branch, deliverable, or major module changes; recover from concise project facts and Git rather than old chat transcripts.
