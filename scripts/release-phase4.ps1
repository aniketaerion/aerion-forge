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

function Assert-CommandSuccess {
    param([Parameter(Mandatory)][string]$Name)

    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

function Invoke-Step {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][scriptblock]$Command
    )

    Write-Host ""
    Write-Host "RUNNING: $Name" -ForegroundColor Cyan

    & $Command
    Assert-CommandSuccess $Name

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
Assert-CommandSuccess "Read current branch"

if ($CurrentBranch -ne $FeatureBranch) {
    throw "Release must start from '$FeatureBranch'. Current branch: '$CurrentBranch'."
}

$TrackedChanges = @(git status --short --untracked-files=no)
Assert-CommandSuccess "Read tracked working-tree status"

if ($TrackedChanges.Count -gt 0) {
    $TrackedChanges | ForEach-Object { Write-Host $_ -ForegroundColor Yellow }
    throw "Commit or restore tracked changes before releasing Phase 4."
}

Invoke-Step "Fetch origin" {
    git fetch origin --tags --prune
}

Invoke-Step "Verify feature branch is pushed" {
    git diff --exit-code "origin/$FeatureBranch..$FeatureBranch"
}

Invoke-Step "Phase 4 completion validation" {
    powershell.exe `
        -NoLogo `
        -NoProfile `
        -ExecutionPolicy Bypass `
        -File ".\scripts\validate-phase4-completion.ps1" `
        -RepositoryRoot $RepositoryRoot
}

$ExistingLocalTag = git tag --list $ReleaseTag
Assert-CommandSuccess "Check local release tag"

$ExistingRemoteTag = git ls-remote --tags origin "refs/tags/$ReleaseTag"
Assert-CommandSuccess "Check remote release tag"

if ($ExistingLocalTag -or $ExistingRemoteTag) {
    throw "Release tag already exists: $ReleaseTag"
}

Invoke-Step "Switch to main" {
    git switch $MainBranch
}

Invoke-Step "Update main" {
    git pull --ff-only origin $MainBranch
}

Invoke-Step "Fast-forward merge Phase 4" {
    git merge --ff-only $FeatureBranch
}

$MainCommit = git rev-parse HEAD
Assert-CommandSuccess "Read merged commit"

$FeatureCommit = git rev-parse $FeatureBranch
Assert-CommandSuccess "Read feature commit"

if ($MainCommit -ne $FeatureCommit) {
    throw "Main does not exactly match the feature branch after merge."
}

Invoke-Step "Create annotated Phase 4 tag" {
    git tag -a $ReleaseTag -m "Aerion Forge Phase 4 complete"
}

if (-not $SkipPush) {
    Invoke-Step "Push main" {
        git push origin $MainBranch
    }

    Invoke-Step "Push release tag" {
        git push origin $ReleaseTag
    }
}

$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$ReportRoot = Join-Path $RepositoryRoot "reports\phase4-release\$Timestamp"
New-Item -ItemType Directory -Path $ReportRoot -Force | Out-Null

$ReleaseReportPath = Join-Path $ReportRoot "PHASE4_RELEASE_SUMMARY.md"
$StatusLines = @(git status --short)
$HistoryLines = @(git log --oneline --decorate -12)

$Summary = @(
    "# Aerion Forge Phase 4 Release",
    "",
    "Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')",
    "",
    "## Release",
    "",
    "| Field | Value |",
    "|---|---|",
    "| Status | **COMPLETE** |",
    "| Branch | ``$MainBranch`` |",
    "| Commit | ``$MainCommit`` |",
    "| Tag | ``$ReleaseTag`` |",
    "| Push performed | ``$(-not $SkipPush)`` |",
    "",
    "## Validation",
    "",
    "- Ruff passed",
    "- MyPy passed",
    "- Full test suite passed",
    "- Phase 4 architecture validation passed",
    "- Phase 4 milestone completion validations passed",
    "",
    "## Working Tree",
    "",
    "```text"
)

if ($StatusLines.Count -eq 0) {
    $Summary += "Clean"
}
else {
    $Summary += $StatusLines
}

$Summary += @(
    "```",
    "",
    "## Recent History",
    "",
    "```text"
)

$Summary += $HistoryLines
$Summary += "```"

$Summary | Out-File -FilePath $ReleaseReportPath -Encoding utf8

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "PHASE 4 RELEASE COMPLETE" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "Main commit: $MainCommit"
Write-Host "Release tag: $ReleaseTag"
Write-Host "Report:      $ReleaseReportPath"

git status --short
git log --oneline --decorate -10
