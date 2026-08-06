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
    -File ".\scripts\validate-m5.3-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot

if ($LASTEXITCODE -ne 0) {
    throw "M5.3 architecture validation failed."
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
    .\tests\test_autonomous_orchestration_identifiers.py `
    .\tests\test_autonomous_orchestration_states.py `
    .\tests\test_autonomous_orchestration_policies.py `
    .\tests\test_autonomous_orchestration_models.py `
    .\tests\test_autonomous_orchestration_transitions.py `
    .\tests\test_autonomous_orchestration_session_registry.py `
    .\tests\test_autonomous_orchestration_session_service.py `
    .\tests\test_autonomous_orchestration_resume.py `
    .\tests\test_autonomous_orchestration_plan_loader.py `
    .\tests\test_autonomous_orchestration_progress.py `
    .\tests\test_autonomous_orchestration_budget_monitor.py `
    .\tests\test_autonomous_orchestration_coordinator.py `
    .\tests\test_autonomous_orchestration_journal.py `
    .\tests\test_autonomous_orchestration_outcome_processor.py `
    .\tests\test_autonomous_orchestration_recovery.py `
    .\tests\test_autonomous_orchestration_iteration_service.py `
    .\tests\test_autonomous_orchestration_reporting.py `
    .\tests\test_autonomous_orchestration_cli.py `
    -p no:cacheprovider

if ($LASTEXITCODE -ne 0) {
    throw "M5.3 focused test suite failed."
}

python -m pytest -p no:cacheprovider
if ($LASTEXITCODE -ne 0) {
    throw "Full repository test suite failed."
}

Write-Host "M5.3 completion validation passed." -ForegroundColor Green