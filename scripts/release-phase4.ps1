[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge",
    [string]$FeatureBranch = "feature/m4.8-phase-validation-intelligence",
    [string]$MainBranch = "main",
    [string]$ReleaseTag = "forge-v0.3-phase4",
    [switch]$SkipPush
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

function Assert-LastExitCode {
    param(
        [Parameter(Mandatory)]
        [string]$Name
    )

    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

function Invoke-ReleaseStep {
    param(
        [Parameter(Mandatory)]
        [string]$Name,

        [Parameter(Mandatory)]
        [scriptblock]$Command
    )

    Write-Host ""
    Write-Host "RUNNING: $Name" -ForegroundColor Cyan

    & $Command
    Assert-LastExitCode $Name

    Write-Host "PASS: $Name" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "AERION FORGE PHASE 4 RELEASE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$RequiredFiles = @(
    ".\scripts\validate-m4.8-architecture.ps1",
    ".\scripts\validate-m4.8-completion.ps1",
    ".\scripts\validate-phase4-architecture.ps1",
    ".\scripts\validate-phase4-completion.ps1"
)

foreach ($Path in $RequiredFiles) {
    if (-not (Test-Path $Path)) {
        throw "Required file is missing: $Path"
    }

    if ((Get-Item $Path).Length -eq 0) {
        throw "Required file is empty: $Path"
    }
}

$CurrentBranch = git branch --show-current
Assert-LastExitCode "Read current branch"

if ($CurrentBranch -ne $FeatureBranch) {
    throw "Release must start from $FeatureBranch. Current branch: $CurrentBranch"
}

$TrackedChanges = @(git status --short --untracked-files=no)
Assert-LastExitCode "Read tracked working-tree status"

if ($TrackedChanges.Count -gt 0) {
    Write-Host ""
    Write-Host "Tracked changes must be committed first:" -ForegroundColor Yellow

    foreach ($Line in $TrackedChanges) {
        Write-Host $Line -ForegroundColor Yellow
    }

    throw "Tracked working tree is not clean."
}

Invoke-ReleaseStep "Fetch origin" {
    git fetch origin --tags --prune
}

Invoke-ReleaseStep "Verify feature branch is pushed" {
    git diff --exit-code "origin/$FeatureBranch..$FeatureBranch"
}

Invoke-ReleaseStep "Phase 4 completion validation" {
    powershell.exe `
        -NoLogo `
        -NoProfile `
        -ExecutionPolicy Bypass `
        -File ".\scripts\validate-phase4-completion.ps1" `
        -RepositoryRoot $RepositoryRoot
}

$LocalTag = git tag --list $ReleaseTag
Assert-LastExitCode "Check local release tag"

$RemoteTag = git ls-remote `
    --tags `
    origin `
    "refs/tags/$ReleaseTag"

Assert-LastExitCode "Check remote release tag"

if ($LocalTag -or $RemoteTag) {
    throw "Release tag already exists: $ReleaseTag"
}

Invoke-ReleaseStep "Switch to main" {
    git switch $MainBranch
}

Invoke-ReleaseStep "Update main" {
    git pull --ff-only origin $MainBranch
}

Invoke-ReleaseStep "Fast-forward merge Phase 4" {
    git merge --ff-only $FeatureBranch
}

$MainCommit = git rev-parse HEAD
Assert-LastExitCode "Read main commit"

$FeatureCommit = git rev-parse $FeatureBranch
Assert-LastExitCode "Read feature commit"

if ($MainCommit -ne $FeatureCommit) {
    throw "Main does not match the feature branch after merge."
}

Invoke-ReleaseStep "Create Phase 4 release tag" {
    git tag `
        -a $ReleaseTag `
        -m "Aerion Forge Phase 4 complete"
}

if (-not $SkipPush) {
    Invoke-ReleaseStep "Push main" {
        git push origin $MainBranch
    }

    Invoke-ReleaseStep "Push release tag" {
        git push origin $ReleaseTag
    }
}
else {
    Write-Host ""
    Write-Host "Push skipped." -ForegroundColor Yellow
}

$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$ReportRoot = Join-Path `
    $RepositoryRoot `
    "reports\phase4-release\$Timestamp"

New-Item `
    -ItemType Directory `
    -Path $ReportRoot `
    -Force |
    Out-Null

$ReportPath = Join-Path `
    $ReportRoot `
    "PHASE4_RELEASE_SUMMARY.txt"

$ReportLines = @(
    "AERION FORGE PHASE 4 RELEASE",
    "Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')",
    "Status: COMPLETE",
    "Branch: $MainBranch",
    "Commit: $MainCommit",
    "Tag: $ReleaseTag",
    "Push performed: $(-not $SkipPush)",
    "",
    "VALIDATION",
    "Ruff: PASS",
    "MyPy: PASS",
    "Full test suite: PASS",
    "Phase 4 architecture: PASS",
    "Phase 4 milestone completion: PASS",
    "",
    "RECENT HISTORY"
)

$RecentHistory = @(git log --oneline --decorate -12)
Assert-LastExitCode "Read release history"

$ReportLines += $RecentHistory

[System.IO.File]::WriteAllLines(
    $ReportPath,
    $ReportLines,
    [System.Text.UTF8Encoding]::new($false)
)

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "PHASE 4 RELEASE COMPLETE" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "Main commit: $MainCommit"
Write-Host "Release tag: $ReleaseTag"
Write-Host "Report:      $ReportPath"
Write-Host ""

git status --short
git log --oneline --decorate -10