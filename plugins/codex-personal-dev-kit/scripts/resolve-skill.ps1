[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Name,
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

if ($Name -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]*$') {
    throw "Skill name must be a simple name, not a path: $Name"
}

$codexHomePath = [System.IO.Path]::GetFullPath($CodexHome)
$installedPath = Join-Path $codexHomePath ("skills\$Name\SKILL.md")
if (Test-Path -LiteralPath $installedPath -PathType Leaf) {
    Write-Output ([System.IO.Path]::GetFullPath($installedPath))
    exit 0
}

# If a built-in skill is requested, discover it by its actual folder name.
# Never construct a guessed `.system\<name>` path.
$skillsRoot = Join-Path $codexHomePath "skills"
if (Test-Path -LiteralPath $skillsRoot -PathType Container) {
    $candidates = @(
        Get-ChildItem -LiteralPath $skillsRoot -Recurse -Filter "SKILL.md" -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Directory.Name -eq $Name } |
            Select-Object -ExpandProperty FullName
    )
    if ($candidates.Count -eq 1) {
        Write-Output ([System.IO.Path]::GetFullPath($candidates[0]))
        exit 0
    }
    if ($candidates.Count -gt 1) {
        throw "Multiple installed Skills named '$Name' were found. Use the exact path listed by the current Codex task: $($candidates -join '; ')"
    }
}

$sourceMetadataPath = Join-Path $codexHomePath "codex-dev-kit\source.json"
if (Test-Path -LiteralPath $sourceMetadataPath -PathType Leaf) {
    try {
        $source = Get-Content -Raw -LiteralPath $sourceMetadataPath | ConvertFrom-Json
        if ($source.sourceType -eq "local" -and -not [string]::IsNullOrWhiteSpace([string]$source.source)) {
            $sourcePath = Join-Path ([string]$source.source) ("plugins\codex-personal-dev-kit\skills\$Name\SKILL.md")
            if (Test-Path -LiteralPath $sourcePath -PathType Leaf) {
                Write-Output ([System.IO.Path]::GetFullPath($sourcePath))
                exit 0
            }
        }
    }
    catch {
        # Report the normal missing-path error below; do not invent a replacement.
    }
}

throw "Skill '$Name' was not found. Use the exact file locator from the current task; do not prepend '.system'."
