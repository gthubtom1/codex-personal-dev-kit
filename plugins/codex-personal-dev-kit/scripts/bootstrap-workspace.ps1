[CmdletBinding()]
param(
    [string]$WorkspaceRoot = (Get-Location).Path,
    [string]$CodexHome,
    [switch]$Apply
)

$ErrorActionPreference = "Stop"
$workspacePath = [System.IO.Path]::GetFullPath($WorkspaceRoot)
$codexHomePath = if (-not [string]::IsNullOrWhiteSpace($CodexHome)) {
    [System.IO.Path]::GetFullPath($CodexHome)
}
elseif (-not [string]::IsNullOrWhiteSpace($env:CODEX_HOME)) {
    [System.IO.Path]::GetFullPath($env:CODEX_HOME)
}
else {
    [System.IO.Path]::GetFullPath((Join-Path ([Environment]::GetFolderPath("UserProfile")) ".codex"))
}
$filesystemRoot = [System.IO.Path]::GetPathRoot($workspacePath)
if ($workspacePath.TrimEnd('\', '/') -eq $filesystemRoot.TrimEnd('\', '/')) {
    throw "Refusing to use a filesystem root as the workspace: $workspacePath"
}

$pluginRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$templateRoot = Join-Path $pluginRoot "assets\workspace-template"
if (-not (Test-Path -LiteralPath $templateRoot -PathType Container)) {
    throw "Workspace template not found: $templateRoot"
}
$skillsRoot = Join-Path $pluginRoot "skills"
if (-not (Test-Path -LiteralPath $skillsRoot -PathType Container)) {
    $installedSkillsRoot = Join-Path (Split-Path -Parent $pluginRoot) "skills"
    if (Test-Path -LiteralPath $installedSkillsRoot -PathType Container) {
        $skillsRoot = $installedSkillsRoot
    }
}

$workspaceName = Split-Path -Leaf $workspacePath
$targets = @(
    [pscustomobject]@{ Type = "directory"; Path = (Join-Path $workspacePath "projects") },
    [pscustomobject]@{ Type = "directory"; Path = (Join-Path $workspacePath "archives") },
    [pscustomobject]@{ Type = "file"; Path = (Join-Path $workspacePath "AGENTS.md"); Source = (Join-Path $templateRoot "AGENTS.md") },
    [pscustomobject]@{ Type = "file"; Path = (Join-Path $workspacePath "workspace.json"); Source = (Join-Path $templateRoot "workspace.json") }
)

$preview = foreach ($target in $targets) {
    $action = if (-not (Test-Path -LiteralPath $target.Path)) {
        "create"
    }
    else {
        "keep"
    }
    [pscustomobject]@{
        Action = $action
        Type = $target.Type
        Path = $target.Path
    }
}
$preview | Format-Table -AutoSize
if (-not $Apply) {
    Write-Host "Preview only. Re-run with -Apply after checking the mother-folder path."
    exit 0
}

New-Item -ItemType Directory -Path $workspacePath -Force | Out-Null
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
foreach ($target in $targets) {
    if (Test-Path -LiteralPath $target.Path) {
        continue
    }
    if ($target.Type -eq "directory") {
        New-Item -ItemType Directory -Path $target.Path -Force | Out-Null
        continue
    }
    $content = [System.IO.File]::ReadAllText($target.Source)
    $content = $content.Replace("{{WORKSPACE_NAME}}", $workspaceName)
    $content = $content.Replace("{{WORKSPACE_ROOT}}", $workspacePath)
    $content = $content.Replace("{{DEV_KIT_SKILLS_ROOT}}", $skillsRoot)
    $content = $content.Replace("{{CODEX_HOME}}", $codexHomePath)
    [System.IO.File]::WriteAllText($target.Path, $content, $utf8NoBom)
}

Write-Host "Workspace initialized. The mother folder was not made into a Git repository."
