[CmdletBinding()]
param(
    [string]$CodexHome,
    [switch]$Apply,
    [string]$Marketplace,
    [string]$Ref,
    [string]$MarketplaceName = "codex-dev-kit"
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($CodexHome)) {
    if (-not [string]::IsNullOrWhiteSpace($env:CODEX_HOME)) {
        $CodexHome = $env:CODEX_HOME
    }
    else {
        $CodexHome = Join-Path ([Environment]::GetFolderPath("UserProfile")) ".codex"
    }
}

$codexHomePath = [System.IO.Path]::GetFullPath($CodexHome)
$filesystemRoot = [System.IO.Path]::GetPathRoot($codexHomePath)
if ($codexHomePath.TrimEnd('\', '/') -eq $filesystemRoot.TrimEnd('\', '/')) {
    throw "Refusing to install into a filesystem root: $codexHomePath"
}

if (([string]::IsNullOrWhiteSpace($Marketplace)) -xor ([string]::IsNullOrWhiteSpace($Ref))) {
    throw "Marketplace and Ref must be provided together."
}
if (-not [string]::IsNullOrWhiteSpace($Ref) -and $Ref.ToLowerInvariant() -in @("main", "master", "head", "latest")) {
    throw "Ref must be a fixed release tag or commit, not '$Ref'."
}

$pluginRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
$assetRoot = Join-Path $pluginRoot "assets\global-profile"
$manifest = Get-Content -Raw (Join-Path $pluginRoot ".codex-plugin\plugin.json") | ConvertFrom-Json
$version = [string]$manifest.version
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

$agentsBlock = [System.IO.File]::ReadAllText((Join-Path $assetRoot "AGENTS.md"))
$agentsTarget = Join-Path $codexHomePath "AGENTS.md"
$currentAgents = if (Test-Path -LiteralPath $agentsTarget -PathType Leaf) { [System.IO.File]::ReadAllText($agentsTarget) } else { "" }
$startMarker = "<!-- codex-dev-kit:start -->"
$endMarker = "<!-- codex-dev-kit:end -->"
$startIndex = $currentAgents.IndexOf($startMarker, [System.StringComparison]::Ordinal)
$endIndex = $currentAgents.IndexOf($endMarker, [System.StringComparison]::Ordinal)
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

Get-ChildItem -LiteralPath (Join-Path $assetRoot "agents") -File | ForEach-Object {
    Set-ManagedTextFile -Target (Join-Path $codexHomePath ("agents\" + $_.Name)) -Content ([System.IO.File]::ReadAllText($_.FullName))
}
Get-ChildItem -LiteralPath (Join-Path $assetRoot "rules") -File | ForEach-Object {
    Set-ManagedTextFile -Target (Join-Path $codexHomePath ("rules\" + $_.Name)) -Content ([System.IO.File]::ReadAllText($_.FullName))
}

$kitStateRoot = Join-Path $codexHomePath "codex-dev-kit"
foreach ($name in @("config.fragment.toml", "config.optional-memories.fragment.toml", "source.example.json")) {
    Set-ManagedTextFile -Target (Join-Path $kitStateRoot $name) -Content ([System.IO.File]::ReadAllText((Join-Path $assetRoot $name)))
}
Set-ManagedTextFile -Target (Join-Path $kitStateRoot "VERSION") -Content ($version + [Environment]::NewLine)

if (-not [string]::IsNullOrWhiteSpace($Marketplace)) {
    $sourceConfig = [ordered]@{
        marketplace = $Marketplace
        ref = $Ref
        marketplaceName = $MarketplaceName
        plugin = "codex-personal-dev-kit"
    } | ConvertTo-Json
    Set-ManagedTextFile -Target (Join-Path $kitStateRoot "source.json") -Content ($sourceConfig + [Environment]::NewLine)
}

$planned | Format-Table -AutoSize
if (-not $Apply) {
    Write-Host "Preview only. Re-run with -Apply to install the managed AGENTS block, agents, rules, and reference fragments."
    exit 0
}

Write-Host "Global profile installed at $codexHomePath"
Write-Host "Backups of changed files, if any, are under $backupRoot"
Write-Host "config.toml was not modified. Review codex-dev-kit\config.fragment.toml manually."
Write-Host "Start a new Codex task so instructions, rules, and agents reload."
