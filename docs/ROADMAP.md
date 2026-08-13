# Roadmap

## Current Milestone

- v0.2.10 + v0.2.11 shipped: worktree-outside enforcement on Cursor (`.cursor/hooks.json` `beforeShellExecution` guard), `.vscode` watcher-exclude template, a HIGH classifier fix (newline-hidden destructive commands + nested `$()`), and the host-adaptation docs + a 10-agent audit follow-up.
- Next up (v0.3): the multi-host installer AND existing-project migration — retro-add the hook + watcher-exclude to already-onboarded projects and relocate their in-workspace worktrees. This is the outstanding gap; v0.2.10/v0.2.11 only cover newly-created projects on Cursor.

## Next Milestone

- Add focused regression tests for any real failure found during project use (the v0.2.10 guards each carry a red-when-broken test).
- Ship the v0.3 multi-host installer (below) so the worktree hard-guard and short-block conventions are placed into each host's system-rule location automatically instead of by manual self-adaptation.
- Keep Skills, global instructions, and project documents concise as host capabilities evolve.

## v0.3 Theme: Multi-Host Adaptation (Codex / Cursor / Claude)

- Keep one source tree; the enforcement core (guard scripts, tests, project templates, both AGENTS layers) is already host-neutral Python + Git + Markdown.
- Teach the installer a host parameter that targets each agent's skills directory (`~/.codex/skills`, `~/.cursor/skills`, `~/.claude/skills`) instead of assuming the Codex Home.
- Replace `$skill-name` dispatch wording with host-neutral routing ("read and follow the named SKILL.md"), and describe subagents as "the current host's native subagent capability, or sequential main-agent execution when absent".
- Until then, the README self-adaptation guide is the supported path for non-Codex agents: the user hands the repository link to their agent and the agent adapts by following that section; the Cursor path is already exercised in real use, the Claude path is documented but not yet verified.

## Later

- Add separately tested guarded upgrade/downgrade, divergent-history conflict resolution, and provider-specific release/deployment flows only where real use proves they are needed.
- Configure separate private remotes for each long-term project when the user requests off-device project backup; the public Dev Kit repository does not contain project source or data.
- Preserve license and third-party notices in future formal versions and recheck attribution when external source code is ever vendored or adapted.
