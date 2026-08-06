[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

function Assert-Success {
    param([string]$Name)

    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m5.5-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-Success "M5.5 architecture validation"

python -m ruff check .
Assert-Success "Ruff"

python -m mypy .
Assert-Success "MyPy"

python -m pytest `
    .\tests\test_autonomous_memory_identifiers.py `
    .\tests\test_autonomous_memory_states.py `
    .\tests\test_autonomous_memory_policies.py `
    .\tests\test_autonomous_memory_models.py `
    .\tests\test_autonomous_memory_normalization.py `
    .\tests\test_autonomous_memory_redaction.py `
    .\tests\test_autonomous_memory_provenance.py `
    .\tests\test_autonomous_memory_classification.py `
    .\tests\test_autonomous_memory_deduplication.py `
    .\tests\test_autonomous_memory_ingestion.py `
    .\tests\test_autonomous_memory_storage.py `
    .\tests\test_autonomous_memory_repository.py `
    .\tests\test_autonomous_memory_indexing.py `
    .\tests\test_autonomous_memory_search.py `
    .\tests\test_autonomous_memory_retrieval.py `
    .\tests\test_autonomous_memory_retention.py `
    .\tests\test_autonomous_memory_service.py `
    .\tests\test_autonomous_memory_supersession.py `
    .\tests\test_autonomous_memory_feedback.py `
    .\tests\test_autonomous_memory_learning.py `
    .\tests\test_autonomous_memory_consolidation.py `
    .\tests\test_autonomous_memory_learning_service.py `
    .\tests\test_autonomous_memory_reporting.py `
    .\tests\test_autonomous_memory_cli.py `
    -p no:cacheprovider
Assert-Success "M5.5 focused tests"

python -m pytest -p no:cacheprovider
Assert-Success "Full repository tests"

Write-Host "M5.5 completion validation passed." `
    -ForegroundColor Green