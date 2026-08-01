[CmdletBinding()]
param(
    [string]$ProjectRoot = (Get-Location).Path,
    [string]$WorkspaceRoot,
    [string]$CodexHome,
    [switch]$Apply,
    [switch]$InitializeGit,
    [switch]$CreateBaselineCheckpoint
)

$ErrorActionPreference = "Stop"

function Get-SafeFullPath {
    param([Parameter(Mandatory = $true)][string]$Path)

    $full = [System.IO.Path]::GetFullPath($Path)
    $root = [System.IO.Path]::GetPathRoot($full)
    $trimmedFull = $full.TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar)
    $trimmedRoot = $root.TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar)
    if ($trimmedFull -eq $trimmedRoot) {
        throw "Refusing to use a drive or filesystem root as a project directory: $full"
    }
    return $full
}

function Test-UnsafeBaselinePath {
    param([Parameter(Mandatory = $true)][string]$RelativePath)

    $normalized = $RelativePath.Replace('\', '/')
    $leaf = [System.IO.Path]::GetFileName($normalized)
    if ($leaf -match '^\.env(?:\.|$)' -and $leaf -notmatch '^\.env\.(?:example|sample|template)$') {
        return $true
    }
    if ($leaf -match '(?i)\.(?:pem|p12|pfx|key|sqlite|sqlite3|db)$') {
        return $true
    }
    if ($leaf -match '(?i)^(?:credentials?|secrets?|service[-_]?account)(?:\.|[-_]|$)') {
        return $true
    }
    if ($leaf -match '(?i)^(?:\.npmrc|\.pypirc|\.netrc|_netrc|id_rsa(?:\.pub)?|id_ed25519(?:\.pub)?|kubeconfig|google-services\.json|GoogleService-Info\.plist)$') {
        return $true
    }
    if ($leaf -match '(?i)\.(?:kdbx|jks|keystore|mobileprovision)$') {
        return $true
    }
    if ($leaf -match '(?i)(?:^|[-_])credentials?\.json$') {
        return $true
    }
    return $normalized -match '(?i)(?:^|/)(?:node_modules|vendor|dist|build|coverage|target|__pycache__|\.venv|venv|\.next|\.nuxt|\.svelte-kit|\.cache|\.pytest_cache|\.mypy_cache|\.ruff_cache|\.gradle|bin|obj)(?:/|$)'
}

function Test-UnsafeBaselineContent {
    param(
        [Parameter(Mandatory = $true)][string]$ProjectRoot,
        [Parameter(Mandatory = $true)][string]$RelativePath
    )

    $fullPath = Join-Path $ProjectRoot $RelativePath
    if (-not (Test-Path -LiteralPath $fullPath -PathType Leaf)) {
        return $false
    }
    $file = Get-Item -LiteralPath $fullPath
    if ($file.Length -gt 16MB) {
        try {
            $stream = [System.IO.File]::OpenRead($fullPath)
            try {
                $sample = New-Object byte[] 4096
                $sampleLength = $stream.Read($sample, 0, $sample.Length)
            }
            finally {
                $stream.Dispose()
            }
            if (@($sample[0..([Math]::Max(0, $sampleLength - 1))]) -contains 0) {
                return $false
            }
        }
        catch {
            return $true
        }
        return $true
    }
    try {
        $bytes = [System.IO.File]::ReadAllBytes($fullPath)
        if ($bytes -contains 0) {
            return $false
        }
        $text = [System.Text.Encoding]::UTF8.GetString($bytes)
    }
    catch {
        return $false
    }

    $strongPatterns = @(
        '-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
        '\bAKIA[0-9A-Z]{16}\b',
        '\bAIza[0-9A-Za-z_-]{35}\b',
        '\bgh[pousr]_[A-Za-z0-9]{30,}\b',
        '\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b',
        '\bxox[baprs]-[A-Za-z0-9-]{20,}\b',
        '"type"\s*:\s*"service_account"',
        '"private_key"\s*:\s*"-----BEGIN'
    )
    if ($strongPatterns | Where-Object { $text -match $_ }) {
        return $true
    }

    $generic = [regex]::Match($text, '(?im)(?:^\s*|[,{]\s*)["'']?(?:api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|private[_-]?key|password|secret)["'']?\s*[:=]\s*["'']?([^\s"'']{16,})')
    if (-not $generic.Success) {
        return $false
    }
    $value = $generic.Groups[1].Value
    return $value -notmatch '(?i)(?:example|sample|placeholder|changeme|replace[-_]?me|your[-_]|dummy|test[-_]?only)'
}

$projectPath = Get-SafeFullPath -Path $ProjectRoot
$pluginRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$templateRoot = Join-Path $pluginRoot "assets\project-template"
if (-not (Test-Path -LiteralPath $templateRoot -PathType Container)) {
    throw "Project template not found: $templateRoot"
}

if ([string]::IsNullOrWhiteSpace($CodexHome)) {
    $CodexHome = if (-not [string]::IsNullOrWhiteSpace($env:CODEX_HOME)) { $env:CODEX_HOME } else { Join-Path ([Environment]::GetFolderPath("UserProfile")) ".codex" }
}
$codexHomePath = [System.IO.Path]::GetFullPath($CodexHome)
$hookRuntimeRoot = $pluginRoot
$installedRuntimeRoot = Join-Path $codexHomePath "codex-dev-kit"
$installedSourceMetadata = Join-Path $installedRuntimeRoot "source.json"
if (Test-Path -LiteralPath $installedSourceMetadata -PathType Leaf) {
    try {
        $installedSource = Get-Content -Raw $installedSourceMetadata | ConvertFrom-Json
        $requiredRuntimeFiles = @("scripts\feature_guard.py", "scripts\pre_tool_guard.py")
        $runtimeComplete = $installedSource.mode -eq "standalone" -and -not ($requiredRuntimeFiles | Where-Object { -not (Test-Path -LiteralPath (Join-Path $installedRuntimeRoot $_) -PathType Leaf) })
        if ($runtimeComplete) {
            $hookRuntimeRoot = $installedRuntimeRoot
        }
    }
    catch { }
}

$projectName = Split-Path -Leaf $projectPath
if ([string]::IsNullOrWhiteSpace($projectName)) {
    throw "Unable to determine the project name from: $projectPath"
}

if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    $projectParent = Split-Path -Parent $projectPath
    if ((Split-Path -Leaf $projectParent) -eq "projects") {
        $WorkspaceRoot = Split-Path -Parent $projectParent
    }
    else {
        $sourceMetadataPath = Join-Path $pluginRoot "source.json"
        if (Test-Path -LiteralPath $sourceMetadataPath -PathType Leaf) {
            try { $WorkspaceRoot = [string]((Get-Content -Raw $sourceMetadataPath | ConvertFrom-Json).workspaceRoot) } catch { }
        }
    }
}
if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    throw "WorkspaceRoot is required when the project is not under a projects directory and no standalone source metadata is available."
}
$workspacePath = Get-SafeFullPath -Path $WorkspaceRoot
$workspaceAgentsPath = Join-Path $workspacePath "AGENTS.md"

$templateFiles = Get-ChildItem -LiteralPath $templateRoot -Recurse -Force -File
$actions = foreach ($source in $templateFiles) {
    $relative = $source.FullName.Substring($templateRoot.Length).TrimStart('\', '/')
    $destination = Join-Path $projectPath $relative
    [pscustomobject]@{
        Action = if (Test-Path -LiteralPath $destination) { "keep" } else { "create" }
        Path = $destination
        Source = $source.FullName
    }
}

$actions | Select-Object Action, Path | Format-Table -AutoSize
if (-not $Apply) {
    Write-Host "Preview only. Re-run with -Apply after checking the target paths."
    if ($InitializeGit -or $CreateBaselineCheckpoint) {
        Write-Host "Git initialization would run only after template creation."
    }
    if ($CreateBaselineCheckpoint) {
        Write-Host "A local baseline recovery point would be created after generated and sensitive paths are checked."
    }
    exit 0
}

New-Item -ItemType Directory -Path $projectPath -Force | Out-Null
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
foreach ($action in $actions) {
    if ($action.Action -ne "create") {
        continue
    }
    $destinationDirectory = Split-Path -Parent $action.Path
    New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null
    $content = [System.IO.File]::ReadAllText($action.Source)
    $content = $content.Replace("{{PROJECT_NAME}}", $projectName)
    $content = $content.Replace("{{WORKSPACE_AGENTS_PATH}}", $workspaceAgentsPath)
    $content = $content.Replace("{{CODEX_DEV_KIT_ROOT_JSON}}", $hookRuntimeRoot.Replace('\', '\\'))
    $content = $content.Replace("{{CODEX_DEV_KIT_ROOT_POSIX}}", $hookRuntimeRoot.Replace('\', '/'))
    [System.IO.File]::WriteAllText($action.Path, $content, $utf8NoBom)
}

if ($CreateBaselineCheckpoint) {
    $InitializeGit = $true
}

if ($InitializeGit) {
    $git = Get-Command git -ErrorAction SilentlyContinue
    if (-not $git) {
        throw "Git is not available on PATH. Templates were created, but Git was not initialized."
    }

    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "SilentlyContinue"
        $existingRoot = (& $git.Source -C $projectPath rev-parse --show-toplevel 2>$null)
        $existingRootExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    if ($existingRootExitCode -eq 0) {
        $existingFull = [System.IO.Path]::GetFullPath(($existingRoot | Select-Object -First 1))
        if ($existingFull.TrimEnd('\', '/') -ne $projectPath.TrimEnd('\', '/')) {
            throw "The project is already inside another Git repository: $existingFull"
        }
        Write-Host "Git repository already exists at $existingFull"
    }
    else {
        & $git.Source -C $projectPath init -b main
        if ($LASTEXITCODE -ne 0) {
            & $git.Source -C $projectPath init
            if ($LASTEXITCODE -ne 0) {
                throw "git init failed for $projectPath"
            }
            & $git.Source -C $projectPath branch -M main
        }
    }

    if ($CreateBaselineCheckpoint) {
        $previousErrorActionPreference = $ErrorActionPreference
        try {
            $ErrorActionPreference = "SilentlyContinue"
            & $git.Source -C $projectPath rev-parse --verify HEAD *> $null
            $hasHead = $LASTEXITCODE -eq 0
        }
        finally {
            $ErrorActionPreference = $previousErrorActionPreference
        }

        if ($hasHead) {
            Write-Host "Git history already exists. The existing baseline was preserved."
        }
        else {
            $candidatePaths = @(
                & $git.Source -C $projectPath ls-files --others --exclude-standard
                & $git.Source -C $projectPath diff --cached --name-only
            ) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Sort-Object -Unique
            $unsafePaths = @($candidatePaths | Where-Object { Test-UnsafeBaselinePath -RelativePath $_ })
            if ($unsafePaths.Count -gt 0) {
                $preview = ($unsafePaths | Select-Object -First 12) -join ", "
                if ($unsafePaths.Count -gt 12) { $preview += ", ..." }
                throw "Baseline checkpoint stopped because generated, sensitive, or local-data paths are not ignored: $preview. Review .gitignore, then run the bootstrap again."
            }
            $secretContentPaths = @($candidatePaths | Where-Object { Test-UnsafeBaselineContent -ProjectRoot $projectPath -RelativePath $_ })
            if ($secretContentPaths.Count -gt 0) {
                $preview = ($secretContentPaths | Select-Object -First 12) -join ", "
                if ($secretContentPaths.Count -gt 12) { $preview += ", ..." }
                throw "Baseline checkpoint stopped because files appear to contain credentials/private keys or are oversized text that needs review: $preview. Remove the secret, ignore the local-only file, or review the oversized text before running the bootstrap again."
            }

            & $git.Source -C $projectPath add -A -- .
            if ($LASTEXITCODE -ne 0) { throw "Unable to stage the initial project baseline." }
            & $git.Source -C $projectPath diff --cached --quiet
            if ($LASTEXITCODE -eq 0) {
                Write-Host "No project files needed an initial baseline checkpoint."
            }
            elseif ($LASTEXITCODE -eq 1) {
                & $git.Source -c user.name="Codex Dev Kit" -c user.email="codex-dev-kit@local.invalid" -C $projectPath commit --no-gpg-sign -m "checkpoint: initialize project"
                if ($LASTEXITCODE -ne 0) { throw "Unable to create the initial local checkpoint." }
                Write-Host "Created the initial local recovery point."
            }
            else {
                throw "Unable to inspect the initial project baseline."
            }
        }
    }
}

Write-Host "Project bootstrap complete. Existing files were preserved."
