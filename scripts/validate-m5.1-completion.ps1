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
    -File ".\scripts\validate-m5.1-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot

if ($LASTEXITCODE -ne 0) {
    throw "M5.1 architecture validation failed."
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
    .\tests\test_autonomous_runtime_identifiers.py `
    .\tests\test_autonomous_runtime_states.py `
    .\tests\test_autonomous_runtime_models.py `
    .\tests\test_autonomous_runtime_policies.py `
    .\tests\test_autonomous_runtime_transitions.py `
    .\tests\test_autonomous_runtime_invariants.py `
    .\tests\test_autonomous_runtime_lifecycle.py `
    .\tests\test_autonomous_runtime_service.py `
    .\tests\test_autonomous_runtime_authority.py `
    .\tests\test_autonomous_runtime_approvals.py `
    .\tests\test_autonomous_runtime_risk.py `
    .\tests\test_autonomous_runtime_permission.py `
    .\tests\test_autonomous_runtime_checkpoints.py `
    .\tests\test_autonomous_runtime_recovery_engine.py `
    .\tests\test_autonomous_runtime_events.py `
    .\tests\test_autonomous_runtime_recovery_service.py `
    .\tests\test_autonomous_runtime_reporting.py `
    .\tests\test_autonomous_runtime_cli.py `
    -p no:cacheprovider

if ($LASTEXITCODE -ne 0) {
    throw "M5.1 focused test suite failed."
}

python -m pytest -p no:cacheprovider
if ($LASTEXITCODE -ne 0) {
    throw "Full test suite failed."
}

Write-Host "M5.1 completion validation passed." -ForegroundColor Green