# Current Status

## Milestone

The beginner-first Codex Personal Dev Kit is hardened against fabricated verification, mixed checkpoints, feature-map splits, context loss, unsafe global installs, local Marketplace drift, and accidental replacement of native subagents with user-visible tasks.

## Working State

- Branch/worktree: `main`, one writer, one Worktree.
- Source candidate: `codex-personal-dev-kit` version `0.1.0+codex.20260801171741` in this repository.
- Installed Plugin: version `0.1.0+codex.20260801163726` from local Marketplace `codex-dev-kit`; it remains active until the verified candidate is explicitly reinstalled and a new Codex task starts.
- Global profile: managed `AGENTS.md` block, four specialist agents, safety Rules, and reference fragments installed under `C:\Users\Administrator\.codex`.
- Global backup: the previous `AGENTS.md` is under `C:\Users\Administrator\.codex\backups\codex-dev-kit\20260801-151604`.

## Verified

- Seven Skills pass the official Skill validator.
- The Plugin passes the official Plugin validator.
- Thirty-three automated tests cover exact-tree/content verification, explicit staging and dirty-baseline isolation, mid-task feature-scope promotion, composite/auto-staging commit rejection, new and split feature maps, bounded startup/resume/compact/clear recovery, uncommitted-contract preservation, generic document-bloat audits, command safety, local/Git Marketplace handling, HEAD/worktree/version diagnostics, project creation, preservation, idempotence, and the native-subagent versus visible-task boundary.
- Python, JSON, TOML, and PowerShell syntax checks pass.
- The Rules parser checks pass through the runnable Codex Desktop CLI resolved from its local bin directory.
- The real `D:\开发` mother folder was initialized without a Git repository.
- `codex plugin list` reports the local Plugin installed and enabled.
- The installed cached Hook generates a capped recovery packet with a reserved `Next Action`, aggregated FEATURES routing, current change scope, Git state, and latest checkpoint.
- Installed Rules and Hook protection reject remote/destructive actions and automatic global installs; dependency changes require explicit review.
- Local source diagnosis checks Marketplace identity, pinned HEAD, clean worktree, source/marker/cache/active Plugin version, and enabled state.
- Orchestration routing now requires native collaboration `spawn_agent` for subagents and explicitly forbids `create_thread`, `fork_thread`, cross-task messages, or Handoff as substitutes.

## Current Limitations

- Codex Desktop may ask the user to trust the newly installed Plugin Hooks the first time they run.
- The current Codex task loaded the previous Plugin instructions. The routing fix can only be exercised after explicit reinstall and a new task.
- No Git remote is configured, so the local checkpoint is recoverable on this machine but is not an off-device backup.

## Next Action

After the verified local checkpoint, obtain permission to reinstall version `0.1.0+codex.20260801171741`, run diagnostics, and start a new Codex task for a real native-subagent forward test. Open `D:\开发` only to create/manage projects; open `D:\开发\projects\<project>` directly to develop an existing project.
