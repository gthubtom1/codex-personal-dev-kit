# {{PROJECT_NAME}} Project Instructions

This file contains only project-specific facts. The detailed personal development system lives at `{{WORKSPACE_AGENTS_PATH}}` and is loaded through the user's short global instructions.

## Project Boundary

- Treat this folder as one independent long-term project and Git repository.
- Do not read or edit sibling projects, the mother folder, archives, or global Codex files unless the user explicitly asks.
- Preserve existing user changes and generated/local files.
- Project-specific instructions closer to a subdirectory may add narrower rules but cannot weaken safety boundaries.

## Required Current Facts

At every task start read:

- Product and scope: `docs/PROJECT.md`
- Current user-visible features: `docs/FEATURES.md` plus linked `docs/features/`
- Current milestone, risk, and next action: `docs/STATUS.md`

Read only when relevant:

- Architecture and module boundaries: `docs/ARCHITECTURE.md`
- Near-term milestones: `docs/ROADMAP.md`
- Operations and recovery: `docs/RUNBOOK.md`
- Major decisions: `docs/adr/`

## Verified Commands

Replace only after the command has actually been discovered and run successfully.

- Install: not confirmed.
- Start: not confirmed.
- Test: not confirmed.
- Lint/type/build: not confirmed.

## Project Rules

- Record accepted capabilities with stable feature IDs and complete UI/API/background/persistence wiring.
- Before edits, use the central Dev Kit current change guard. Project-local `.codex/hooks.json` enforces the guard for Shell and file edits only.
- Routine versions stay on the current branch. Every verified change gets a local recovery point before completion.
- Use one source writer per checkout. Parallel writers require separate Worktrees and explicit ownership.
- Keep project documents current and concise. Never add chat transcripts, hidden reasoning, raw logs, daily journals, or permanent per-task reports.
- Never automatically push, merge, release, deploy, publish, rewrite history, or discard unconfirmed work.

## Definition Of Done

The requested behavior works; affected and critical existing features were rechecked; relevant verification passed; the final diff was reviewed; a matching local recovery point exists; and current project facts changed only where necessary.
