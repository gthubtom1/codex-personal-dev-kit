[CmdletBinding()]
param(
    [string]$CodexHome,
    [string]$WorkspaceRoot = "D:\开发"
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($CodexHome)) {
    $CodexHome = if (-not [string]::IsNullOrWhiteSpace($env:CODEX_HOME)) { $env:CODEX_HOME } else { Join-Path ([Environment]::GetFolderPath("UserProfile")) ".codex" }
}
$codexHomePath = [System.IO.Path]::GetFullPath($CodexHome)
$workspacePath = [System.IO.Path]::GetFullPath($WorkspaceRoot)
$checks = New-Object System.Collections.Generic.List[object]

function Add-Check {
    param([string]$Name, [bool]$Passed, [string]$Detail)
    $checks.Add([pscustomobject]@{ Check = $Name; Passed = $Passed; Detail = $Detail })
}

$agentsPath = Join-Path $codexHomePath "AGENTS.md"
$agentsContent = if (Test-Path -LiteralPath $agentsPath -PathType Leaf) { Get-Content -Raw $agentsPath } else { "" }
Add-Check "Short global AGENTS block" ($agentsContent.Contains("<!-- codex-dev-kit:start -->") -and $agentsContent.Contains($workspacePath)) $agentsPath
$workspaceAgents = Join-Path $workspacePath "AGENTS.md"
Add-Check "Detailed mother-folder AGENTS" (Test-Path -LiteralPath $workspaceAgents -PathType Leaf) $workspaceAgents

$kitRoot = Join-Path $codexHomePath "codex-dev-kit"
$indexPath = Join-Path $kitRoot "INDEX.md"
Add-Check "Standalone local index" (Test-Path -LiteralPath $indexPath -PathType Leaf) $indexPath
$versionPath = Join-Path $kitRoot "VERSION"
Add-Check "Standalone version marker" (Test-Path -LiteralPath $versionPath -PathType Leaf) $versionPath
$sourcePath = Join-Path $kitRoot "source.json"
$source = $null
if (Test-Path -LiteralPath $sourcePath -PathType Leaf) {
    try {
        $source = Get-Content -Raw $sourcePath | ConvertFrom-Json
        Add-Check "Standalone source metadata" ($source.schemaVersion -eq 2 -and $source.mode -eq "standalone" -and $source.sourceType -eq "local") "$($source.sourceType) source"
        $installedVersion = if (Test-Path -LiteralPath $versionPath) { (Get-Content -Raw $versionPath).Trim() } else { "" }
        Add-Check "Source version matches marker" ([string]$source.version -eq $installedVersion -and -not [string]::IsNullOrWhiteSpace($installedVersion)) "source=$($source.version); marker=$installedVersion"
    }
    catch {
        Add-Check "Standalone source metadata" $false $_.Exception.Message
    }
}
else {
    Add-Check "Standalone source metadata" $false $sourcePath
}

if ($source -and $source.sourceType -eq "local") {
    $localSource = [string]$source.source
    $localExists = Test-Path -LiteralPath $localSource -PathType Container
    Add-Check "Local standalone source" $localExists $localSource
    $git = Get-Command git -ErrorAction SilentlyContinue
    Add-Check "Git for local source" ($null -ne $git) $(if ($git) { $git.Source } else { "git not found" })
    if ($localExists -and $git) {
        $headOutput = @(& $git.Source -C $localSource rev-parse HEAD 2>$null)
        $head = if ($LASTEXITCODE -eq 0 -and $headOutput.Count -gt 0) { ([string]$headOutput[0]).Trim() } else { "" }
        Add-Check "Local source HEAD" ($head -eq [string]$source.ref -and -not [string]::IsNullOrWhiteSpace($head)) "expected=$($source.ref); actual=$head"
        $status = (& $git.Source -C $localSource status --porcelain 2>$null) -join [Environment]::NewLine
        Add-Check "Local source working tree" ($LASTEXITCODE -eq 0 -and [string]::IsNullOrWhiteSpace($status)) $(if ([string]::IsNullOrWhiteSpace($status)) { "clean" } else { $status })
        $sourceManifest = Join-Path $localSource "plugins\codex-personal-dev-kit\.codex-plugin\plugin.json"
        if (-not (Test-Path -LiteralPath $sourceManifest -PathType Leaf)) {
            $sourceManifest = Join-Path $localSource ".codex-plugin\plugin.json"
        }
        $sourceVersion = ""
        if (Test-Path -LiteralPath $sourceManifest -PathType Leaf) {
            try { $sourceVersion = [string]((Get-Content -Raw $sourceManifest | ConvertFrom-Json).version) } catch { }
        }
        $installedVersion = if (Test-Path -LiteralPath $versionPath) { (Get-Content -Raw $versionPath).Trim() } else { "" }
        Add-Check "Local source version" ($sourceVersion -eq $installedVersion -and -not [string]::IsNullOrWhiteSpace($sourceVersion)) "source=$sourceVersion; installed=$installedVersion"
    }
}

foreach ($name in @(
    "codex-development-assistant",
    "onboard-codex-project",
    "prepare-codex-goal",
    "orchestrate-codex-team",
    "codex-safe-development",
    "manage-project-continuity",
    "audit-codex-kit"
)) {
    $path = Join-Path $codexHomePath ("skills\$name\SKILL.md")
    Add-Check "Standalone Skill $name" (Test-Path -LiteralPath $path -PathType Leaf) $path
}
foreach ($relative in @("scripts\feature_guard.py", "scripts\pre_tool_guard.py", "scripts\bootstrap-project.ps1", "assets\project-template\.codex\hooks.json")) {
    $path = Join-Path $kitRoot $relative
    Add-Check "Standalone runtime $relative" (Test-Path -LiteralPath $path -PathType Leaf) $path
}

$configPath = Join-Path $codexHomePath "config.toml"
$configContent = if (Test-Path -LiteralPath $configPath -PathType Leaf) { Get-Content -Raw $configPath } else { "" }
$legacyPluginEnabled = $configContent -match '(?m)^\[plugins\."codex-personal-dev-kit@'
Add-Check "Legacy Dev Kit Plugin disabled" (-not $legacyPluginEnabled) $(if ($legacyPluginEnabled) { "The old Plugin is still enabled in config.toml; disable it before testing standalone mode." } else { "not configured" })
. (Join-Path $PSScriptRoot "resolve-codex-cli.ps1")
$codexCommand = Resolve-CodexCli
if ($codexCommand) {
    $previousCodexHome = $env:CODEX_HOME
    try {
        $env:CODEX_HOME = $codexHomePath
        $previousErrorActionPreference = $ErrorActionPreference
        try {
            $ErrorActionPreference = "Continue"
            $pluginListOutput = & $codexCommand.Path plugin list 2>&1
            $pluginListExitCode = $LASTEXITCODE
        }
        finally {
            $ErrorActionPreference = $previousErrorActionPreference
        }
        $pluginListText = ($pluginListOutput | ForEach-Object { [string]$_ }) -join [Environment]::NewLine
        $pluginListPassed = $pluginListExitCode -eq 0
        $legacyPluginMatches = @([regex]::Matches($pluginListText, '(?im)^\s*(codex-personal-dev-kit@[^\s]+)\s+installed(?:\s|,|$)') | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique)
        $legacyPluginInstalled = $pluginListPassed -and $legacyPluginMatches.Count -gt 0
        Add-Check "Legacy Dev Kit Plugin not installed" ($pluginListPassed -and -not $legacyPluginInstalled) $(if (-not $pluginListPassed) { "codex plugin list failed" } elseif ($legacyPluginInstalled) { ($legacyPluginMatches -join ", ") + " is still installed" } else { "not installed" })
    }
    finally {
        if ($null -eq $previousCodexHome) { Remove-Item Env:CODEX_HOME -ErrorAction SilentlyContinue } else { $env:CODEX_HOME = $previousCodexHome }
    }
}
else {
    Add-Check "Legacy Dev Kit Plugin not installed" $false "Codex CLI was not found"
}
$globalHooksPath = Join-Path $codexHomePath "hooks.json"
$globalHooks = if (Test-Path -LiteralPath $globalHooksPath -PathType Leaf) { Get-Content -Raw $globalHooksPath } else { "" }
Add-Check "No global Dev Kit Hook" (-not ($globalHooks -match "codex-dev-kit|feature_guard\.py")) $(if ($globalHooks) { $globalHooksPath } else { "no global hooks.json" })

$legacyAgents = @(Get-ChildItem -LiteralPath (Join-Path $codexHomePath "agents") -Filter "codex-kit-*.toml" -File -ErrorAction SilentlyContinue)
Add-Check "No required custom agents" ($legacyAgents.Count -eq 0) $(if ($legacyAgents.Count -eq 0) { "standalone mode uses native built-in agents" } else { ($legacyAgents.Name -join ", ") + " are legacy optional files" })

$checks | Format-Table -AutoSize
if ($checks.Where({ -not $_.Passed }).Count -gt 0) {
    exit 1
}
