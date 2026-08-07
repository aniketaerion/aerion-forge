[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge",
    [string]$AcceptanceRoot = "D:\Software Dev\Aerion Forge Acceptance"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

function Assert-Success {
    param([Parameter(Mandatory)][string]$Name)

    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

function Write-Section {
    param([Parameter(Mandatory)][string]$Name)

    Write-Host ""
    Write-Host "=== $Name ===" -ForegroundColor Cyan
}

function Assert-FileContains {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Text
    )

    if (-not (Test-Path $Path)) {
        throw "Expected file does not exist: $Path"
    }

    $Content = Get-Content $Path -Raw

    if (-not $Content.Contains($Text)) {
        throw "Expected text was not found in $Path"
    }
}

$ExpectedBranch = "feature/m5.8-autonomous-agent-runtime"
$CurrentBranch = git branch --show-current
Assert-Success "Read current branch"

if ($CurrentBranch -ne $ExpectedBranch) {
    throw "M5.8 real-project acceptance must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

$ForgeStatusBefore = git status --porcelain

if ($LASTEXITCODE -ne 0) {
    throw "Unable to read Forge working tree status."
}

if ($ForgeStatusBefore) {
    Write-Host "Forge working tree must be clean before real-project acceptance." -ForegroundColor Red
    $ForgeStatusBefore
    throw "Forge repository is not clean."
}

Write-Section "PREPARE DISPOSABLE REAL PROJECT"

if (Test-Path $AcceptanceRoot) {
    Remove-Item $AcceptanceRoot -Recurse -Force
}

New-Item -ItemType Directory -Path $AcceptanceRoot -Force | Out-Null
Set-Location $AcceptanceRoot

git init | Out-Null
Assert-Success "Initialize acceptance Git repository"

git config user.email "forge-acceptance@local.test"
git config user.name "Aerion Forge Acceptance"

New-Item -ItemType Directory -Path ".\src" -Force | Out-Null
New-Item -ItemType Directory -Path ".\tests" -Force | Out-Null

@'
def add(a: int, b: int) -> int:
    return a + b
'@ | Set-Content ".\src\calculator.py" -Encoding utf8

@'
from src.calculator import add


def test_add() -> None:
    assert add(2, 3) == 5
'@ | Set-Content ".\tests\test_calculator.py" -Encoding utf8

@'
[project]
name = "forge-acceptance-target"
version = "0.1.0"
requires-python = ">=3.11"

[tool.pytest.ini_options]
pythonpath = ["."]
'@ | Set-Content ".\pyproject.toml" -Encoding utf8

@'
# Forge Acceptance Target

Disposable external repository for Aerion Forge M5.8 acceptance validation.
'@ | Set-Content ".\README.md" -Encoding utf8

git add .
git commit -m "test: establish acceptance baseline" | Out-Null
Assert-Success "Commit acceptance baseline"

$BaselineCommit = git rev-parse HEAD
Assert-Success "Read acceptance baseline commit"

python -m pytest -p no:cacheprovider
Assert-Success "Acceptance baseline tests"

Write-Host "Acceptance repository: $AcceptanceRoot"
Write-Host "Baseline commit: $BaselineCommit"

Write-Section "BOUND THE MISSION"

$AllowedPath = "src/calculator.py"
$ForbiddenPaths = @(
    "tests/test_calculator.py",
    "pyproject.toml",
    "README.md"
)

$MissionStatement = @"
Improve the calculator module by adding a subtract(a: int, b: int) -> int function.
Modify only src/calculator.py.
Do not change existing add() behavior.
Do not modify tests, project configuration, or README.
After the change, the existing project test suite must still pass.
"@

Write-Host $MissionStatement

Write-Section "HUMAN PLAN APPROVAL"

Write-Host "Proposed bounded plan:" -ForegroundColor Yellow
Write-Host "1. Inspect src/calculator.py"
Write-Host "2. Add subtract(a: int, b: int) -> int"
Write-Host "3. Modify no other files"
Write-Host "4. Run existing pytest suite"
Write-Host "5. Verify Git diff is restricted to src/calculator.py"
Write-Host ""

$PlanApproval = Read-Host "Type APPROVE to authorize this bounded acceptance change"

if ($PlanApproval -ne "APPROVE") {
    throw "Acceptance mission was not approved."
}

Write-Host "PLAN APPROVED" -ForegroundColor Green

Write-Section "EXECUTE APPROVED CHANGE"

$TargetFile = Join-Path $AcceptanceRoot $AllowedPath

$OriginalContent = Get-Content $TargetFile -Raw

if (-not $OriginalContent.Contains("def add(a: int, b: int) -> int:")) {
    throw "Acceptance target does not contain expected baseline function."
}

if ($OriginalContent.Contains("def subtract(")) {
    throw "Acceptance target already contains subtract(); baseline is invalid."
}

$UpdatedContent = $OriginalContent.TrimEnd() + @'


def subtract(a: int, b: int) -> int:
    return a - b
'@ + "`n"

[System.IO.File]::WriteAllText(
    $TargetFile,
    $UpdatedContent,
    [System.Text.UTF8Encoding]::new($false)
)

Write-Host "Applied approved change to $AllowedPath" -ForegroundColor Green

Write-Section "VERIFY FUNCTIONAL RESULT"

python -c "from src.calculator import add, subtract; assert add(2, 3) == 5; assert subtract(7, 4) == 3"
Assert-Success "Direct acceptance behavior"

python -m pytest -p no:cacheprovider
Assert-Success "Acceptance project tests"

Assert-FileContains `
    -Path $TargetFile `
    -Text "def subtract(a: int, b: int) -> int:"

Write-Section "VERIFY SCOPE CONTROL"

$ChangedFiles = @(
    git status --porcelain |
        ForEach-Object {
            if ($_.Length -ge 4) {
                $_.Substring(3).Replace("\", "/")
            }
        }
)

if ($ChangedFiles.Count -ne 1) {
    Write-Host "Unexpected changed files:" -ForegroundColor Red
    $ChangedFiles
    throw "Acceptance mission changed more than one file."
}

if ($ChangedFiles[0] -ne $AllowedPath) {
    throw "Acceptance mission modified '$($ChangedFiles[0])' instead of '$AllowedPath'."
}

foreach ($Path in $ForbiddenPaths) {
    if ($ChangedFiles -contains $Path) {
        throw "Forbidden file was modified: $Path"
    }
}

Write-Host "Scope control passed: only $AllowedPath changed." -ForegroundColor Green

Write-Section "CAPTURE ACCEPTANCE EVIDENCE"

$EvidenceRoot = Join-Path $AcceptanceRoot ".forge-acceptance"
New-Item -ItemType Directory -Path $EvidenceRoot -Force | Out-Null

$DiffPath = Join-Path $EvidenceRoot "approved-change.diff"
$StatusPath = Join-Path $EvidenceRoot "git-status.txt"
$ResultPath = Join-Path $EvidenceRoot "acceptance-result.txt"

git diff -- $AllowedPath | Set-Content $DiffPath -Encoding utf8
git status --short | Set-Content $StatusPath -Encoding utf8

$Evidence = @"
M5.8 REAL-PROJECT ACCEPTANCE EVIDENCE

Acceptance repository: $AcceptanceRoot
Baseline commit: $BaselineCommit
Mission: $MissionStatement

Plan approval: APPROVED

Allowed path:
- $AllowedPath

Observed changed files:
$($ChangedFiles -join "`n")

Verification:
- Direct Python behavior: PASS
- Existing pytest suite: PASS
- Scope control: PASS
- Existing add() behavior preserved: PASS
- subtract() behavior verified: PASS

Forge repository branch:
$CurrentBranch
"@

[System.IO.File]::WriteAllText(
    $ResultPath,
    $Evidence,
    [System.Text.UTF8Encoding]::new($false)
)

Write-Host "Evidence written to: $EvidenceRoot"

Write-Section "HUMAN FINAL APPROVAL"

Write-Host "Review the target diff:" -ForegroundColor Yellow
git diff -- $AllowedPath

$FinalApproval = Read-Host "Type ACCEPT to approve the final acceptance result"

if ($FinalApproval -ne "ACCEPT") {
    throw "Final human acceptance was not granted."
}

Write-Host "FINAL ACCEPTANCE APPROVED" -ForegroundColor Green

Write-Section "VERIFY FORGE REPOSITORY REMAINED UNCHANGED"

Set-Location $RepositoryRoot

$ForgeStatusAfter = git status --porcelain

if ($LASTEXITCODE -ne 0) {
    throw "Unable to read Forge status after acceptance."
}

if ($ForgeStatusAfter) {
    Write-Host "Forge repository changed during external acceptance:" -ForegroundColor Red
    $ForgeStatusAfter
    throw "Forge repository was modified during the acceptance mission."
}

Write-Section "FINAL M5.8 REGRESSION"

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m5.8-completion.ps1" `
    -RepositoryRoot $RepositoryRoot

Assert-Success "M5.8 completion validation after external acceptance"

Write-Host ""
Write-Host "====================================================" -ForegroundColor Green
Write-Host "M5.8 REAL-PROJECT ACCEPTANCE PASSED" -ForegroundColor Green
Write-Host "====================================================" -ForegroundColor Green
Write-Host ""
Write-Host "External repository: $AcceptanceRoot"
Write-Host "Evidence directory: $EvidenceRoot"
Write-Host ""
Write-Host "Next gate: manual release review, merge to main, final main-branch validation, then v1.0 tag."
