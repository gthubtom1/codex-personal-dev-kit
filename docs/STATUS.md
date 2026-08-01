# Current Status

## Milestone

The Codex Personal Dev Kit now uses a two-layer instruction model and standalone Codex Skills as the primary runtime. It is designed for a complete beginner while preserving Codex native subagents, tasks, Worktrees, Git UI, Appshots, configuration, and Hooks.

## Working State

- Source candidate: `codex-personal-dev-kit` version `0.1.0+codex.20260801171741` on `main`, one writer, one Worktree.
- Mother folder: `D:\开发\AGENTS.md` contains the detailed system and `D:\开发\.codex\config.toml` enables native multi-agent defaults with `gpt-5.6-luna` and reasoning effort `max`.
- Global installation: the standalone short `~/.codex/AGENTS.md`, Skills, runtime, and Rules have not been installed in this task because global Codex changes require explicit permission.
- Legacy local state: `codex plugin list` does not currently list Codex Personal Dev Kit as installed, no global Dev Kit Hook is present, but four old `codex-kit-*.toml` files and legacy `source.json` metadata remain under `~/.codex` until an approved migration.

## Verified

- Current official Codex behavior was checked for global/project `AGENTS.md` discovery, `[agents]` subagent defaults, `gpt-5.6-luna`, `max`, multi-agent settings, and Hook matching behavior.
- Seven standalone Skills pass the official Skill validator; the optional Skills-only Plugin passes the official Plugin validator and contains no lifecycle Hook, custom agent, MCP, or App surface.
- Fifty-three automated tests cover feature regression contracts, native apply_patch/Edit/Write mutation enforcement, exact verified checkpoints, reversible rollback, dirty-user-change isolation, bounded context recovery, generic document-bloat audits, dangerous command protection, standalone install/update/diagnosis, installed-versus-not-installed Plugin status parsing, metadata-restored custom workspace roots, all-Marketplace Plugin-only legacy detection, damaged managed-marker rejection before legacy switching, exact-versus-ambiguous Hook migration handling with backups, prepare-before-switch migration ordering, central-runtime Hook pinning, project creation, secret-aware first baselines, and native-subagent versus visible-task boundaries.
- PowerShell parsing, Python/JSON/TOML structural checks, unresolved placeholder checks, and Codex Rules parser checks pass.
- Native current-task subagents using the current `gpt-5.6-luna/max` selection completed multiple read-only review passes. Their findings drove the legacy migration gate, stronger secret and large-text checks, exact Hook recognition, path templating, native Edit/Write enforcement, exact Luna/max orchestration policy, all-Marketplace Plugin detection, selective mixed-Hook cleanup, central-runtime Hook pinning, metadata-restored updates, README correction, and this status refresh. All reported P1/P2 findings were implemented and covered by the final verification recorded in this task.

## Current Limitations

- Local Git recovery protects work on this machine but is not an off-device backup.
- Secret detection covers common named files, quoted JSON/YAML or assignment-style keys, common provider tokens, and bounded large-text handling. It remains intentionally conservative and does not replace a dedicated security scanner for release-critical projects.
- The current Codex task began before the new mother-folder config was loaded. A new task is required for the definitive native-subagent runtime test after standalone installation.

## Next Action

After the verified local source checkpoint, obtain explicit permission to run the standalone installer with legacy migration, then start a new Codex task and run diagnosis plus a native `gpt-5.6-luna/max` subagent smoke test.
