[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$scriptRoot = [System.IO.Path]::GetFullPath($PSScriptRoot)
$runtimeRoot = [System.IO.Path]::GetFullPath((Join-Path $scriptRoot ".."))
$codexHome = if (-not [string]::IsNullOrWhiteSpace($env:CODEX_HOME)) {
    $env:CODEX_HOME
}
else {
    Join-Path ([Environment]::GetFolderPath("UserProfile")) ".codex"
}
$codexHome = [System.IO.Path]::GetFullPath($codexHome)

$sourceMode = Test-Path -LiteralPath (Join-Path $runtimeRoot "skills") -PathType Container
$pluginRoot = $null
$repoRoot = $null
$skillRoot = $null
$sourceValidationScript = $null

if ($sourceMode) {
    $pluginRoot = $runtimeRoot
    $repoRoot = [System.IO.Path]::GetFullPath((Join-Path $pluginRoot "..\.."))
    $skillRoot = Join-Path $pluginRoot "skills"
}
else {
    $sourceMetadataPath = Join-Path $runtimeRoot "source.json"
    if (-not (Test-Path -LiteralPath $sourceMetadataPath -PathType Leaf)) {
        throw "Standalone runtime source metadata was not found: $sourceMetadataPath"
    }
    try {
        $sourceMetadata = Get-Content -Raw -LiteralPath $sourceMetadataPath | ConvertFrom-Json
    }
    catch {
        throw "Standalone runtime source metadata is invalid: $sourceMetadataPath"
    }
    if ([string]::IsNullOrWhiteSpace([string]$sourceMetadata.source)) {
        throw "Standalone runtime source metadata has no local source path: $sourceMetadataPath"
    }
    $sourceRepoRoot = [System.IO.Path]::GetFullPath([string]$sourceMetadata.source)
    $sourceValidationScript = Join-Path $sourceRepoRoot "plugins\codex-personal-dev-kit\scripts\validate-kit.ps1"
    if (-not (Test-Path -LiteralPath $sourceValidationScript -PathType Leaf)) {
        throw "Verified local source validation script was not found: $sourceValidationScript"
    }
    $skillRoot = Join-Path $codexHome "skills"
    Write-Host "Standalone runtime detected; delegating source validation to $sourceValidationScript"
    & $sourceValidationScript
    if ($LASTEXITCODE -ne 0) {
        throw "Source Dev Kit validation failed."
    }
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw "Python was not found on PATH."
}

$skillValidator = Join-Path $codexHome "skills\.system\skill-creator\scripts\quick_validate.py"
if (-not (Test-Path -LiteralPath $skillValidator -PathType Leaf)) { throw "Skill validator not found: $skillValidator" }

@(
    "audit-codex-kit",
    "codex-development-assistant",
    "codex-safe-development",
    "integrate-codex-projects",
    "manage-project-continuity",
    "onboard-codex-project",
    "orchestrate-codex-team",
    "prepare-codex-goal",
    "research-and-reuse"
) | ForEach-Object {
    $skillName = $_
    $skillPath = Join-Path $skillRoot $skillName
    if (-not (Test-Path -LiteralPath $skillPath -PathType Container)) {
        throw "Standalone Skill directory was not found: $skillPath"
    }
    & $python.Source $skillValidator $skillPath
    if ($LASTEXITCODE -ne 0) { throw "Skill validation failed: $skillName" }
}

if ($sourceMode) {
    & $python.Source (Join-Path $pluginRoot "scripts\validate_kit.py")
    if ($LASTEXITCODE -ne 0) { throw "Dev Kit structural validation failed." }
}

$powerShellParseErrors = New-Object System.Collections.Generic.List[object]
$parseRoot = if ($sourceMode) { $repoRoot } else { $runtimeRoot }
Get-ChildItem -LiteralPath $parseRoot -Recurse -Filter *.ps1 -File | ForEach-Object {
    $tokens = $null
    $parseErrors = $null
    [System.Management.Automation.Language.Parser]::ParseFile($_.FullName, [ref]$tokens, [ref]$parseErrors) | Out-Null
    foreach ($parseError in $parseErrors) {
        $powerShellParseErrors.Add($parseError)
    }
}
if ($powerShellParseErrors.Count -gt 0) {
    $powerShellParseErrors | Format-List
    throw "PowerShell parsing failed."
}
Write-Host "PowerShell parse checks passed."

$reportedRoot = if ($sourceMode) { $repoRoot } else { $runtimeRoot }
Write-Host "All available validators passed for $reportedRoot"
