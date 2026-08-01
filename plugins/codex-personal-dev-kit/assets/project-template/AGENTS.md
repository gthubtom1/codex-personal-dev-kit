# Project Instructions

## Purpose

This repository is a long-term project managed with Codex Personal Dev Kit. Treat code, tests, Git, and the current documents under `docs/` as the source of truth.

## Workflow

- At every task start, read this file plus `docs/PROJECT.md`, `docs/FEATURES.md`, and `docs/STATUS.md`. Read architecture, ADRs, roadmap, and runbook only when the request touches them.
- Route ordinary build, change, fix, and continue requests through `$codex-development-assistant` even when the user only describes the desired result.
- Use `$prepare-codex-goal` for fuzzy, multi-step, architectural, or high-risk requests.
- Create a persistent Goal when the user asks Codex to finish a multi-step outcome, keep working until usable, or run unattended.
- Use `$orchestrate-codex-team` only when independent work benefits from Codex's native collaboration subagents or Worktrees. A subagent stays inside the current task; never replace it with a user-visible task, chat, fork, message, or Handoff.
- Use `$codex-safe-development` for implementation and `$manage-project-continuity` at task boundaries.
- Analyze adjacent requirements broadly, but implement only the accepted scope.
- Before changing an existing project, open the bundled current change guard with the intended feature IDs and adjacent behaviors to verify. Use guard-managed explicit staging and recorded verification commands; never use broad `git add` or a chained commit command.
- Keep one writer per checkout. Parallel writers require separate Git Worktrees and branches.
- Preserve existing user changes. Stage only files owned by the current task.
- For complex work, keep at most one ignored `.codex/active-plan.md`; delete it when the task ends. Never accumulate plan versions, chat transcripts, or chronological development logs.
- Local branches and verified checkpoint commits are allowed automatically.
- Never automatically push, pull, merge, rebase, tag, release, deploy, publish, run production migrations, rewrite history, or discard unconfirmed work.

## Repository Map

- Product definition: `docs/PROJECT.md`
- Current user-visible behavior: `docs/FEATURES.md` plus linked `docs/features/` domain maps
- Current architecture: `docs/ARCHITECTURE.md`
- Current milestone and next action: `docs/STATUS.md`
- Near-term milestones: `docs/ROADMAP.md`
- Operations and recovery: `docs/RUNBOOK.md`
- Major decisions: `docs/adr/`

## Commands

- Install: not confirmed; discover from project files before running.
- Start: not confirmed; record the verified command here.
- Test: not confirmed; record the verified command here.
- Lint/type/build: not confirmed; record only commands that actually exist.

## Definition Of Done

The requested behavior is implemented, the current change guard is verified, existing affected and critical features have been rechecked, risk-based checks have run, the diff has been reviewed, remaining risk is stated, and durable project documents are updated only where facts changed.
