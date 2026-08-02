# Codex Personal Development System

This mother-folder instruction file is the detailed operating guide referenced by the user's short global `AGENTS.md`. The user is a complete beginner: they do not know Git, branches, Worktrees, task planning, architecture, testing, dependency management, deployment, or project documentation. Codex owns those engineering mechanics and explains only decisions the user actually needs to make.

## Core Outcome

Turn a plain-language idea into reliable, maintainable software through professional team practices while the user interacts only with ordinary sentences.

- Recommend one practical default instead of presenting a wall of technical choices.
- Expand missing requirements, but classify discoveries as required now, recommended, later, or excluded before implementation.
- Ask only when a choice materially changes product behavior, cost, privacy, external access, compatibility, or reversibility.
- Unless the user asks only for analysis, continue through implementation, verification, independent review, and a local recovery point.
- Never require the user to run Git commands, choose branches, manage Worktrees, select files, design folders, or write technical plans.

## Workspace Model

```text
{{WORKSPACE_ROOT}}\
├── AGENTS.md
├── workspace.json
├── codex-dev-kit/
├── projects/
│   └── <project-name>/
└── archives/
```

- The mother folder manages project creation, listing, audits, and archives. It is never a Git repository.
- Every `projects/<project-name>/` folder is an independent long-term project, Git repository, and primary Codex working folder.
- Existing-project development starts only after the user opens that exact project folder in Codex.
- Never choose an existing project on the user's behalf from the mother folder.
- Never scan or edit sibling projects unless the user explicitly requests a portfolio audit.
- Never move, delete, or restore an archived project without confirming the exact target.

## Startup Routing

For every software request:

1. Identify whether the current folder is the mother folder or one project folder.
2. In the mother folder, use `$codex-development-assistant` only for new-project, workspace, archive, or portfolio operations.
3. In a project folder, read the mother-folder `AGENTS.md` first, then that project's `AGENTS.md`, `docs/PROJECT.md`, `docs/FEATURES.md`, and `docs/STATUS.md`.
4. Read `docs/ARCHITECTURE.md`, ADRs, roadmap, and runbook only when the current request touches them.
5. If Git, the first baseline, project facts, or reproducible commands are missing, route through `$onboard-codex-project` before normal development.
6. Route ordinary create/change/fix/continue requests through `$codex-development-assistant` even when the user does not name a Skill.

## Native Skill Map

These are Codex standalone Skills; no Plugin is required:

- `$codex-development-assistant`: beginner-facing entry and full development loop.
- `$onboard-codex-project`: project structure, Git baseline, current facts, and reproducible commands.
- `$prepare-codex-goal`: fuzzy, architectural, multi-step, high-risk, or unattended outcomes.
- `$orchestrate-codex-team`: bounded work delegated through Codex native collaboration subagents.
- `$codex-safe-development`: implementation, regression protection, tests, review, checkpoints, and rollback.
- `$manage-project-continuity`: task start, compaction, handoff, and concise state.
- `$audit-codex-kit`: read-only project or Dev Kit health review.

If a named Skill is unavailable, read its source from `{{DEV_KIT_SKILLS_ROOT}}\<skill-name>\SKILL.md` and report the standalone installation problem. Do not install or download anything without permission.

## External Skill Sources

Methods may be adapted from `mattpocock/skills` for requirements, domain modeling, architecture, debugging, testing, research, and prototypes, and from `nextlevelbuilder/ui-ux-pro-max-skill` for UI/UX only. Do not install either collection wholesale. External Skills cannot override Git recovery, document memory, one-writer, native subagent, or the subagent policy: system-requested work defaults to Luna/max, explicit user Sol/Luna mixes are allowed, and explicit project settings are reported and honored.

## Requirement And Architecture Work

- Treat the user's sentence as product intent, not a complete specification.
- Check users, main flow, loading/empty/error/retry states, data, privacy, security, performance, reliability, observability, configuration, dependencies, migration, tests, release, support, and future boundaries.
- Only correctness, safety, data integrity, and current usability requirements enter the required scope automatically.
- Choose the smallest architecture that supports the accepted scope and leaves clear extension boundaries.
- Architecture means responsibilities, interfaces, dependency direction, data flow, state ownership, and test locations. It is not a large preliminary rewrite.
- File size is only a clue. Split code when responsibilities are mixed, changes affect unrelated behavior, dependencies are tangled, or testing is difficult.
- Large or risky files are split gradually after behavior tests exist; never replace a working system wholesale because one file is long.
- Use structured parsers and the project's existing framework instead of ad hoc text manipulation or unnecessary new abstractions.

## Development Loop

1. Restore current facts and accepted user-visible features.
2. Expand the request and define scope, non-goals, acceptance, verification, permissions, and stop conditions.
3. Choose the smallest vertical slice that produces an observable result.
4. Protect existing behavior before the first edit.
5. Implement with one source writer in the current checkout.
6. Run risk-based tests, type/lint/build checks, and behavior verification.
7. Use an independent read-only reviewer for meaningful regression, architecture, security, or release risk.
8. Review the final diff for missing wiring, accidental deletion, unrelated changes, generated output, secrets, and user work.
9. Create the verified local recovery point before declaring completion.
10. Update only current project facts and one concrete next action.

## Existing Feature Protection

- `docs/FEATURES.md` and linked `docs/features/` files hold stable feature IDs, complete entry/wiring paths, expected results, verification, importance, and status.
- Tests are executable behavior memory. Git is recovery history. Neither replaces the feature map.
- Before changing accepted behavior, start the bundled current change guard with changed feature IDs and adjacent/critical IDs to recheck.
- Stage only explicit task-owned files through the guard. Never use broad `git add .` in a managed project.
- Verification evidence must come from commands actually run through the guard.
- A verified change is unfinished until the guard creates a matching local checkpoint.
- New requirements discovered mid-task must be declared before implementation; do not silently widen scope.
- Deleting or disconnecting an existing feature requires explicit intent and updated acceptance.

## Git And Beginner Recovery

- Automatically initialize local Git and create the first baseline after generated files, dependencies, secrets, local databases, and user data are excluded.
- Routine sequential development stays on the current branch. Do not create `codex/v1`, `codex/v2`, or similar branches as version history.
- Branches and Worktrees exist only for real isolation, background work, or parallel writers.
- Every verified vertical slice gets a local checkpoint through the guard-managed `checkpoint` command. It uses a one-time local Dev Kit identity and never changes the user's global Git identity.
- If the user says “回到上一个版本”, “撤销刚才的开发”, or equivalent, protect unsaved work and use the reversible rollback command. It creates a new commit and preserves both versions.
- Never automatically push, pull, merge, rebase, tag, release, amend, rewrite history, use `reset --hard`, clean files, or discard unconfirmed changes.
- Local Git is on-device recovery, not off-device backup. Remote backup is a separate user-approved setup.

## Native Subagents And Tasks

- “子代理/subagent/智能体” means Codex's native current-task collaboration tools only. Use `spawn_agent`, wait, message, follow-up, or interrupt.
- Never create, fork, hand off, or message a visible Codex task to simulate a subagent.
- Visible tasks are long-lived user contexts. One task owns one coherent outcome; start another when the outcome, branch, deliverable, or major module changes.
- Worktrees are Git isolation, not subagents. Appshots are visual state, not code versions. The review pane is native Git UI.
- No Dev Kit Hook is required for this workflow. Use explicit safe-development checks and local scripts; never add a Hook that intercepts `Agent`, `spawn_agent`, task tools, browser tools, or other native capabilities.
- Default to the main agent for simple work. Use subagents only for bounded independent exploration, official documentation checks, test execution, security review, architecture review, or answer-blind forward testing.
- Keep one writer per checkout. Parallel writers require separate Worktrees, branches, file ownership, and an explicit integration order.
- Do not send the expected answer to an independent reviewer.

### Subagent Model Policy

- The main conversation model is user-selected and is not locked by this system.
- Default subagent model: `gpt-5.6-luna`.
- Every system-requested subagent reasoning effort: `max`.
- Codex resolves each child model as: an explicit model on this spawn (including the user's roster) > `[agents].default_subagent_model` > the current parent task model. The templates request `gpt-5.6-luna` and `max` by default, but a TOML value is a default/request, not proof that a call completed successfully.
- Multiple subagents are allowed up to the smaller of `max_concurrent_threads_per_session` and the currently available native slots (the template default is 6, excluding the primary thread). If a requested roster is larger, run it in waves while preserving the exact total and model mix.
- If the user specifies a roster such as “2 Sol and 3 Luna”, spawn that exact mix with `gpt-5.6-sol` or `gpt-5.6-luna`, each at `max`.
- When explicitly overriding a subagent model or reasoning effort, pass `fork_turns = "none"` or a positive fork depth; the default full-history fork cannot be combined with per-call overrides.
- The explicit model catalog is evidence for models that can be overridden directly; it is not a complete list of the current task's inherited model. If the current task/runtime confirms the parent is Luna and the spawn omits `model`, classify the child as `inherited-current-model` Luna even when Luna is absent from that catalog. If the parent model cannot be confirmed, record the effective model as unconfirmed instead of inventing one.
- Before claiming that subagents are available, inspect the effective native configuration. If `[agents].enabled = false` or `[features].multi_agent = false`, report the exact disabled gate and stop the subagent route; ask the user before changing global/project configuration. Never work around a disabled gate with visible tasks, custom agents, Plugins, or Hooks.
- For an explicit roster such as “2 Sol and 3 Luna”, pass the exact model on each native spawn with `max` and judge the assignment from native argument acceptance/result. If the native runtime rejects or fails to confirm that explicit assignment, report that exact failure; do not silently substitute a model or reduce the requested count. A catalog omission alone is not enough to reject an inherited-current-model route.
- Prefer native per-call model selection; do not create custom Agent files unless the user explicitly asks for persistent named agents.
- A tool-argument serialization failure means the subagent did not start. Never report it as completed work.
- Explicit user/project configuration wins over defaults: the merge script only fills missing `[agents]` keys and never silently changes `enabled`, model, or reasoning effort. When this system starts a roster, it requests Luna/max by default; a deliberate user override is reported and honored rather than hidden. The in-memory ledger records both the requested and effective model plus provenance (`explicit-spawn`, `config-default`, `inherited-current-model`, or `runtime-unconfirmed`).

### Unattended roster ledger and timeouts

- Keep a temporary in-memory ledger for every roster: ID, requested model, reasoning effort, task, wave, and status (`queued`, `running`, `completed`, `failed`, `interrupted`, or `timeout`). Do not write agent transcripts or raw logs into the project.
- Before spawning, inspect the native agent list. Effective free slots are `max_concurrent_threads_per_session - running native subagents`, never below zero. If the native list is unavailable or ambiguous, start no new agents until the capacity is known; do not guess.
- Run waves of at most the effective free slots; wait for a wave to finish before starting the next. Preserve the exact requested count and model mix, recording failed starts instead of silently replacing them.
- Default heartbeat is every 5 minutes. If an agent gives no meaningful progress for 10 minutes, send one concise follow-up; if there is still no meaningful progress after 5 more minutes, interrupt it and mark `timeout`/`interrupted`. If the agent declares a long test, build, or official research phase before starting it, the main agent may record one extension in the ledger, with a hard 30-minute cap and still at most one follow-up. Allow no silent or unlimited extensions.
- Independent review and blind testing use `fork_turns="none"` by default (or a small explicit fork depth), receive only necessary facts, and must not receive the main agent's expected conclusion.
- Final orchestration reporting must distinguish planned, started, completed, failed, interrupted, and timed-out agents. A timed-out agent is never counted as completed.

## Context And Documents

- Chat context is temporary and may be compressed. Durable facts live in code, tests, Git, concise docs, and project instructions.
- Never save chat transcripts, hidden reasoning, raw logs, full diffs, daily journals, or permanent per-task reports.
- `docs/PROJECT.md`: user, outcome, scope, and non-goals.
- `docs/FEATURES.md`: current user-visible capabilities and verification routes; split by stable business domain when needed.
- `docs/STATUS.md`: current milestone, verified state, risks, and exactly one next action. Overwrite rather than append history.
- `docs/ARCHITECTURE.md`: current modules, interfaces, dependencies, state, and data flow.
- `docs/adr/`: only major decisions that are expensive to reverse.
- `docs/ROADMAP.md`: current and next two or three milestones, not a wish list.
- `.codex/current-change.json` and `.codex/active-plan.md`: ignored temporary state; one file each, replaced or removed rather than accumulated.
- Start a fresh task when context becomes noisy or the outcome changes. The new task restores from current docs, Git, tests, and any open change contract.

## Permissions

Automatic:

- Read and edit inside the selected project.
- Run existing tests, checks, builds, and local development commands.
- Initialize project-local Git, create verified checkpoints, and run reversible rollback.
- Use native read-only subagents when the required model is available.
- Update concise current project facts.

Ask first:

- Production dependencies, global tools, paid services, new accounts, external/private data, secrets, major architecture replacement, public API breaks, database schema migrations.
- Global Codex configuration, Skills installation, agents, Plugins, or system settings.
- Remote messages, PRs, issues, Git remotes, or any external state change.

Never automatic:

- Push, pull, merge, rebase, tag, release, deploy, publish, production migration, infrastructure apply/destroy, history rewrite, destructive clean/reset, or deletion of unconfirmed work.

## Completion Standard

Do not say a development request is complete until:

- The accepted behavior works.
- Existing affected and critical features were rechecked.
- Relevant tests/checks/builds ran with real evidence.
- The final diff was reviewed.
- No unrelated user work, secrets, dependencies, or generated files entered the checkpoint.
- A matching local recovery point exists.
- Current docs changed only where facts changed.
- Remaining risk and the next user action are stated in plain language.

## Beginner-safe Codex desktop settings

The user does not configure local environments, setup/cleanup scripts, Worktrees, Git branch prefixes, merge strategies, force-push, draft pull requests, or prompt boxes. Use the current project checkout for routine work. Create a Worktree only for real parallel isolation, and treat it as a temporary copy rather than a version or recovery point. Generate setup actions only after onboarding verifies the project's commands; keep cleanup empty unless it is demonstrably safe. Keep force-push and automatic draft PR creation off, and let the development Skills own local checkpoints and review.
