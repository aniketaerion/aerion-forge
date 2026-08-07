[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

function Assert-Success {
    param([Parameter(Mandatory)][string]$Name)

    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

$ExpectedBranch = "feature/m5.8-autonomous-agent-runtime"
$CurrentBranch = git branch --show-current
Assert-Success "Read current branch"

if ($CurrentBranch -ne $ExpectedBranch) {
    throw "M5.8 completion validation must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

Write-Host ""
Write-Host "=== M5.8 ARCHITECTURE GATE ===" -ForegroundColor Cyan

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m5.8-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot

Assert-Success "M5.8 architecture validation"

Write-Host ""
Write-Host "=== RUFF ===" -ForegroundColor Cyan

python -m ruff check forge tests
Assert-Success "Ruff"

Write-Host ""
Write-Host "=== MYPY ===" -ForegroundColor Cyan

python -m mypy .
Assert-Success "MyPy"

$FocusedTests = @(
    ".\tests\test_mission_runtime_identifiers.py",
    ".\tests\test_mission_runtime_states.py",
    ".\tests\test_mission_runtime_policies.py",
    ".\tests\test_mission_runtime_models.py",
    ".\tests\test_mission_runtime_technology_detection.py",
    ".\tests\test_mission_runtime_capability_resolution.py",
    ".\tests\test_mission_runtime_workspace_context.py",
    ".\tests\test_mission_runtime_context_builder.py",
    ".\tests\test_mission_runtime_approval.py",
    ".\tests\test_mission_runtime_execution_conversion.py",
    ".\tests\test_mission_runtime_execution_authority.py",
    ".\tests\test_mission_runtime_verification.py",
    ".\tests\test_mission_runtime_state_machine.py",
    ".\tests\test_mission_runtime_repository.py",
    ".\tests\test_mission_runtime_service.py",
    ".\tests\test_mission_runtime_reporting.py",
    ".\tests\test_mission_runtime_cli.py"
)

foreach ($Test in $FocusedTests) {
    if (-not (Test-Path $Test)) {
        throw "Missing M5.8 focused test: $Test"
    }
}

Write-Host ""
Write-Host "=== M5.8 FOCUSED TESTS ===" -ForegroundColor Cyan

python -m pytest $FocusedTests -p no:cacheprovider
Assert-Success "M5.8 focused tests"

Write-Host ""
Write-Host "=== FULL REPOSITORY REGRESSION ===" -ForegroundColor Cyan

python -m pytest -p no:cacheprovider
Assert-Success "Full repository test suite"

Write-Host ""
Write-Host "=== ROOT CLI ===" -ForegroundColor Cyan

forge mission-runtime about
Assert-Success "Mission Runtime CLI"

Write-Host ""
Write-Host "=== GIT WORKTREE REVIEW ===" -ForegroundColor Cyan

$Status = git status --short

if ($LASTEXITCODE -ne 0) {
    throw "Unable to read Git status."
}

if ($Status) {
    Write-Host "Working tree contains uncommitted/untracked files:" -ForegroundColor Yellow
    $Status
    Write-Host ""
    Write-Host "This does not automatically fail code validation, but the M5.8 stage gate is NOT release-ready until intended M5.8 validator changes are committed and unrelated files are excluded or cleaned." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "==================================================" -ForegroundColor Green
Write-Host "M5.8 COMPLETION VALIDATION PASSED" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green
Write-Host ""
Write-Host "NOTE: Forge v1.0 is not released by this validator alone."
Write-Host "A bounded real-project acceptance mission and manual approval are still required."
