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
    .\tests\test_domain_intelligence_embedded_identifiers.py `
    .\tests\test_domain_intelligence_embedded_models.py `
    .\tests\test_domain_intelligence_embedded_policies.py `
    .\tests\test_domain_intelligence_embedded_px4.py `
    .\tests\test_domain_intelligence_embedded_ardupilot.py `
    .\tests\test_domain_intelligence_embedded_ros2.py `
    .\tests\test_domain_intelligence_embedded_stm32.py `
    .\tests\test_domain_intelligence_embedded_build_systems.py `
    .\tests\test_domain_intelligence_embedded_registry.py `
    .\tests\test_domain_intelligence_embedded_interfaces.py `
    .\tests\test_domain_intelligence_embedded_messages.py `
    .\tests\test_domain_intelligence_embedded_safety.py `
    .\tests\test_domain_intelligence_embedded_reporting.py `
    .\tests\test_domain_intelligence_embedded_service.py `
    .\tests\test_domain_intelligence_embedded_cli.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.6 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m4.6-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-CommandSuccess "M4.6 architecture validation"

Write-Host "M4.6 completion validation passed." -ForegroundColor Green