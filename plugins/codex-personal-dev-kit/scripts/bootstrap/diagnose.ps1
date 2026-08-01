[CmdletBinding()]
param(
    [string]$CodexHome
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "resolve-codex-cli.ps1")
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

$installedVersion = if (Test-Path -LiteralPath $versionPath -PathType Leaf) { (Get-Content -Raw $versionPath).Trim() } else { "" }
$source = $null
if (Test-Path -LiteralPath $sourcePath -PathType Leaf) {
    try {
        $source = Get-Content -Raw $sourcePath | ConvertFrom-Json
        Add-Check "Source metadata schema" ($source.schemaVersion -eq 1 -and $source.sourceType -in @("local", "git")) "$($source.sourceType) source"
        Add-Check "Source version matches marker" (-not [string]::IsNullOrWhiteSpace($source.pluginVersion) -and $source.pluginVersion -eq $installedVersion) "source=$($source.pluginVersion); marker=$installedVersion"
    }
    catch {
        Add-Check "Source metadata schema" $false $_.Exception.Message
    }
}

if ($source -and $source.sourceType -eq "local") {
    $localMarketplace = [string]$source.marketplace
    $localExists = Test-Path -LiteralPath $localMarketplace -PathType Container
    Add-Check "Local Marketplace path" $localExists $localMarketplace
    if ($localExists) {
        $marketplaceFile = Join-Path $localMarketplace ".agents\plugins\marketplace.json"
        $marketplaceName = ""
        if (Test-Path -LiteralPath $marketplaceFile -PathType Leaf) {
            try { $marketplaceName = [string]((Get-Content -Raw $marketplaceFile | ConvertFrom-Json).name) } catch { }
        }
        Add-Check "Local Marketplace identity" ($marketplaceName -eq [string]$source.marketplaceName -and -not [string]::IsNullOrWhiteSpace($marketplaceName)) "expected=$($source.marketplaceName); actual=$marketplaceName"
        $git = Get-Command git -ErrorAction SilentlyContinue
        Add-Check "Git for local source" ($null -ne $git) $(if ($git) { $git.Source } else { "git not found" })
        if ($git) {
            $headOutput = @(& $git.Source -C $localMarketplace rev-parse HEAD 2>$null)
            $headExit = $LASTEXITCODE
            $head = if ($headOutput.Count -gt 0) { ([string]$headOutput[0]).Trim() } else { "" }
            $expectedHead = ([string]$source.ref).Trim()
            $headPassed = $headExit -eq 0 -and [string]::Equals($head, $expectedHead, [System.StringComparison]::Ordinal)
            Add-Check "Local source HEAD" $headPassed "expected=$expectedHead; actual=$head"
            $status = (& $git.Source -C $localMarketplace status --porcelain 2>$null) -join [Environment]::NewLine
            Add-Check "Local source working tree" ($LASTEXITCODE -eq 0 -and [string]::IsNullOrWhiteSpace($status)) $(if ([string]::IsNullOrWhiteSpace($status)) { "clean" } else { $status })
        }

        $sourceManifestPath = Join-Path $localMarketplace ("plugins\" + [string]$source.plugin + "\.codex-plugin\plugin.json")
        $sourceManifestVersion = ""
        if (Test-Path -LiteralPath $sourceManifestPath -PathType Leaf) {
            try { $sourceManifestVersion = [string]((Get-Content -Raw $sourceManifestPath | ConvertFrom-Json).version) } catch { }
        }
        Add-Check "Local source plugin version" ($sourceManifestVersion -eq $installedVersion -and -not [string]::IsNullOrWhiteSpace($sourceManifestVersion)) "source=$sourceManifestVersion; marker=$installedVersion"
    }
}
elseif ($source -and $source.sourceType -eq "git") {
    $ref = [string]$source.ref
    $pinned = -not [string]::IsNullOrWhiteSpace($ref) -and $ref.ToLowerInvariant() -notin @("main", "master", "head", "latest")
    Add-Check "Git source fixed Ref" $pinned $ref
}

if ($source -and -not [string]::IsNullOrWhiteSpace($source.marketplaceName) -and -not [string]::IsNullOrWhiteSpace($source.plugin) -and -not [string]::IsNullOrWhiteSpace($installedVersion)) {
    $cachePath = Join-Path $codexHomePath ("plugins\cache\" + [string]$source.marketplaceName + "\" + [string]$source.plugin + "\" + $installedVersion)
    Add-Check "Installed plugin cache version" (Test-Path -LiteralPath $cachePath -PathType Container) $cachePath
}

$codexCommand = Resolve-CodexCli
Add-Check "Runnable Codex CLI" ($null -ne $codexCommand) $(if ($codexCommand) { "$($codexCommand.Version) at $($codexCommand.Path)" } else { "No runnable PATH, CODEX_CLI, or Codex Desktop candidate" })
if ($codexCommand -and $source) {
    $pluginListOutput = & $codexCommand.Path plugin list 2>&1
    $pluginListExit = $LASTEXITCODE
    $pluginListText = ($pluginListOutput | ForEach-Object { [string]$_ }) -join [Environment]::NewLine
    $pluginName = [string]$source.plugin
    $pluginLine = $pluginListOutput | ForEach-Object { [string]$_ } | Where-Object { $_.IndexOf($pluginName, [System.StringComparison]::OrdinalIgnoreCase) -ge 0 } | Select-Object -First 1
    $listed = $pluginListExit -eq 0 -and -not [string]::IsNullOrWhiteSpace($pluginLine) -and $pluginLine -match "installed,\s*enabled"
    Add-Check "Plugin enabled/listed" $listed $(if ($pluginListExit -eq 0) { [string]$pluginLine } else { "codex plugin list failed" })
    $listedVersion = $listed -and -not [string]::IsNullOrWhiteSpace($installedVersion) -and $pluginLine.IndexOf($installedVersion, [System.StringComparison]::OrdinalIgnoreCase) -ge 0
    Add-Check "Active plugin version" $listedVersion "expected=$installedVersion; listing=$pluginLine"
}

$checks | Format-Table -AutoSize
if ($checks.Where({ -not $_.Passed }).Count -gt 0) {
    exit 1
}
