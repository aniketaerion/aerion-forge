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
    .\tests\test_domain_intelligence_knowledge_loader_identifiers.py `
    .\tests\test_domain_intelligence_knowledge_loader_models.py `
    .\tests\test_domain_intelligence_knowledge_loader_policies.py `
    .\tests\test_domain_intelligence_knowledge_loader_discovery.py `
    .\tests\test_domain_intelligence_knowledge_loader_loader.py `
    .\tests\test_domain_intelligence_knowledge_loader_manifest.py `
    .\tests\test_domain_intelligence_knowledge_loader_registry.py `
    .\tests\test_domain_intelligence_knowledge_loader_resolver.py `
    .\tests\test_domain_intelligence_knowledge_loader_cache.py `
    .\tests\test_domain_intelligence_knowledge_loader_chunking.py `
    .\tests\test_domain_intelligence_knowledge_loader_compatibility.py `
    .\tests\test_domain_intelligence_knowledge_loader_validation.py `
    .\tests\test_domain_intelligence_knowledge_loader_versioning.py `
    .\tests\test_domain_intelligence_knowledge_loader_reporting.py `
    .\tests\test_domain_intelligence_knowledge_loader_service.py `
    .\tests\test_domain_intelligence_knowledge_loader_cli.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.7 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m4.7-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-CommandSuccess "M4.7 architecture validation"

Write-Host "M4.7 completion validation passed." -ForegroundColor Green