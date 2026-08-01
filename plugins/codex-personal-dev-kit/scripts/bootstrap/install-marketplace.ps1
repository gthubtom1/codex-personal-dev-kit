[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Marketplace,
    [Parameter(Mandatory = $true)][string]$Ref,
    [string]$MarketplaceName = "codex-dev-kit",
    [string]$PluginName = "codex-personal-dev-kit",
    [switch]$Apply
)

$ErrorActionPreference = "Stop"
if ($Ref.ToLowerInvariant() -in @("main", "master", "head", "latest")) {
    throw "Use a fixed release tag or commit, not '$Ref'."
}
if ($Marketplace -notmatch "^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$" -and $Marketplace -notmatch "^https://") {
    throw "Marketplace must be GitHub owner/repo shorthand or an HTTPS Git URL."
}

Write-Host "Planned commands:"
Write-Host "codex plugin marketplace add $Marketplace --ref $Ref"
Write-Host "codex plugin add $PluginName@$MarketplaceName"
if (-not $Apply) {
    Write-Host "Preview only. Re-run with -Apply after reviewing the pinned source."
    exit 0
}

$codex = Get-Command codex -ErrorAction Stop
& $codex.Source plugin marketplace add $Marketplace --ref $Ref
if ($LASTEXITCODE -ne 0) { throw "Marketplace installation failed." }
& $codex.Source plugin add "$PluginName@$MarketplaceName"
if ($LASTEXITCODE -ne 0) { throw "Plugin installation failed." }

Write-Host "Plugin installed. Start a new Codex task before using it."
