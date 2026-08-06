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
    -File ".\scripts\validate-m5.6-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-Success "M5.6 architecture validation"

python -m ruff check .
Assert-Success "Ruff"

python -m mypy .
Assert-Success "MyPy"

python -m pytest `
    .\tests\test_autonomous_planning_identifiers.py `
    .\tests\test_autonomous_planning_states.py `
    .\tests\test_autonomous_planning_policies.py `
    .\tests\test_autonomous_planning_models.py `
    .\tests\test_autonomous_planning_graph.py `
    .\tests\test_autonomous_planning_cycle_detection.py `
    .\tests\test_autonomous_planning_ordering.py `
    .\tests\test_autonomous_planning_eligibility.py `
    .\tests\test_autonomous_planning_graph_builder.py `
    .\tests\test_autonomous_planning_analysis.py `
    .\tests\test_autonomous_planning_step_synthesis.py `
    .\tests\test_autonomous_planning_dependency_synthesis.py `
    .\tests\test_autonomous_planning_plan_generation.py `
    .\tests\test_autonomous_planning_validation.py `
    .\tests\test_autonomous_planning_approval.py `
    .\tests\test_autonomous_planning_revision.py `
    .\tests\test_autonomous_planning_repository.py `
    .\tests\test_autonomous_planning_service.py `
    .\tests\test_autonomous_planning_reporting.py `
    .\tests\test_autonomous_planning_cli.py `
    -p no:cacheprovider
Assert-Success "M5.6 focused tests"

python -m pytest -p no:cacheprovider
Assert-Success "Full repository tests"

Write-Host "M5.6 completion validation passed." `
    -ForegroundColor Green