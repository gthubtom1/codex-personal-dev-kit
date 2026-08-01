[CmdletBinding()]
param(
    [string]$CodexHome,
    [string]$WorkspaceRoot,
    [switch]$Apply,
    [switch]$MigrateLegacy,
    [string]$Source,
    [string]$Ref
)

$resolvedCodexHome = if (-not [string]::IsNullOrWhiteSpace($CodexHome)) {
    [System.IO.Path]::GetFullPath($CodexHome)
}
elseif (-not [string]::IsNullOrWhiteSpace($env:CODEX_HOME)) {
    [System.IO.Path]::GetFullPath($env:CODEX_HOME)
}
else {
    [System.IO.Path]::GetFullPath((Join-Path ([Environment]::GetFolderPath("UserProfile")) ".codex"))
}

$sourceMetadataPath = Join-Path $resolvedCodexHome "codex-dev-kit\source.json"
$sourceMetadata = $null
if (Test-Path -LiteralPath $sourceMetadataPath -PathType Leaf) {
    try { $sourceMetadata = Get-Content -Raw $sourceMetadataPath | ConvertFrom-Json } catch { }
}

if ([string]::IsNullOrWhiteSpace($Source)) {
    if (-not (Test-Path -LiteralPath $sourceMetadataPath -PathType Leaf)) {
        throw "Standalone source metadata was not found. Pass -Source with the verified local Dev Kit checkout: $sourceMetadataPath"
    }
    if ($sourceMetadata.mode -ne "standalone" -or $sourceMetadata.sourceType -ne "local" -or [string]::IsNullOrWhiteSpace([string]$sourceMetadata.source)) {
        throw "Standalone source metadata is invalid: $sourceMetadataPath"
    }
    $Source = [string]$sourceMetadata.source
    if ([string]::IsNullOrWhiteSpace($Ref)) {
        $Ref = [string]$sourceMetadata.ref
    }
}

if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    if ($sourceMetadata -and -not [string]::IsNullOrWhiteSpace([string]$sourceMetadata.workspaceRoot)) {
        $WorkspaceRoot = [string]$sourceMetadata.workspaceRoot
    }
    else {
        $WorkspaceRoot = "D:\开发"
    }
}

$installer = Join-Path $PSScriptRoot "install.ps1"
$arguments = @{
    Apply = $Apply
    WorkspaceRoot = $WorkspaceRoot
    CodexHome = $resolvedCodexHome
    Source = $Source
    MigrateLegacy = $MigrateLegacy
}
if (-not [string]::IsNullOrWhiteSpace($Ref)) { $arguments.Ref = $Ref }

& $installer @arguments
exit $LASTEXITCODE
