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

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m5.7-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-Success "M5.7 architecture validation"

python -m ruff check forge tests
Assert-Success "Ruff"

python -m mypy .
Assert-Success "MyPy"

python -m pytest `
    .\tests\test_autonomous_execution_v2_identifiers.py `
    .\tests\test_autonomous_execution_v2_states.py `
    .\tests\test_autonomous_execution_v2_policies.py `
    .\tests\test_autonomous_execution_v2_models.py `
    .\tests\test_autonomous_execution_v2_graph.py `
    .\tests\test_autonomous_execution_v2_cycle_detection.py `
    .\tests\test_autonomous_execution_v2_ordering.py `
    .\tests\test_autonomous_execution_v2_eligibility.py `
    .\tests\test_autonomous_execution_v2_scheduler.py `
    .\tests\test_autonomous_execution_v2_graph_builder.py `
    .\tests\test_autonomous_execution_v2_authority.py `
    .\tests\test_autonomous_execution_v2_attempts.py `
    .\tests\test_autonomous_execution_v2_evidence.py `
    .\tests\test_autonomous_execution_v2_step_execution.py `
    .\tests\test_autonomous_execution_v2_coordinator.py `
    .\tests\test_autonomous_execution_v2_repository.py `
    .\tests\test_autonomous_execution_v2_retry.py `
    .\tests\test_autonomous_execution_v2_recovery.py `
    .\tests\test_autonomous_execution_v2_resume.py `
    .\tests\test_autonomous_execution_v2_history.py `
    .\tests\test_autonomous_execution_v2_reporting.py `
    .\tests\test_autonomous_execution_v2_cli.py `
    -p no:cacheprovider
Assert-Success "M5.7 focused tests"

python -m pytest -p no:cacheprovider
Assert-Success "Full repository tests"

Write-Host "M5.7 completion validation passed." `
    -ForegroundColor Green