# Codex Dev Kit Instructions

This repository builds a beginner-first Codex development assistant. The user communicates in plain language; internal Git, Skills, Goals, subagents, Hooks, Rules, tests, and continuity should stay automatic unless troubleshooting requires detail.

## Workflow

- Treat `docs/FEATURES.md`, tests, Git, `docs/DESIGN.md`, and short current docs as the source of truth.
- Use the local `plugin-creator` and `skill-creator` guidance when changing Plugin or Skill structure.
- Preserve the single user entry skill and keep supporting Skills concise with progressive references.
- Protect accepted Dev Kit features before edits. Keep one source writer per checkout and use read-only subagents for independent exploration, review, and verification.
- Do not modify or install into `~/.codex`, publish, push, release, or deploy unless the user explicitly asks.
- Do not encode file-line thresholds. Judge structure by responsibility, coupling, testability, and change impact.

## Verification

- Full validation: `powershell -NoProfile -ExecutionPolicy Bypass -File .\plugins\codex-personal-dev-kit\scripts\validate-kit.ps1`
- Unit tests: `python -m unittest discover -s tests -p test_*.py -v`
- PowerShell parsing: parse every `*.ps1` with `System.Management.Automation.Language.Parser`.
- Rules: use `codex execpolicy check` when the local Codex CLI is executable; otherwise state the limitation.

## Done

The requested behavior is implemented, affected feature IDs are rechecked, official validators and risk-based tests pass, the final diff is reviewed, current docs are concise, and no global install or remote action occurred without permission.
