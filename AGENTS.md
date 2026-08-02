# Codex Dev Kit Instructions

This repository builds a beginner-first Codex development assistant. The user communicates in plain language; internal Git, Skills, Goals, subagents, tests, explicit safety scripts, and continuity should stay automatic unless troubleshooting requires detail.

## Workflow

- Treat `docs/FEATURES.md`, tests, Git, `docs/DESIGN.md`, and short current docs as the source of truth.
- Use the local `skill-creator` guidance when changing standalone Skills. Do not create or maintain a Dev Kit Plugin package.
- Preserve the single user entry skill and keep supporting Skills concise with progressive references.
- Protect accepted Dev Kit features before edits. Keep one source writer per checkout and use read-only subagents for independent exploration, review, and verification.
- Treat Codex native subagents, user-visible tasks, Worktrees, the review pane, and Appshots as product capabilities to orchestrate, never as surfaces for this Dev Kit to replace or intercept.
- Routine sequential development stays on the current branch. Every verified change must use the bundled guard-managed checkpoint before completion; branches are only for real isolation.
- Do not modify or install into `~/.codex`, publish, push, release, or deploy unless the user explicitly asks.
- Do not encode file-line thresholds. Judge structure by responsibility, coupling, testability, and change impact.
- When debugging Skill availability, use the exact file locator exposed by the current task and never invent a `.system` prefix for standalone Skills; the runtime resolver is `scripts/resolve-skill.ps1`.

## Verification

- Full validation: `powershell -NoProfile -ExecutionPolicy Bypass -File .\plugins\codex-personal-dev-kit\scripts\validate-kit.ps1`
- Unit tests: `python -m unittest discover -s tests -p test_*.py -v`
- PowerShell parsing: parse every `*.ps1` with `System.Management.Automation.Language.Parser`.
- Safety policy: use the bundled explicit guard scripts and the project's normal Codex approval/sandbox settings; do not add a custom Rules layer.

## Done

The requested behavior is implemented, affected feature IDs are rechecked, official validators and risk-based tests pass, the final diff is reviewed, current docs are concise, and no global install or remote action occurred without permission.
