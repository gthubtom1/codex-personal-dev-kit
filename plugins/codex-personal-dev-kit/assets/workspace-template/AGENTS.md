# Workspace Instructions

This mother folder only organizes independent long-term projects. Use `$codex-development-assistant` here for project creation and workspace management, not for developing an existing project.

## Boundaries

- New projects live under `projects/<project-name>/`.
- Every project is its own Git repository and should become its own primary Codex working folder.
- Existing-project development never starts from this mother folder. The user opens the specific project folder in Codex first, and that project's `AGENTS.md` then governs the work.
- Do not initialize Git at the mother-folder level.
- Do not scan or edit multiple project folders unless the user explicitly requests a portfolio audit.
- Do not copy Codex Dev Kit into projects. Reuse the installed Plugin.
- `archives/` contains inactive projects. Never move, delete, or restore one without confirming the exact target.

## New Project Flow

Create the requested folder with the Dev Kit project template and a local baseline checkpoint. Then tell the user to open that project folder as the Codex working folder and start a new task so project instructions load correctly.
