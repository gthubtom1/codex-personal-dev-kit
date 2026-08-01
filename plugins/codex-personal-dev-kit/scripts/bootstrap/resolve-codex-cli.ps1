[CmdletBinding()]
param()

function Resolve-CodexCli {
    [CmdletBinding()]
    param([switch]$ErrorIfMissing)

    $candidates = New-Object System.Collections.Generic.List[string]
    if (-not [string]::IsNullOrWhiteSpace($env:CODEX_CLI)) {
        $candidates.Add($env:CODEX_CLI)
    }

    Get-Command codex -All -ErrorAction SilentlyContinue | ForEach-Object {
        if (-not [string]::IsNullOrWhiteSpace($_.Source)) {
            $candidates.Add($_.Source)
        }
    }

    $localAppData = [Environment]::GetFolderPath("LocalApplicationData")
    if (-not [string]::IsNullOrWhiteSpace($localAppData)) {
        $desktopBinRoot = Join-Path $localAppData "OpenAI\Codex\bin"
        foreach ($name in @("codex.exe", "codex")) {
            $candidates.Add((Join-Path $desktopBinRoot $name))
        }
        if (Test-Path -LiteralPath $desktopBinRoot -PathType Container) {
            Get-ChildItem -LiteralPath $desktopBinRoot -Directory -ErrorAction SilentlyContinue |
                Sort-Object LastWriteTimeUtc -Descending |
                ForEach-Object {
                    foreach ($name in @("codex.exe", "codex")) {
                        $candidates.Add((Join-Path $_.FullName $name))
                    }
                }
        }
    }

    $seen = New-Object System.Collections.Generic.HashSet[string]([System.StringComparer]::OrdinalIgnoreCase)
    foreach ($candidate in $candidates) {
        if ([string]::IsNullOrWhiteSpace($candidate) -or -not $seen.Add($candidate)) {
            continue
        }
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            continue
        }
        try {
            $versionOutput = & $candidate --version 2>&1
            $exitCode = $LASTEXITCODE
        }
        catch {
            continue
        }
        if ($exitCode -eq 0) {
            return [pscustomobject]@{
                Path = [System.IO.Path]::GetFullPath($candidate)
                Version = (($versionOutput | ForEach-Object { [string]$_ }) -join " ").Trim()
            }
        }
    }

    if ($ErrorIfMissing) {
        throw "No runnable Codex CLI was found on PATH, in CODEX_CLI, or in the Codex Desktop local bin directory."
    }
    return $null
}
