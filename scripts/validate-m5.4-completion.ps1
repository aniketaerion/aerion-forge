[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m5.4-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot

if ($LASTEXITCODE -ne 0) {
    throw "M5.4 architecture validation failed."
}

python -m ruff check .
if ($LASTEXITCODE -ne 0) {
    throw "Ruff failed."
}

python -m mypy .
if ($LASTEXITCODE -ne 0) {
    throw "MyPy failed."
}

python -m pytest `
    .\tests\test_autonomous_decision_identifiers.py `
    .\tests\test_autonomous_decision_states.py `
    .\tests\test_autonomous_decision_policies.py `
    .\tests\test_autonomous_decision_models.py `
    .\tests\test_autonomous_decision_candidate_generator.py `
    .\tests\test_autonomous_decision_deduplication.py `
    .\tests\test_autonomous_decision_feasibility.py `
    .\tests\test_autonomous_decision_policy_filter.py `
    .\tests\test_autonomous_decision_candidate_service.py `
    .\tests\test_autonomous_decision_risk_assessor.py `
    .\tests\test_autonomous_decision_confidence_assessor.py `
    .\tests\test_autonomous_decision_evidence_assessor.py `
    .\tests\test_autonomous_decision_scoring.py `
    .\tests\test_autonomous_decision_assessment_service.py `
    .\tests\test_autonomous_decision_ranking.py `
    .\tests\test_autonomous_decision_selector.py `
    .\tests\test_autonomous_decision_rationale.py `
    .\tests\test_autonomous_decision_replay_guard.py `
    .\tests\test_autonomous_decision_decision_journal.py `
    .\tests\test_autonomous_decision_decision_service.py `
    .\tests\test_autonomous_decision_reporting.py `
    .\tests\test_autonomous_decision_cli.py `
    -p no:cacheprovider

if ($LASTEXITCODE -ne 0) {
    throw "M5.4 focused test suite failed."
}

python -m pytest -p no:cacheprovider
if ($LASTEXITCODE -ne 0) {
    throw "Full repository test suite failed."
}

Write-Host "M5.4 completion validation passed." `
    -ForegroundColor Green