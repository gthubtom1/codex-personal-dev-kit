[CmdletBinding()]
param(
    [string]$CodexHome,
    [switch]$Apply,
    [string]$Marketplace,
    [string]$Ref,
    [string]$MarketplaceName = "codex-dev-kit"
)

$installer = Join-Path $PSScriptRoot "install.ps1"
$arguments = @{
    Apply = $Apply
    MarketplaceName = $MarketplaceName
}
if (-not [string]::IsNullOrWhiteSpace($CodexHome)) { $arguments.CodexHome = $CodexHome }
if (-not [string]::IsNullOrWhiteSpace($Marketplace)) { $arguments.Marketplace = $Marketplace }
if (-not [string]::IsNullOrWhiteSpace($Ref)) { $arguments.Ref = $Ref }

& $installer @arguments
exit $LASTEXITCODE
