[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$pluginRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $pluginRoot "..\.."))
$codexHome = if (-not [string]::IsNullOrWhiteSpace($env:CODEX_HOME)) {
    $env:CODEX_HOME
}
else {
    Join-Path ([Environment]::GetFolderPath("UserProfile")) ".codex"
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw "Python was not found on PATH."
}

$skillValidator = Join-Path $codexHome "skills\.system\skill-creator\scripts\quick_validate.py"
$pluginValidator = Join-Path $codexHome "skills\.system\plugin-creator\scripts\validate_plugin.py"
if (-not (Test-Path -LiteralPath $skillValidator -PathType Leaf)) { throw "Skill validator not found: $skillValidator" }
if (-not (Test-Path -LiteralPath $pluginValidator -PathType Leaf)) { throw "Plugin validator not found: $pluginValidator" }

Get-ChildItem -LiteralPath (Join-Path $pluginRoot "skills") -Directory | Sort-Object Name | ForEach-Object {
    & $python.Source $skillValidator $_.FullName
    if ($LASTEXITCODE -ne 0) { throw "Skill validation failed: $($_.Name)" }
}

& $python.Source $pluginValidator $pluginRoot
if ($LASTEXITCODE -ne 0) { throw "Plugin validation failed." }

& $python.Source (Join-Path $pluginRoot "scripts\validate_kit.py")
if ($LASTEXITCODE -ne 0) { throw "Dev Kit structural validation failed." }

Write-Host "All available validators passed for $repoRoot"
