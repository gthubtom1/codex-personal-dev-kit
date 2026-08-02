# Current Status

## Milestone

The Codex Personal Dev Kit now uses the intended two-layer `AGENTS.md` model and standalone Codex Skills. The old Plugin, Marketplace manifest, project lifecycle Hook, and custom Rules packaging are removed from the source tree. Codex native subagents, tasks, Worktrees, Git UI, Appshots, and configuration remain untouched. The isolated zero-based forward test has exercised the full guarded loop, and the project templates now include a concise `docs/INDEX.md` navigation map with Markdown link and orphan-document audits.

## Working State

- Source candidate: `codex-personal-dev-kit` version `0.1.0` on the current local branch.
- Mother folder: `D:\开发\AGENTS.md` contains the detailed system; workspace and project templates keep native multi-agent enabled, default Luna/max subagents, six concurrent slots, and no main-model lock. Model precedence is explicit user roster > project configuration > system default; runtime model availability is still checked by Codex before spawning.
- Standalone installation writes the short global `AGENTS.md`, seven Skills, central explicit safety scripts, and project/workspace templates. It does not install a Plugin, lifecycle Hook, custom Agent, or Rules file.
- Legacy Plugin, custom-agent, and Dev Kit Hook detection remains only as an explicit migration/diagnostic path; it is not a runtime dependency.

## Verified

- Seven standalone Skills pass the official Skill validator.
- 68 unit tests cover feature contracts, meaningful STATUS freshness, all-active regression coverage, native edit/write guard behavior, exact checkpoints, reversible rollback, dirty-user-change isolation, bounded context recovery, document-bloat audits, dangerous command protection, standalone install/update/diagnosis, exact Skill path resolution, legacy-state detection, project creation, secret-aware first baselines, template-placeholder gates, domain/ADR document budgets, and native-subagent boundaries.
- The documentation navigation audit checks local Markdown targets, GitHub-style heading anchors, external/code-fenced links, reachable durable documents, and bounded document budgets; the project template creates `docs/INDEX.md` and the workspace tests verify it.
- A real cross-task failure was reproduced in two layers: older tasks had an 18-item cached Skill catalog before installation, and a later task guessed the invalid `.system\prepare-codex-goal` path even though the Skill was listed. The standalone instructions now require exact file locators, provide `resolve-skill.ps1`, and explicitly require a full Codex Desktop restart before treating a new task's Skill catalog as refreshed.
- PowerShell parsing, Python/JSON/TOML structural checks, unresolved placeholder checks, and the no-obsolete-artifact check pass after the cleanup is completed.
- Native subagent policy defaults to Luna/max, supports multiple parallel agents and explicit Sol/Luna rosters at max; roster ledger, slot calculation, 5-10-5 minute timeout handling, one recorded long-task extension, explicit user > project > system precedence, and no custom Agent or visible-task replacement are shipped. Disabled `[agents].enabled` or `[features].multi_agent` gates are now diagnosed and reported without being overridden. The current tool schema did not expose Luna, so this environment has not been claimed as a successful real Luna spawn.
- Existing project and workspace Codex configs receive the native agent defaults in place while preserving any top-level main-model choice; explicit model overrides use the required fork-depth parameter.

## Current Limitations

- Explicit safety scripts depend on the Skills following the workflow; there is intentionally no lifecycle Hook that can alter Codex native tool behavior.
- Local Git recovery protects work on this machine but is not an off-device backup.
- Explicit global Codex settings are outside Dev Kit ownership. The diagnostic now warns about known plaintext bearer/API/secret keys without printing values; the current host still requires user-led credential rotation/removal and review of any global main-model default.
- Secret detection covers common named files, provider tokens, assignment-style keys, and bounded large-text handling. It is not a dedicated release security scanner.
- Markdown anchor checking intentionally approximates common GitHub-style slugs; unusual renderer-specific extensions may still require manual review.
- The current Codex task began before any global installation. A new task is required after an approved standalone install so Codex reloads the short global instructions and Skills. A real Luna/max spawn remains an environment-dependent runtime check, not something this repository can fake.

## Next Action

Open a new Codex task in a real project folder and verify the beginner-facing flow with the new documentation index; do not migrate unrelated files under the user's global `~/.codex` directory automatically.
