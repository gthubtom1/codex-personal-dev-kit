[CmdletBinding()]
param(
    [string]$CodexHome,
    [string]$WorkspaceRoot = "D:\开发",
    [switch]$Apply,
    [switch]$MigrateLegacy,
    [string]$Source,
    [string]$Ref
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
$workspacePath = [System.IO.Path]::GetFullPath($WorkspaceRoot)
foreach ($path in @($codexHomePath, $workspacePath)) {
    $filesystemRoot = [System.IO.Path]::GetPathRoot($path)
    if ($path.TrimEnd('\', '/') -eq $filesystemRoot.TrimEnd('\', '/')) {
        throw "Refusing to use a filesystem root: $path"
    }
}

$workspaceAgents = Join-Path $workspacePath "AGENTS.md"
if (-not (Test-Path -LiteralPath $workspaceAgents -PathType Leaf)) {
    throw "Detailed workspace AGENTS.md was not found: $workspaceAgents"
}
$workspaceConfig = Join-Path $workspacePath ".codex\config.toml"
$legacyLunaDefaultDetected = $false
if (Test-Path -LiteralPath $workspaceConfig -PathType Leaf) {
    $workspaceConfigText = [System.IO.File]::ReadAllText($workspaceConfig)
    $legacyLunaDefaultDetected = [bool]($workspaceConfigText -match '(?m)^\s*default_subagent_model\s*=\s*["'']gpt-5\.6-luna["'']\s*(?:#.*)?$')
}
$workspaceAgentsText = [System.IO.File]::ReadAllText($workspaceAgents)
$legacyRoutingTextDetected = [bool](
    $workspaceAgentsText -match '(?i)(default|默认|请求).{0,40}(gpt-5\.6-luna|Luna/max)' -or
    $workspaceAgentsText -match '(?i)(agent list|代理列表).{0,80}(unavailable|不可用|不启动)'
)

$bootstrapKitRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
$bootstrapRepoRoot = [System.IO.Path]::GetFullPath((Join-Path $bootstrapKitRoot "..\.."))
if ([string]::IsNullOrWhiteSpace($Source)) {
    $Source = $bootstrapRepoRoot
}

$resolvedSource = if (Test-Path -LiteralPath $Source -PathType Container) {
    [System.IO.Path]::GetFullPath($Source)
}
else {
    throw "Standalone installation requires a local Git checkout. Clone or check out a fixed tag/commit first: $Source"
}
$repoLayoutKitRoot = Join-Path $resolvedSource "plugins\codex-personal-dev-kit"
if (Test-Path -LiteralPath (Join-Path $repoLayoutKitRoot "assets\standalone\AGENTS.md") -PathType Leaf) {
    $kitSourceRoot = $repoLayoutKitRoot
}
elseif (Test-Path -LiteralPath (Join-Path $resolvedSource "assets\standalone\AGENTS.md") -PathType Leaf) {
    $kitSourceRoot = $resolvedSource
}
else {
    throw "Local standalone Dev Kit checkout is missing the standalone AGENTS template: $resolvedSource"
}

$git = Get-Command git -ErrorAction SilentlyContinue
if (-not $git) { throw "Git is required to verify the local Dev Kit checkout." }
$gitRootOutput = @(& $git.Source -C $resolvedSource rev-parse --show-toplevel 2>$null)
$gitRoot = if ($LASTEXITCODE -eq 0 -and $gitRootOutput.Count -gt 0) { ([string]$gitRootOutput[0]).Trim() } else { "" }
if ([string]::IsNullOrWhiteSpace($gitRoot)) {
    throw "Local Dev Kit source must be a Git checkout: $resolvedSource"
}
$headOutput = @(& $git.Source -C $gitRoot rev-parse HEAD 2>$null)
$head = if ($LASTEXITCODE -eq 0 -and $headOutput.Count -gt 0) { ([string]$headOutput[0]).Trim() } else { "" }
if ([string]::IsNullOrWhiteSpace($head)) {
    throw "Local Dev Kit checkout has no committed HEAD: $gitRoot"
}
$status = (& $git.Source -C $gitRoot status --porcelain 2>$null) -join [Environment]::NewLine
if ($LASTEXITCODE -ne 0) { throw "Unable to inspect the local Dev Kit checkout." }
if (-not [string]::IsNullOrWhiteSpace($status)) {
    throw "Local Dev Kit source has uncommitted changes. Create a verified local recovery point before installing it."
}
if (-not [string]::IsNullOrWhiteSpace($Ref)) {
    $requestedOutput = @(& $git.Source -C $gitRoot rev-parse "$Ref^{commit}" 2>$null)
    $requestedHead = if ($LASTEXITCODE -eq 0 -and $requestedOutput.Count -gt 0) { ([string]$requestedOutput[0]).Trim() } else { "" }
    if ([string]::IsNullOrWhiteSpace($requestedHead) -or $requestedHead -ne $head) {
        throw "Local Dev Kit HEAD $head does not match requested Ref $Ref."
    }
}
$sourceType = "local"
$resolvedRef = $head
$versionCandidates = @(
    (Join-Path $resolvedSource "VERSION"),
    (Join-Path $kitSourceRoot "VERSION")
)
$versionPath = $versionCandidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
if (-not $versionPath) {
    throw "Local standalone Dev Kit checkout is missing VERSION: $resolvedSource"
}
$version = (Get-Content -Raw -LiteralPath $versionPath).Trim()
if ([string]::IsNullOrWhiteSpace($version)) {
    throw "Local standalone Dev Kit VERSION is empty: $versionPath"
}

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$timestamp = (Get-Date).ToUniversalTime().ToString("yyyyMMdd-HHmmss")
$backupRoot = Join-Path $codexHomePath "backups\codex-dev-kit\$timestamp"
$planned = New-Object System.Collections.Generic.List[object]

function Backup-ExistingFile {
    param([Parameter(Mandatory = $true)][string]$Target)

    if (-not (Test-Path -LiteralPath $Target -PathType Leaf)) {
        return
    }
    $relative = $Target.Substring($codexHomePath.Length).TrimStart('\', '/')
    $backup = Join-Path $backupRoot $relative
    New-Item -ItemType Directory -Path (Split-Path -Parent $backup) -Force | Out-Null
    Copy-Item -LiteralPath $Target -Destination $backup -Force
}

function Set-ManagedTextFile {
    param(
        [Parameter(Mandatory = $true)][string]$Target,
        [Parameter(Mandatory = $true)][string]$Content
    )

    $existing = if (Test-Path -LiteralPath $Target -PathType Leaf) { [System.IO.File]::ReadAllText($Target) } else { $null }
    $action = if ($null -eq $existing) { "create" } elseif ($existing -eq $Content) { "unchanged" } else { "update" }
    $planned.Add([pscustomobject]@{ Action = $action; Path = $Target })
    if (-not $Apply -or $action -eq "unchanged") {
        return
    }
    if ($action -eq "update") {
        Backup-ExistingFile -Target $Target
    }
    New-Item -ItemType Directory -Path (Split-Path -Parent $Target) -Force | Out-Null
    [System.IO.File]::WriteAllText($Target, $Content, $utf8NoBom)
}

function Copy-ManagedTree {
    param(
        [Parameter(Mandatory = $true)][string]$SourceRoot,
        [Parameter(Mandatory = $true)][string]$TargetRoot,
        [string[]]$Extensions = @()
    )

    foreach ($file in Get-ChildItem -LiteralPath $SourceRoot -Recurse -Force -File) {
        if ($Extensions.Count -gt 0 -and $file.Extension.ToLowerInvariant() -notin $Extensions) {
            continue
        }
        $relative = $file.FullName.Substring($SourceRoot.Length).TrimStart('\', '/')
        Set-ManagedTextFile -Target (Join-Path $TargetRoot $relative) -Content ([System.IO.File]::ReadAllText($file.FullName))
    }
}

function Test-LegacyDevKitHookObject {
    param([Parameter(Mandatory = $true)]$HookObject)

    foreach ($field in @("command", "commandWindows")) {
        $property = $HookObject.PSObject.Properties[$field]
        if (-not $property) {
            continue
        }
        $command = ([string]$property.Value).Replace('\', '/')
        $knownRoot = $command -match '(?i)(?:\$\{PLUGIN_ROOT\}|\$env:PLUGIN_ROOT)/' -or $command -match '(?i)/(?:codex-dev-kit(?:/plugins/codex-personal-dev-kit)?|codex-personal-dev-kit)/(?:scripts|hooks)/'
        $knownGuardInvocation = $command -match '(?i)/scripts/feature_guard\.py"?\s+hook(?:\s|$)' -or $command -match '(?i)/(?:scripts|hooks)/pre_tool_guard\.py"?(?:\s|$)'
        if ($knownRoot -and $knownGuardInvocation) {
            return $true
        }
    }
    return $false
}

$legacyAgentPaths = @(Get-ChildItem -LiteralPath (Join-Path $codexHomePath "agents") -Filter "codex-kit-*.toml" -File -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
$existingSourcePath = Join-Path $codexHomePath "codex-dev-kit\source.json"
$legacySource = $null
if (Test-Path -LiteralPath $existingSourcePath -PathType Leaf) {
    try {
        $candidateSource = Get-Content -Raw $existingSourcePath | ConvertFrom-Json
        if ($candidateSource.mode -ne "standalone" -or $candidateSource.schemaVersion -ne 2) {
            $legacySource = $candidateSource
        }
    }
    catch {
        $legacySource = [pscustomobject]@{}
    }
}

$globalHooksPath = Join-Path $codexHomePath "hooks.json"
$legacyGlobalHook = $false
$globalHooksDocument = $null
$legacyGlobalHookHandlerCount = 0
if (Test-Path -LiteralPath $globalHooksPath -PathType Leaf) {
    $globalHooksText = [System.IO.File]::ReadAllText($globalHooksPath)
    if ($globalHooksText -match '(?i)codex-dev-kit|feature_guard\.py|pre_tool_guard\.py') {
        try {
            $globalHooksDocument = $globalHooksText | ConvertFrom-Json
        }
        catch {
            throw "Global hooks.json contains legacy Dev Kit text but is not valid JSON. Review it manually before standalone installation: $globalHooksPath"
        }
        if ($globalHooksDocument.hooks) {
            foreach ($eventProperty in @($globalHooksDocument.hooks.PSObject.Properties)) {
                foreach ($entry in @($eventProperty.Value)) {
                    if (Test-LegacyDevKitHookObject -HookObject $entry) {
                        $legacyGlobalHookHandlerCount++
                    }
                    foreach ($handler in @($entry.hooks)) {
                        if (Test-LegacyDevKitHookObject -HookObject $handler) {
                            $legacyGlobalHookHandlerCount++
                        }
                    }
                }
            }
        }
        if ($legacyGlobalHookHandlerCount -eq 0) {
            throw "Global hooks.json contains an unrecognized legacy Dev Kit reference. Review it manually before standalone installation: $globalHooksPath"
        }
        $legacyGlobalHook = $true
    }
}

$legacyPluginName = if ($legacySource -and -not [string]::IsNullOrWhiteSpace([string]$legacySource.plugin)) { [string]$legacySource.plugin } else { "codex-personal-dev-kit" }

$legacyPaths = @($legacyAgentPaths)
if ($legacyGlobalHook) { $legacyPaths += $globalHooksPath }
if ($legacySource) { $legacyPaths += $existingSourcePath }
if ($legacyPaths.Count -gt 0) {
    foreach ($legacyPath in $legacyPaths | Sort-Object -Unique) {
        $planned.Add([pscustomobject]@{ Action = "migrate-legacy"; Path = $legacyPath })
    }
    if (-not $MigrateLegacy) {
        $planned | Format-Table -AutoSize
        throw "Legacy Codex Dev Kit state was detected. Re-run with -MigrateLegacy only after reviewing the listed backup/removal targets."
    }
}

$legacyPluginSelectors = @()
$codexCommand = $null
if (Test-Path -LiteralPath $codexHomePath -PathType Container) {
    . (Join-Path $PSScriptRoot "resolve-codex-cli.ps1")
    $codexCommand = Resolve-CodexCli
    if (-not $codexCommand) {
        throw "Unable to verify whether the legacy Plugin is installed. Codex CLI is required before standalone installation."
    }
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
        if ($pluginListExitCode -ne 0) {
            throw "Unable to query installed Codex Plugins before standalone installation."
        }
        $legacyPluginNames = @("codex-personal-dev-kit", $legacyPluginName) | Sort-Object -Unique
        foreach ($line in $pluginListText -split "`r?`n") {
            $selectorMatch = [regex]::Match($line, '^\s*([^\s@]+@[^\s]+)\s+installed(?:\s|,|$)', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
            if (-not $selectorMatch.Success) {
                continue
            }
            $selector = $selectorMatch.Groups[1].Value
            $pluginName = $selector.Substring(0, $selector.IndexOf('@'))
            if ($pluginName -in $legacyPluginNames) {
                $legacyPluginSelectors += $selector
            }
        }
        $legacyPluginSelectors = @($legacyPluginSelectors | Sort-Object -Unique)
    }
    finally {
        if ($null -eq $previousCodexHome) { Remove-Item Env:CODEX_HOME -ErrorAction SilentlyContinue } else { $env:CODEX_HOME = $previousCodexHome }
    }
}

if ($legacyPluginSelectors.Count -gt 0) {
    foreach ($selector in $legacyPluginSelectors) {
        $planned.Add([pscustomobject]@{ Action = "remove-legacy-plugin"; Path = $selector })
    }
    if (-not $MigrateLegacy) {
        $planned | Format-Table -AutoSize
        throw "The legacy Plugin is still installed. Re-run with -MigrateLegacy to remove it before standalone installation."
    }
}

$agentsTemplate = [System.IO.File]::ReadAllText((Join-Path $kitSourceRoot "assets\standalone\AGENTS.md"))
$agentsBlock = $agentsTemplate.Replace("{{WORKSPACE_AGENTS_PATH}}", $workspaceAgents)
$agentsTarget = Join-Path $codexHomePath "AGENTS.md"
$currentAgents = if (Test-Path -LiteralPath $agentsTarget -PathType Leaf) { [System.IO.File]::ReadAllText($agentsTarget) } else { "" }
$startMarker = "<!-- codex-dev-kit:start -->"
$endMarker = "<!-- codex-dev-kit:end -->"
$startMarkerCount = ([regex]::Matches($currentAgents, [regex]::Escape($startMarker))).Count
$endMarkerCount = ([regex]::Matches($currentAgents, [regex]::Escape($endMarker))).Count
if ($startMarkerCount -ne $endMarkerCount -or $startMarkerCount -gt 1) {
    throw "Global AGENTS.md has incomplete or duplicate Codex Dev Kit managed markers. Restore or remove the damaged managed block before installation: $agentsTarget"
}
$startIndex = $currentAgents.IndexOf($startMarker, [System.StringComparison]::Ordinal)
$endIndex = $currentAgents.IndexOf($endMarker, [System.StringComparison]::Ordinal)
if ($startMarkerCount -eq 1 -and $endIndex -le $startIndex) {
    throw "Global AGENTS.md has Codex Dev Kit managed markers in the wrong order. Restore the file before installation: $agentsTarget"
}
if ($startIndex -ge 0 -and $endIndex -gt $startIndex) {
    $afterEnd = $endIndex + $endMarker.Length
    $mergedAgents = $currentAgents.Substring(0, $startIndex) + $agentsBlock + $currentAgents.Substring($afterEnd)
}
elseif ([string]::IsNullOrWhiteSpace($currentAgents)) {
    $mergedAgents = $agentsBlock
}
else {
    $mergedAgents = $currentAgents.TrimEnd() + [Environment]::NewLine + [Environment]::NewLine + $agentsBlock
}
Set-ManagedTextFile -Target $agentsTarget -Content $mergedAgents

$kitTargetRoot = Join-Path $codexHomePath "codex-dev-kit"
Set-ManagedTextFile -Target (Join-Path $kitTargetRoot "VERSION") -Content ($version + [Environment]::NewLine)
Set-ManagedTextFile -Target (Join-Path $kitTargetRoot "config.fragment.toml") -Content ([System.IO.File]::ReadAllText((Join-Path $kitSourceRoot "assets\global-profile\config.fragment.toml")))

$sourceConfig = [ordered]@{
    schemaVersion = 2
    mode = "standalone"
    sourceType = $sourceType
    source = $resolvedSource
    ref = $resolvedRef
    version = $version
    workspaceRoot = $workspacePath
} | ConvertTo-Json
Set-ManagedTextFile -Target (Join-Path $kitTargetRoot "source.json") -Content ($sourceConfig + [Environment]::NewLine)

Copy-ManagedTree -SourceRoot (Join-Path $kitSourceRoot "scripts") -TargetRoot (Join-Path $kitTargetRoot "scripts") -Extensions @(".py", ".ps1")
Copy-ManagedTree -SourceRoot (Join-Path $kitSourceRoot "assets\project-template") -TargetRoot (Join-Path $kitTargetRoot "assets\project-template")
Copy-ManagedTree -SourceRoot (Join-Path $kitSourceRoot "assets\workspace-template") -TargetRoot (Join-Path $kitTargetRoot "assets\workspace-template")
Copy-ManagedTree -SourceRoot (Join-Path $kitSourceRoot "skills") -TargetRoot (Join-Path $codexHomePath "skills")

$planned | Format-Table -AutoSize
if (-not $Apply) {
    Write-Host "Preview only. Re-run with -Apply to install the short global AGENTS block, standalone Skills, central runtime, and templates."
    exit 0
}

$requiredInstalledPaths = @(
    $agentsTarget,
    (Join-Path $kitTargetRoot "VERSION"),
    (Join-Path $kitTargetRoot "source.json"),
    (Join-Path $kitTargetRoot "scripts\feature_guard.py"),
    (Join-Path $kitTargetRoot "scripts\pre_tool_guard.py"),
    (Join-Path $kitTargetRoot "scripts\resolve-skill.ps1"),
    (Join-Path $codexHomePath "skills\codex-development-assistant\SKILL.md"),
    (Join-Path $codexHomePath "skills\orchestrate-codex-team\SKILL.md"),
    (Join-Path $codexHomePath "skills\research-and-reuse\SKILL.md"),
    (Join-Path $codexHomePath "skills\integrate-codex-projects\SKILL.md")
)
$missingInstalledPaths = @($requiredInstalledPaths | Where-Object { -not (Test-Path -LiteralPath $_ -PathType Leaf) })
if ($missingInstalledPaths.Count -gt 0) {
    throw "Standalone files were not fully prepared; legacy state was not removed: $($missingInstalledPaths -join ', ')"
}
$installedSourceCheck = Get-Content -Raw (Join-Path $kitTargetRoot "source.json") | ConvertFrom-Json
if ($installedSourceCheck.schemaVersion -ne 2 -or $installedSourceCheck.mode -ne "standalone") {
    throw "Standalone source metadata validation failed; legacy state was not removed."
}

if ($MigrateLegacy) {
    foreach ($legacyAgentPath in $legacyAgentPaths) {
        Backup-ExistingFile -Target $legacyAgentPath
        Remove-Item -LiteralPath $legacyAgentPath -Force
    }
    if ($legacyGlobalHook) {
        Backup-ExistingFile -Target $globalHooksPath
        $remainingHookEntryCount = 0
        foreach ($eventProperty in @($globalHooksDocument.hooks.PSObject.Properties)) {
            $remainingEntries = @()
            foreach ($entry in @($eventProperty.Value)) {
                if (Test-LegacyDevKitHookObject -HookObject $entry) {
                    continue
                }
                $hooksProperty = $entry.PSObject.Properties["hooks"]
                if ($hooksProperty) {
                    $remainingHandlers = @($hooksProperty.Value | Where-Object { -not (Test-LegacyDevKitHookObject -HookObject $_) })
                    if ($remainingHandlers.Count -eq 0) {
                        continue
                    }
                    $hooksProperty.Value = $remainingHandlers
                }
                $remainingEntries += $entry
            }
            $eventProperty.Value = $remainingEntries
            $remainingHookEntryCount += $remainingEntries.Count
        }
        if ($remainingHookEntryCount -eq 0) {
            Remove-Item -LiteralPath $globalHooksPath -Force
        }
        else {
            $cleanedHooks = $globalHooksDocument | ConvertTo-Json -Depth 100
            [System.IO.File]::WriteAllText($globalHooksPath, $cleanedHooks + [Environment]::NewLine, $utf8NoBom)
        }
    }
    if ($legacyPluginSelectors.Count -gt 0) {
        $previousCodexHome = $env:CODEX_HOME
        try {
            $env:CODEX_HOME = $codexHomePath
            foreach ($selector in $legacyPluginSelectors) {
                & $codexCommand.Path plugin remove $selector
                if ($LASTEXITCODE -ne 0) { throw "Standalone is installed, but removing legacy Plugin $selector failed. Retry migration before starting a new Codex task." }
            }
        }
        finally {
            if ($null -eq $previousCodexHome) { Remove-Item Env:CODEX_HOME -ErrorAction SilentlyContinue } else { $env:CODEX_HOME = $previousCodexHome }
        }
    }
}

Write-Host "Standalone Codex Dev Kit installed at $kitTargetRoot"
Write-Host "No Plugin, global Hook, custom agent file, or config.toml change was installed."
Write-Host "Backups of changed managed files, if any, are under $backupRoot"
Write-Host "Review codex-dev-kit\config.fragment.toml before applying native subagent concurrency/reasoning settings; the fragment does not pin a child model."
if ($legacyLunaDefaultDetected) {
    Write-Warning "Legacy Luna child-model default remains in $workspaceConfig. It was not removed because it may be a deliberate user choice. Use bootstrap-workspace.ps1 -Apply -RemoveLegacyLunaDefault only after confirming its origin."
}
if ($legacyRoutingTextDetected) {
    Write-Warning "Legacy subagent-routing text remains in $workspaceAgents. Update the detailed workspace rules before claiming task-local model routing or list_agents degradation is active."
}
Write-Host "Fully exit Codex Desktop and reopen it, then create a new task so the short global instructions and standalone Skills reload."
Write-Host "Creating a task inside an already-running app-server may keep an older Skill catalog; disk files alone do not prove that the task discovered the Skill."
