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
    .\tests\test_domain_intelligence_business_domain_identifiers.py `
    .\tests\test_domain_intelligence_business_domain_models.py `
    .\tests\test_domain_intelligence_business_domain_policies.py `
    .\tests\test_domain_intelligence_business_domain_entities.py `
    .\tests\test_domain_intelligence_business_domain_erp.py `
    .\tests\test_domain_intelligence_business_domain_crm.py `
    .\tests\test_domain_intelligence_business_domain_manifest.py `
    .\tests\test_domain_intelligence_business_domain_registry.py `
    .\tests\test_domain_intelligence_business_domain_ontology.py `
    .\tests\test_domain_intelligence_business_domain_workflows.py `
    .\tests\test_domain_intelligence_business_domain_rules.py `
    .\tests\test_domain_intelligence_business_domain_plugin.py `
    .\tests\test_domain_intelligence_business_domain_reporting.py `
    .\tests\test_domain_intelligence_business_domain_service.py `
    .\tests\test_domain_intelligence_business_domain_cli.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.5 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m4.5-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-CommandSuccess "M4.5 architecture validation"

Write-Host "M4.5 completion validation passed." -ForegroundColor Green