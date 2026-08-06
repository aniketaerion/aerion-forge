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
    -File ".\scripts\validate-m5.2-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot

if ($LASTEXITCODE -ne 0) {
    throw "M5.2 architecture validation failed."
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
    .\tests\test_autonomous_execution_identifiers.py `
    .\tests\test_autonomous_execution_models.py `
    .\tests\test_autonomous_execution_policies.py `
    .\tests\test_autonomous_execution_tool_contracts.py `
    .\tests\test_autonomous_execution_dependency_graph.py `
    .\tests\test_autonomous_execution_eligibility.py `
    .\tests\test_autonomous_execution_scheduler.py `
    .\tests\test_autonomous_execution_planner.py `
    .\tests\test_autonomous_execution_tool_registry.py `
    .\tests\test_autonomous_execution_argument_validation.py `
    .\tests\test_autonomous_execution_effect_verification.py `
    .\tests\test_autonomous_execution_tool_gateway.py `
    .\tests\test_autonomous_execution_transitions.py `
    .\tests\test_autonomous_execution_lease_manager.py `
    .\tests\test_autonomous_execution_evidence.py `
    .\tests\test_autonomous_execution_runtime.py `
    .\tests\test_autonomous_execution_reporting.py `
    .\tests\test_autonomous_execution_cli.py `
    -p no:cacheprovider

if ($LASTEXITCODE -ne 0) {
    throw "M5.2 focused test suite failed."
}

python -m pytest -p no:cacheprovider
if ($LASTEXITCODE -ne 0) {
    throw "Full test suite failed."
}

Write-Host "M5.2 completion validation passed." -ForegroundColor Green