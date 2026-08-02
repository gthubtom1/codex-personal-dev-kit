# Current Status

## Milestone

The Codex Personal Dev Kit 0.2.0 is prepared as a portable GitHub distribution. A fixed clean checkout contains both `AGENTS.md` templates, nine standalone Skills, the central runtime, project/workspace templates, tests, a beginner restore guide, formal-version recovery, and diagnostics without shipping the old Plugin/Hook/custom-agent runtime.

## Working State

- Source candidate: `codex-personal-dev-kit` version `0.2.0` on the current local branch.
- Mother folder: `D:\开发\AGENTS.md` contains the detailed system. Workspace and project templates do not write any native subagent model, reasoning, concurrency, enablement, or interruption setting; Codex official defaults and user-owned configuration remain authoritative.
- Standalone installation writes the short global `AGENTS.md`, nine Skills, central explicit safety scripts, and project/workspace templates. It does not install a Plugin, lifecycle Hook, custom Agent, or Rules file.
- Installation records every fully managed Skill/runtime/template file and its SHA-256 hash in `managed-files.json`. Diagnosis detects missing or changed files; updates back up and remove only unchanged stale Dev Kit files while preserving user-modified stale files with a warning.
- Legacy Plugin, custom-agent, and Dev Kit Hook detection remains only as an explicit migration/diagnostic path; it is not a runtime dependency.
- Formal versions are recorded in `docs/VERSIONS.md`; the guard can mark the current verified checkpoint or safely backfill a verified ancestor during onboarding. Restoration creates a new checkpoint while preserving newer history, tags, and the complete index.
- Raw Git tag creation, deletion, movement, and overwrite remain blocked; explicitly read-only tag listing and verification are allowed for audits.
- The short global AGENTS template substitutes the selected Codex Home, so a different Windows username does not retain `C:\Users\Administrator` in installed Skill guidance.
- `docs/RESTORE.md` defines the supported new-computer path: fixed Git checkout, preview/apply installation, full Desktop restart, diagnostics, and separate project backups.

## Verified

- Nine standalone Skills pass the official Skill validator.
- The complete local regression suite passes; the current suite contains 88 tests.
- The unit suite covers feature contracts, meaningful STATUS freshness, all-active regression coverage, native edit/write guard behavior, exact checkpoints, reversible rollback, dirty-user-change isolation, bounded context recovery, document-bloat audits, dangerous command protection, standalone install/update/diagnosis, exact Skill path resolution, legacy-state detection, project creation, secret-aware first baselines, template-placeholder gates, domain/ADR document budgets, official-default native-subagent boundaries, task receipt confirmation, controlled external research/source reuse, named-project integration boundaries, bounded structural validation, and standalone validator layout detection.
- The documentation navigation audit checks local Markdown targets, GitHub-style heading anchors, external/code-fenced links, reachable durable documents, and bounded document budgets; the project template creates `docs/INDEX.md` and the workspace tests verify it.
- A real cross-task failure was reproduced in two layers: older tasks had an 18-item cached Skill catalog before installation, and a later task guessed the invalid `.system\prepare-codex-goal` path even though the Skill was listed. The standalone instructions now require exact file locators, provide `resolve-skill.ps1`, and explicitly require a full Codex Desktop restart before treating a new task's Skill catalog as refreshed.
- New-project onboarding now resolves `bootstrap-project.ps1` through three bounded local candidates: the standalone runtime, its pinned `source.json`, then the explicitly referenced mother-folder checkout. It no longer tells an agent to infer an ambiguous “Dev Kit root”, recursively search the machine, or download a replacement.
- PowerShell parsing, Python/JSON/TOML structural checks, unresolved placeholder checks, and the no-obsolete-artifact check pass after the cleanup is completed.
- Native subagent policy now delegates completely to Codex. Managed configuration contains no `[agents]` block or `multi_agent` value, and orchestration calls the native tool without model, reasoning or concurrency overrides. A started child must confirm that its task payload is readable; unavailable tools and failed starts are reported without fallback mechanisms.
- Existing user-owned subagent settings are left untouched. Dev Kit bootstraps merge only the general Goal feature into existing project configuration and do not inspect or migrate prior model choices.
- `research-and-reuse` now routes current/unknown/high-risk/common-capability work through project-first official/Web/GitHub research, license/security/compatibility evaluation, permission gates, and bounded durable records. `integrate-codex-projects` keeps the open project as the only default writer, reads only explicitly named sources, and integrates capabilities through small tested interfaces instead of folder or Git-history merging.
- The structural validator now accepts equivalent Chinese/English Skill-path wording and caps its full unit-test subprocess at 300 seconds (override only through `CODEX_DEV_KIT_TEST_TIMEOUT_SECONDS`), so unattended validation reports a timeout instead of waiting forever.
- The PowerShell validator now detects whether it is running from the source checkout or the installed standalone runtime; standalone validation delegates to the pinned local source, separately checks the nine installed Skill directories, and reports the actual source/runtime path in its success line.

## Current Limitations

- Explicit safety scripts depend on the Skills following the workflow; there is intentionally no lifecycle Hook that can alter Codex native tool behavior.
- Local Git recovery protects work on this machine but is not an off-device backup.
- Explicit global Codex settings are outside Dev Kit ownership. The diagnostic now warns about known plaintext bearer/API/secret keys without printing values; the current host still requires user-led credential rotation/removal and review of any global main-model default.
- Secret detection covers common named files, provider tokens, assignment-style keys, and bounded large-text handling. It is not a dedicated release security scanner.
- Markdown anchor checking intentionally approximates common GitHub-style slugs; unusual renderer-specific extensions may still require manual review.
- The current Codex task began before any future standalone update. A new task is required after an approved install so Codex reloads the short global instructions and Skills. Exact cross-model availability remains task- and desktop-version-dependent and cannot be guaranteed by repository configuration.
- A public GitHub repository still needs an explicit license decision. Until the user chooses redistribution terms, private GitHub is the safe default.

## Next Action

Finish distribution validation and the guarded v0.2.0 local version, remove ignored test output, then let the user choose a private or public GitHub repository before any remote creation or push.
