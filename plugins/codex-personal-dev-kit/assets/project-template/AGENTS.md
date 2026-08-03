# {{PROJECT_NAME}} Project Instructions

This file contains only project-specific facts. The detailed personal development system lives at `{{WORKSPACE_AGENTS_PATH}}` and is loaded through the user's short global instructions.

## Project Boundary

- Treat this folder as one independent long-term project and Git repository.
- Always read the explicitly referenced mother-folder `AGENTS.md` to restore the applicable development system. Apart from that rules file, do not read or edit sibling projects, the mother folder, archives, or global Codex files unless the user explicitly asks.
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
- Before edits, use the central Dev Kit current-change checklist or safe-development script when available. The project does not install lifecycle Hooks; run explicit checks through the current task and preserve Codex-native agents, tasks, browser tools, and other built-in capabilities.
- Routine versions stay on the current branch. Every verified change gets a local recovery point before completion.
- Ordinary checkpoints are not product versions. When the user accepts a tested milestone, update `docs/VERSIONS.md`, create the final checkpoint, then use guarded `version` to add an immutable semantic tag such as `v1.2.0`; never create a version branch. If the user explicitly authorizes an exact remote, current branch, and formal tags, use guarded `publish` rather than asking the user to run Git.
- If the user cannot remember a version number, compare the capability descriptions in `docs/VERSIONS.md` and local tags. Restore a confirmed tag through the guarded `restore-version` command, which preserves newer history and the complete version index.
- Use one source writer per checkout. Parallel writers require separate Worktrees and explicit ownership.
- Use guarded `sync` for an authorized remote/current-branch fast-forward, guarded `integrate` for one linear local source branch, guarded `unstage` for exact current-contract paths, and guarded `remove-worktree` only after proving no files or unique commits need recovery.
- Keep project documents current and concise. Never add chat transcripts, hidden reasoning, raw logs, daily journals, or permanent per-task reports.
- Before the first feature checkpoint, replace every `Not yet confirmed` placeholder in `docs/PROJECT.md`, `docs/FEATURES.md`, `docs/ARCHITECTURE.md`, `docs/STATUS.md`, and Verified Commands with confirmed facts. Active Feature rows need a machine-readable verification marker such as `test:tests/example.test.js` or `suite:unit`.
- Never use raw/force Git, unauthorized remote changes, auto-integrate divergent histories, Release, deploy, package publish, history rewrite, remote-ref deletion, or discard unconfirmed work.

## Definition Of Done

The requested behavior works; affected and critical existing features were rechecked; relevant verification passed; the final diff was reviewed; a matching local recovery point exists; and current project facts changed only where necessary.
