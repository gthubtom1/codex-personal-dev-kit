[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$pluginRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $pluginRoot "..\.."))
. (Join-Path $PSScriptRoot "bootstrap\resolve-codex-cli.ps1")
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

$codex = Resolve-CodexCli
if ($codex) {
    $rulesPath = Join-Path $pluginRoot "assets\global-profile\rules\codex-dev-kit.rules"
    function Assert-ExecPolicyDecision {
        param(
            [Parameter(Mandatory = $true)][string[]]$CommandTokens,
            [Parameter(Mandatory = $true)][string]$Expected
        )

        $raw = & $codex.Path execpolicy check --rules $rulesPath @CommandTokens
        if ($LASTEXITCODE -ne 0) { throw "Rules parser failed for: $($CommandTokens -join ' ')" }
        $result = ($raw -join [Environment]::NewLine) | ConvertFrom-Json
        $actual = if ([string]::IsNullOrWhiteSpace([string]$result.decision)) { "allow" } else { [string]$result.decision }
        if ($actual -ne $Expected) {
            throw "Unexpected Rules decision for '$($CommandTokens -join ' ')': expected $Expected, got $actual."
        }
    }

    Assert-ExecPolicyDecision -CommandTokens @("git", "push") -Expected "forbidden"
    Assert-ExecPolicyDecision -CommandTokens @("git", "status") -Expected "allow"
    Assert-ExecPolicyDecision -CommandTokens @("winget", "install", "Git.Git") -Expected "prompt"
    Assert-ExecPolicyDecision -CommandTokens @("npm", "publish") -Expected "forbidden"
    Assert-ExecPolicyDecision -CommandTokens @("npm", "test") -Expected "allow"
    Write-Host "Rules parser checks passed with $($codex.Version) at $($codex.Path)"
}
else {
    Write-Warning "A runnable Codex CLI was not found; Rules parser checks were skipped."
}

Write-Host "All available validators passed for $repoRoot"
