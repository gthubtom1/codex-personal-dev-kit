# Roadmap

## Current Milestone

- Prepare a clean MIT-licensed v0.2.6 checkout whose canonical portable template exactly reconstructs the complete Chinese mother-folder rules.
- Detect local/template AGENTS drift without overwriting or exposing custom rules, while retaining blank-install and idempotence guarantees.

## Next Milestone

- v0.2.7: land the 21-dimension release-review gate, research-by-default routing, the read-only `next_step.py` entry, merged third-party review fixes, and the five small protections (per-checkpoint secret rescan, lockfile-drift gate, large-file warning, dependency-audit and disk-usage audit items); dogfood the release review on the kit itself.
- Add focused regression tests for any real failure found during project use.
- Keep Skills, global instructions, and project documents concise as Codex capabilities evolve.

## v0.3 Theme: Multi-Host Adaptation (Codex / Cursor / Claude)

- Keep one source tree; the enforcement core (guard scripts, tests, project templates, both AGENTS layers) is already host-neutral Python + Git + Markdown.
- Teach the installer a host parameter that targets each agent's skills directory (`~/.codex/skills`, `~/.cursor/skills`, `~/.claude/skills`) instead of assuming the Codex Home.
- Replace `$skill-name` dispatch wording with host-neutral routing ("read and follow the named SKILL.md"), and describe subagents as "the current host's native subagent capability, or sequential main-agent execution when absent".
- Until then, the README self-adaptation guide is the supported path for non-Codex agents: the user hands the repository link to their agent and the agent adapts by following that section; the Cursor path is already exercised in real use, the Claude path is documented but not yet verified.

## Later

- Add separately tested guarded upgrade/downgrade, divergent-history conflict resolution, and provider-specific release/deployment flows only where real use proves they are needed.
- Configure separate private remotes for each long-term project when the user requests off-device project backup; the public Dev Kit repository does not contain project source or data.
- Preserve license and third-party notices in future formal versions and recheck attribution when external source code is ever vendored or adapted.
