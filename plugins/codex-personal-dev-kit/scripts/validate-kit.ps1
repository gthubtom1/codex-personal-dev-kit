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
if (-not (Test-Path -LiteralPath $skillValidator -PathType Leaf)) { throw "Skill validator not found: $skillValidator" }

Get-ChildItem -LiteralPath (Join-Path $pluginRoot "skills") -Directory | Sort-Object Name | ForEach-Object {
    & $python.Source $skillValidator $_.FullName
    if ($LASTEXITCODE -ne 0) { throw "Skill validation failed: $($_.Name)" }
}

& $python.Source (Join-Path $pluginRoot "scripts\validate_kit.py")
if ($LASTEXITCODE -ne 0) { throw "Dev Kit structural validation failed." }

$powerShellParseErrors = New-Object System.Collections.Generic.List[object]
Get-ChildItem -LiteralPath $repoRoot -Recurse -Filter *.ps1 -File | ForEach-Object {
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

Write-Host "All available validators passed for $repoRoot"
