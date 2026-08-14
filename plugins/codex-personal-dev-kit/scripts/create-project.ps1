[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ProjectName,
    [string]$WorkspaceRoot = (Get-Location).Path,
    [string]$TaskId,
    [switch]$Apply
)

$ErrorActionPreference = "Stop"

function Test-RouteGateMark {
    param([Parameter(Mandatory = $true)][string]$TaskId)

    $gateDir = Join-Path ([Environment]::GetFolderPath("UserProfile")) ".route-gate"
    if (Test-Path -LiteralPath (Join-Path $gateDir "DISABLED")) {
        Write-Output "逃生模式开着（门禁已关），这次放行。要恢复：删除 ~/.route-gate/DISABLED 或双击桌面恢复。"
        return
    }
    $decisionPath = Join-Path $gateDir ($TaskId + "\decision.json")
    if (-not (Test-Path -LiteralPath $decisionPath -PathType Leaf)) {
        Write-Output "这个活还没走分派，我先不直接开工。先运行 route.ps1 领个号（约 1 秒），领完我马上接着干。"
        exit 1
    }
    try {
        $decision = [System.IO.File]::ReadAllText($decisionPath) | ConvertFrom-Json
    }
    catch {
        Write-Output "分派标记读不出来，我先不直接开工。先运行 route.ps1 领个号（约 1 秒），领完我马上接着干。"
        exit 1
    }
    if ([string]$decision.decision -eq "ask") {
        Write-Output "这个任务的方向还没选定，先把路由那句 1/2/3 回掉。"
        exit 1
    }
    if ([string]$decision.task_id -ne $TaskId -or [string]$decision.decision -ne "codex-personal-dev-kit") {
        Write-Output "这个任务的分派结果不是走我这条流程。先运行 route.ps1 确认分派，它会告诉你走哪条流程。"
        exit 1
    }
    $routeVersion = [string]$decision.route_version
    if (-not [string]::IsNullOrWhiteSpace($routeVersion) -and $routeVersion -ne "1.0") {
        Write-Output "分派标记的版本和当前路由版本对不上，我先停一下。重新运行 route.ps1（约 1 秒）更新标记，我马上接着干。"
        exit 1
    }
    $routeStamp = $null
    try { $routeStamp = [DateTime]$decision.created_at } catch { }
    if ($null -ne $routeStamp) {
        $alreadyStarted = (Test-Path -LiteralPath (Join-Path $WorkspaceRoot "workspace.json") -PathType Leaf)
        if (-not $alreadyStarted -and (Get-Date).ToUniversalTime() - $routeStamp -gt [TimeSpan]::FromHours(12)) {
            Write-Output "分派标记已经过期了，我先停一下。重新运行 route.ps1（约 1 秒）更新标记，我马上接着干。"
            exit 1
        }
    }
}

if ($PSBoundParameters.ContainsKey('TaskId')) {
    Test-RouteGateMark -TaskId $TaskId
}

$workspacePath = [System.IO.Path]::GetFullPath($WorkspaceRoot)
$workspaceConfigPath = Join-Path $workspacePath "workspace.json"
$requiredWorkspacePaths = @(
    $workspaceConfigPath,
    (Join-Path $workspacePath "AGENTS.md")
)
$workspaceNeedsRepair = @($requiredWorkspacePaths | Where-Object { -not (Test-Path -LiteralPath $_ -PathType Leaf) }).Count -gt 0
if ($workspaceNeedsRepair) {
    if (-not $Apply) {
        Write-Host "The mother-folder contract is incomplete. Apply mode will initialize or repair it before creating the project."
        Write-Host "Preview only. Re-run with -Apply to initialize the workspace, create templates, initialize Git, and make a local baseline checkpoint."
        exit 0
    }
    $bootstrapWorkspace = Join-Path $PSScriptRoot "bootstrap-workspace.ps1"
    & $bootstrapWorkspace -WorkspaceRoot $workspacePath -Apply
    $missingAfterRepair = @($requiredWorkspacePaths | Where-Object { -not (Test-Path -LiteralPath $_ -PathType Leaf) })
    if ($missingAfterRepair.Count -gt 0) {
        throw "Mother-folder initialization completed with required files still missing: $($missingAfterRepair -join ', ')"
    }
}

$workspaceConfig = Get-Content -Raw -LiteralPath $workspaceConfigPath | ConvertFrom-Json
$projectsDirectory = [string]$workspaceConfig.projectsDirectory
if ([string]::IsNullOrWhiteSpace($projectsDirectory)) {
    throw "workspace.json does not define projectsDirectory."
}

$slug = $ProjectName.Trim()
$slug = [regex]::Replace($slug, '[<>:"/\\|?*]', '-')
$slug = [regex]::Replace($slug, '\s+', '-')
$slug = [regex]::Replace($slug, '-{2,}', '-')
$slug = $slug.Trim(' ', '.', '-')
if ([string]::IsNullOrWhiteSpace($slug)) {
    throw "ProjectName does not contain a safe folder name."
}
if ($slug.ToUpperInvariant() -in @("CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "LPT1", "LPT2", "LPT3")) {
    throw "ProjectName resolves to a reserved Windows folder name: $slug"
}

$projectsRoot = [System.IO.Path]::GetFullPath((Join-Path $workspacePath $projectsDirectory))
$projectPath = [System.IO.Path]::GetFullPath((Join-Path $projectsRoot $slug))
$prefix = $projectsRoot.TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
if (-not $projectPath.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Resolved project path escaped the projects directory: $projectPath"
}
if (Test-Path -LiteralPath $projectPath) {
    throw "Project folder already exists: $projectPath"
}

Write-Host "Project folder: $projectPath"
if (-not $Apply) {
    Write-Host "Preview only. Re-run with -Apply to create templates, initialize Git, and make a local baseline checkpoint."
    exit 0
}

New-Item -ItemType Directory -Path $projectsRoot -Force | Out-Null
$bootstrapProject = Join-Path $PSScriptRoot "bootstrap-project.ps1"
& $bootstrapProject -ProjectRoot $projectPath -WorkspaceRoot $workspacePath -Apply -InitializeGit -CreateBaselineCheckpoint
if ($LASTEXITCODE -ne 0) {
    throw "Project bootstrap failed."
}

Write-Host "Project created with a local recovery point."
Write-Host "Next: open '$projectPath' as the Codex working folder and start a new task."
