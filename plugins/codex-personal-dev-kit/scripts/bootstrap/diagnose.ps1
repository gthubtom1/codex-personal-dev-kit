[CmdletBinding()]
param(
    [string]$CodexHome
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($CodexHome)) {
    $CodexHome = if (-not [string]::IsNullOrWhiteSpace($env:CODEX_HOME)) {
        $env:CODEX_HOME
    }
    else {
        Join-Path ([Environment]::GetFolderPath("UserProfile")) ".codex"
    }
}

$codexHomePath = [System.IO.Path]::GetFullPath($CodexHome)
$checks = New-Object System.Collections.Generic.List[object]
function Add-Check {
    param([string]$Name, [bool]$Passed, [string]$Detail)
    $checks.Add([pscustomobject]@{ Check = $Name; Passed = $Passed; Detail = $Detail })
}

$agentsPath = Join-Path $codexHomePath "AGENTS.md"
$agentsContent = if (Test-Path -LiteralPath $agentsPath -PathType Leaf) { Get-Content -Raw $agentsPath } else { "" }
Add-Check "Managed AGENTS block" ($agentsContent.Contains("<!-- codex-dev-kit:start -->")) $agentsPath

foreach ($name in @("codex-kit-explorer.toml", "codex-kit-architect.toml", "codex-kit-reviewer.toml", "codex-kit-verifier.toml")) {
    $path = Join-Path $codexHomePath ("agents\" + $name)
    Add-Check "Agent $name" (Test-Path -LiteralPath $path -PathType Leaf) $path
}

$rulesPath = Join-Path $codexHomePath "rules\codex-dev-kit.rules"
Add-Check "Safety rules" (Test-Path -LiteralPath $rulesPath -PathType Leaf) $rulesPath
$versionPath = Join-Path $codexHomePath "codex-dev-kit\VERSION"
Add-Check "Installed version marker" (Test-Path -LiteralPath $versionPath -PathType Leaf) $versionPath
$sourcePath = Join-Path $codexHomePath "codex-dev-kit\source.json"
Add-Check "Pinned marketplace source" (Test-Path -LiteralPath $sourcePath -PathType Leaf) $sourcePath

$codexCommand = Get-Command codex -ErrorAction SilentlyContinue
Add-Check "Codex CLI available" ($null -ne $codexCommand) $(if ($codexCommand) { $codexCommand.Source } else { "codex was not found on PATH" })

$checks | Format-Table -AutoSize
if ($checks.Where({ -not $_.Passed }).Count -gt 0) {
    exit 1
}
