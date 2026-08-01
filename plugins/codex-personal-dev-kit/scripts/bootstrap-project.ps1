[CmdletBinding()]
param(
    [string]$ProjectRoot = (Get-Location).Path,
    [switch]$Apply,
    [switch]$InitializeGit
)

$ErrorActionPreference = "Stop"

function Get-SafeFullPath {
    param([Parameter(Mandatory = $true)][string]$Path)

    $full = [System.IO.Path]::GetFullPath($Path)
    $root = [System.IO.Path]::GetPathRoot($full)
    $trimmedFull = $full.TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar)
    $trimmedRoot = $root.TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar)
    if ($trimmedFull -eq $trimmedRoot) {
        throw "Refusing to use a drive or filesystem root as a project directory: $full"
    }
    return $full
}

$projectPath = Get-SafeFullPath -Path $ProjectRoot
$pluginRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$templateRoot = Join-Path $pluginRoot "assets\project-template"
if (-not (Test-Path -LiteralPath $templateRoot -PathType Container)) {
    throw "Project template not found: $templateRoot"
}

$projectName = Split-Path -Leaf $projectPath
if ([string]::IsNullOrWhiteSpace($projectName)) {
    throw "Unable to determine the project name from: $projectPath"
}

$templateFiles = Get-ChildItem -LiteralPath $templateRoot -Recurse -Force -File
$actions = foreach ($source in $templateFiles) {
    $relative = $source.FullName.Substring($templateRoot.Length).TrimStart('\', '/')
    $destination = Join-Path $projectPath $relative
    [pscustomobject]@{
        Action = if (Test-Path -LiteralPath $destination) { "keep" } else { "create" }
        Path = $destination
        Source = $source.FullName
    }
}

$actions | Select-Object Action, Path | Format-Table -AutoSize
if (-not $Apply) {
    Write-Host "Preview only. Re-run with -Apply after checking the target paths."
    if ($InitializeGit) {
        Write-Host "Git initialization would run only after template creation."
    }
    exit 0
}

New-Item -ItemType Directory -Path $projectPath -Force | Out-Null
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
foreach ($action in $actions) {
    if ($action.Action -ne "create") {
        continue
    }
    $destinationDirectory = Split-Path -Parent $action.Path
    New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null
    $content = [System.IO.File]::ReadAllText($action.Source)
    $content = $content.Replace("{{PROJECT_NAME}}", $projectName)
    [System.IO.File]::WriteAllText($action.Path, $content, $utf8NoBom)
}

if ($InitializeGit) {
    $git = Get-Command git -ErrorAction SilentlyContinue
    if (-not $git) {
        throw "Git is not available on PATH. Templates were created, but Git was not initialized."
    }

    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "SilentlyContinue"
        $existingRoot = (& $git.Source -C $projectPath rev-parse --show-toplevel 2>$null)
        $existingRootExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    if ($existingRootExitCode -eq 0) {
        $existingFull = [System.IO.Path]::GetFullPath(($existingRoot | Select-Object -First 1))
        if ($existingFull.TrimEnd('\', '/') -ne $projectPath.TrimEnd('\', '/')) {
            throw "The project is already inside another Git repository: $existingFull"
        }
        Write-Host "Git repository already exists at $existingFull"
    }
    else {
        & $git.Source -C $projectPath init -b main
        if ($LASTEXITCODE -ne 0) {
            & $git.Source -C $projectPath init
            if ($LASTEXITCODE -ne 0) {
                throw "git init failed for $projectPath"
            }
            & $git.Source -C $projectPath branch -M main
        }
    }
}

Write-Host "Project bootstrap complete. Existing files were preserved."
