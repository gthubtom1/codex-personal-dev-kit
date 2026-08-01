[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Marketplace,
    [string]$Ref,
    [string]$MarketplaceName = "codex-dev-kit",
    [string]$PluginName = "codex-personal-dev-kit",
    [switch]$Apply
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "resolve-codex-cli.ps1")
$isLocal = Test-Path -LiteralPath $Marketplace -PathType Container
$marketplaceArgument = $Marketplace
if ($isLocal) {
    $marketplaceArgument = [System.IO.Path]::GetFullPath($Marketplace)
    $localMarketplaceFile = Join-Path $marketplaceArgument ".agents\plugins\marketplace.json"
    if (-not (Test-Path -LiteralPath $localMarketplaceFile -PathType Leaf)) {
        throw "Local Marketplace file not found: $localMarketplaceFile"
    }
    $localMarketplaceName = [string]((Get-Content -Raw $localMarketplaceFile | ConvertFrom-Json).name)
    if ($localMarketplaceName -ne $MarketplaceName) {
        throw "Local Marketplace name '$localMarketplaceName' does not match requested name '$MarketplaceName'."
    }
    if (-not [string]::IsNullOrWhiteSpace($Ref)) {
        $git = Get-Command git -ErrorAction SilentlyContinue
        if (-not $git) { throw "Git is required to verify the requested local Marketplace Ref." }
        $localHead = (& $git.Source -C $marketplaceArgument rev-parse HEAD 2>$null | Select-Object -First 1)
        if ($LASTEXITCODE -ne 0 -or $localHead -ne $Ref) {
            throw "Local Marketplace HEAD '$localHead' does not match requested Ref '$Ref'."
        }
    }
}
else {
    if ([string]::IsNullOrWhiteSpace($Ref)) {
        throw "A Git Marketplace requires a fixed release tag or commit Ref."
    }
    if ($Ref.ToLowerInvariant() -in @("main", "master", "head", "latest")) {
        throw "Use a fixed release tag or commit, not '$Ref'."
    }
    if ($Marketplace -notmatch "^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$" -and $Marketplace -notmatch "^https://") {
        throw "Marketplace must be a local directory, GitHub owner/repo shorthand, or an HTTPS Git URL."
    }
}

Write-Host "Planned commands:"
if ($isLocal) {
    Write-Host "codex plugin marketplace add $marketplaceArgument"
}
else {
    Write-Host "codex plugin marketplace add $Marketplace --ref $Ref"
}
Write-Host "codex plugin add $PluginName@$MarketplaceName"
if (-not $Apply) {
    Write-Host "Preview only. Re-run with -Apply after reviewing the pinned source."
    exit 0
}

$codex = Resolve-CodexCli -ErrorIfMissing
if ($isLocal) {
    & $codex.Path plugin marketplace add $marketplaceArgument
}
else {
    & $codex.Path plugin marketplace add $Marketplace --ref $Ref
}
if ($LASTEXITCODE -ne 0) { throw "Marketplace installation failed." }
& $codex.Path plugin add "$PluginName@$MarketplaceName"
if ($LASTEXITCODE -ne 0) { throw "Plugin installation failed." }

Write-Host "Plugin installed. Start a new Codex task before using it."
