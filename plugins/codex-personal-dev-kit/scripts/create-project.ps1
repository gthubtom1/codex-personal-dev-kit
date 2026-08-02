[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ProjectName,
    [string]$WorkspaceRoot = (Get-Location).Path,
    [switch]$Apply
)

$ErrorActionPreference = "Stop"
$workspacePath = [System.IO.Path]::GetFullPath($WorkspaceRoot)
$workspaceConfigPath = Join-Path $workspacePath "workspace.json"
if (-not (Test-Path -LiteralPath $workspaceConfigPath -PathType Leaf)) {
    if (-not $Apply) {
        Write-Host "workspace.json was not found. Apply mode will initialize this mother folder automatically before creating the project."
        Write-Host "Preview only. Re-run with -Apply to initialize the workspace, create templates, initialize Git, and make a local baseline checkpoint."
        exit 0
    }
    $bootstrapWorkspace = Join-Path $PSScriptRoot "bootstrap-workspace.ps1"
    & $bootstrapWorkspace -WorkspaceRoot $workspacePath -Apply
    if (-not (Test-Path -LiteralPath $workspaceConfigPath -PathType Leaf)) {
        throw "Mother-folder initialization completed without creating workspace.json."
    }
}

$workspaceConfig = Get-Content -Raw -LiteralPath $workspaceConfigPath | ConvertFrom-Json
$projectsDirectory = [string]$workspaceConfig.projectsDirectory
if ([string]::IsNullOrWhiteSpace($projectsDirectory)) {
    throw "workspace.json does not define projectsDirectory."
}

$slug = $ProjectName.Trim()
$slug = [regex]::Replace($slug, '[<>:"/\\|?*]', '-')
$slug = [regex]::Replace($slug, '\s+', '-')
$slug = [regex]::Replace($slug, '-{2,}', '-')
$slug = $slug.Trim(' ', '.', '-')
if ([string]::IsNullOrWhiteSpace($slug)) {
    throw "ProjectName does not contain a safe folder name."
}
if ($slug.ToUpperInvariant() -in @("CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "LPT1", "LPT2", "LPT3")) {
    throw "ProjectName resolves to a reserved Windows folder name: $slug"
}

$projectsRoot = [System.IO.Path]::GetFullPath((Join-Path $workspacePath $projectsDirectory))
$projectPath = [System.IO.Path]::GetFullPath((Join-Path $projectsRoot $slug))
$prefix = $projectsRoot.TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
if (-not $projectPath.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Resolved project path escaped the projects directory: $projectPath"
}
if (Test-Path -LiteralPath $projectPath) {
    throw "Project folder already exists: $projectPath"
}

Write-Host "Project folder: $projectPath"
if (-not $Apply) {
    Write-Host "Preview only. Re-run with -Apply to create templates, initialize Git, and make a local baseline checkpoint."
    exit 0
}

New-Item -ItemType Directory -Path $projectsRoot -Force | Out-Null
$bootstrapProject = Join-Path $PSScriptRoot "bootstrap-project.ps1"
& $bootstrapProject -ProjectRoot $projectPath -WorkspaceRoot $workspacePath -Apply -InitializeGit -CreateBaselineCheckpoint
if ($LASTEXITCODE -ne 0) {
    throw "Project bootstrap failed."
}

Write-Host "Project created with a local recovery point."
Write-Host "Next: open '$projectPath' as the Codex working folder and start a new task."
