# Current Status

## Milestone

The Codex Personal Dev Kit now uses the intended two-layer `AGENTS.md` model and standalone Codex Skills. The old Plugin, Marketplace manifest, project lifecycle Hook, and custom Rules packaging are removed from the source tree. Codex native subagents, tasks, Worktrees, Git UI, Appshots, and configuration remain untouched. The isolated zero-based forward test has also exercised the full guarded loop and the system has been hardened against stale STATUS content, ordinary-feature regression gaps, fabricated verification, wrong rollback targets, stuck-agent ambiguity, and contradictory model-precedence wording.

## Working State

- Source candidate: `codex-personal-dev-kit` version `0.1.0` on the current local branch.
- Mother folder: `D:\开发\AGENTS.md` contains the detailed system; workspace and project templates keep native multi-agent enabled, default Luna/max subagents, six concurrent slots, and no main-model lock. Model precedence is explicit user roster > project configuration > system default; runtime model availability is still checked by Codex before spawning.
- Standalone installation writes the short global `AGENTS.md`, seven Skills, central explicit safety scripts, and project/workspace templates. It does not install a Plugin, lifecycle Hook, custom Agent, or Rules file.
- Legacy Plugin, custom-agent, and Dev Kit Hook detection remains only as an explicit migration/diagnostic path; it is not a runtime dependency.

## Verified

- Seven standalone Skills pass the official Skill validator.
- 64 unit tests cover feature contracts, meaningful STATUS freshness, all-active regression coverage, native edit/write guard behavior, exact checkpoints, reversible rollback, dirty-user-change isolation, bounded context recovery, document-bloat audits, dangerous command protection, standalone install/update/diagnosis, legacy-state detection, project creation, secret-aware first baselines, template-placeholder gates, domain/ADR document budgets, and native-subagent boundaries.
- PowerShell parsing, Python/JSON/TOML structural checks, unresolved placeholder checks, and the no-obsolete-artifact check pass after the cleanup is completed.
- Native subagent policy defaults to Luna/max, supports multiple parallel agents and explicit Sol/Luna rosters at max; roster ledger, slot calculation, 5-10-5 minute timeout handling, one recorded long-task extension, explicit user > project > system precedence, and no custom Agent or visible-task replacement are shipped. Disabled `[agents].enabled` or `[features].multi_agent` gates are now diagnosed and reported without being overridden. The current tool schema did not expose Luna, so this environment has not been claimed as a successful real Luna spawn.
- Existing project and workspace Codex configs receive the native agent defaults in place while preserving any top-level main-model choice; explicit model overrides use the required fork-depth parameter.

## Current Limitations

- Explicit safety scripts depend on the Skills following the workflow; there is intentionally no lifecycle Hook that can alter Codex native tool behavior.
- Local Git recovery protects work on this machine but is not an off-device backup.
- Explicit global Codex settings are outside Dev Kit ownership. The diagnostic now warns about known plaintext bearer/API/secret keys without printing values; the current host still requires user-led credential rotation/removal and review of any global main-model default.
- Secret detection covers common named files, provider tokens, assignment-style keys, and bounded large-text handling. It is not a dedicated release security scanner.
- The current Codex task began before any global installation. A new task is required after an approved standalone install so Codex reloads the short global instructions and Skills. A real Luna/max spawn remains an environment-dependent runtime check, not something this repository can fake.

## Next Action

After an approved standalone install, open a new Codex task in a real project folder and verify the beginner-facing flow there; do not migrate unrelated files under the user's global `~/.codex` directory automatically.
