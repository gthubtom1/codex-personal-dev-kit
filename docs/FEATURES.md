# Feature Map

This is the current behavior of Codex Personal Dev Kit. It is an index, not a development log.

| ID | User capability | Entry points / connected path | Expected result | Verification | Criticality | Status |
| --- | --- | --- | --- | --- | --- | --- |
| DK-001 | Start software work with one plain-language request | Plugin prompt -> `codex-development-assistant` -> internal Skills | Codex expands the need and continues to a usable, verified result with only material decisions exposed. | Official validation of all seven Skills plus forward scenarios | critical | active |
| DK-002 | Create and open independent long-term projects | Mother folder -> `create-project.ps1` -> project template -> local Git baseline | Each `projects/<name>` folder is an independent Codex working folder and Git repository; the mother folder is not a repository. | `test_workspace_scripts.py` | critical | active |
| DK-003 | Change one feature without silently losing another | FEATURES IDs -> current change contract -> PreToolUse/SessionStart/Stop Hooks -> tests/review | Unprotected edits, unverified commits, removed feature records, and unexpected tracked-file deletions are stopped. | `test_feature_guard.py` | critical | active |
| DK-004 | Recover from mistakes without learning Git first | Safe development Skill -> local checkpoints -> Rules/PreToolUse guard | Local work has recovery points while destructive or remote Git, publish, deploy, and infrastructure commands are blocked. | `test_pre_tool_guard.py` and Rules check | critical | active |
| DK-005 | Continue across shorter Codex tasks without giant documents | AGENTS/PROJECT/FEATURES/STATUS -> Git/tests -> continuity Skill | A new task restores current facts quickly; documents overwrite current state instead of accumulating transcripts. | Skill validation and continuity forward scenario | standard | active |
| DK-006 | Use subagents without creating merge chaos | Orchestration Skill -> read-only specialists -> one writer per checkout -> Worktree only for real isolation | Parallel research, review, and verification return concise evidence while source ownership stays clear. | Orchestration forward scenario | standard | active |
| DK-007 | Validate and install the assistant predictably | Marketplace/Plugin -> bootstrap preview/apply/backup -> fixed release ref | Structure validates, previews do not write, updates preserve custom content, and installation never silently follows an unpinned branch. | `test_install_scripts.py` and Plugin validator | standard | active |

Keep this file concise. Add a feature only when it is a stable user capability with a repeatable verification path.
