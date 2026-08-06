[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

function Assert-CommandSuccess {
    param([Parameter(Mandatory)][string]$Name)

    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_domain_intelligence_phase_validation_identifiers.py `
    .\tests\test_domain_intelligence_phase_validation_models.py `
    .\tests\test_domain_intelligence_phase_validation_policies.py `
    .\tests\test_domain_intelligence_phase_validation_architecture.py `
    .\tests\test_domain_intelligence_phase_validation_acceptance.py `
    .\tests\test_domain_intelligence_phase_validation_registry.py `
    .\tests\test_domain_intelligence_phase_validation_service.py `
    .\tests\test_domain_intelligence_phase_validation_coverage.py `
    .\tests\test_domain_intelligence_phase_validation_compatibility.py `
    .\tests\test_domain_intelligence_phase_validation_release.py `
    .\tests\test_domain_intelligence_phase_validation_reporting.py `
    .\tests\test_domain_intelligence_phase_validation_cli.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.8 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m4.8-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-CommandSuccess "M4.8 architecture validation"

Write-Host "M4.8 completion validation passed." -ForegroundColor Green