[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$RequiredProductionFiles = @(
    ".\forge\domain_intelligence\backend\__init__.py",
    ".\forge\domain_intelligence\backend\errors.py",
    ".\forge\domain_intelligence\backend\identifiers.py",
    ".\forge\domain_intelligence\backend\models.py",
    ".\forge\domain_intelligence\backend\policies.py",
    ".\forge\domain_intelligence\backend\node.py",
    ".\forge\domain_intelligence\backend\fastapi.py",
    ".\forge\domain_intelligence\backend\django.py",
    ".\forge\domain_intelligence\backend\registry.py",
    ".\forge\domain_intelligence\backend\dependencies.py",
    ".\forge\domain_intelligence\backend\configuration.py",
    ".\forge\domain_intelligence\backend\services.py",
    ".\forge\domain_intelligence\backend\workers.py",
    ".\forge\domain_intelligence\backend\architecture.py",
    ".\forge\domain_intelligence\backend\reporting.py",
    ".\forge\domain_intelligence\backend\service.py",
    ".\forge\domain_intelligence\backend\cli.py"
)

$RequiredTests = @(
    ".\tests\test_domain_intelligence_backend_identifiers.py",
    ".\tests\test_domain_intelligence_backend_models.py",
    ".\tests\test_domain_intelligence_backend_policies.py",
    ".\tests\test_domain_intelligence_backend_node.py",
    ".\tests\test_domain_intelligence_backend_fastapi.py",
    ".\tests\test_domain_intelligence_backend_django.py",
    ".\tests\test_domain_intelligence_backend_registry.py",
    ".\tests\test_domain_intelligence_backend_dependencies.py",
    ".\tests\test_domain_intelligence_backend_configuration.py",
    ".\tests\test_domain_intelligence_backend_services.py",
    ".\tests\test_domain_intelligence_backend_workers.py",
    ".\tests\test_domain_intelligence_backend_architecture.py",
    ".\tests\test_domain_intelligence_backend_reporting.py",
    ".\tests\test_domain_intelligence_backend_service.py",
    ".\tests\test_domain_intelligence_backend_cli.py"
)

$RequiredDocumentation = @(
    ".\docs\domain_intelligence\backend\ARCHITECTURE.md",
    ".\docs\domain_intelligence\backend\SPECIFICATION.md",
    ".\docs\domain_intelligence\backend\DATA_MODEL.md",
    ".\docs\domain_intelligence\backend\SECURITY_MODEL.md",
    ".\docs\domain_intelligence\backend\ACCEPTANCE_CRITERIA.md"
)

foreach (
    $Path in
    $RequiredProductionFiles +
    $RequiredTests +
    $RequiredDocumentation
) {
    if (-not (Test-Path $Path -PathType Leaf)) {
        throw "Missing M4.2 architecture file: $Path"
    }

    if ((Get-Item $Path).Length -le 0) {
        throw "Empty M4.2 architecture file: $Path"
    }
}

$BackendCli = Get-Content `
    ".\forge\domain_intelligence\backend\cli.py" `
    -Raw

if ($BackendCli -notmatch 'backend_app\s*=\s*typer\.Typer') {
    throw "Backend Typer application is missing."
}

$ForgeCli = Get-Content ".\forge\cli.py" -Raw

if (
    $ForgeCli -notmatch
    'from forge\.domain_intelligence\.backend\.cli import backend_app'
) {
    throw "Backend CLI import is missing from forge\cli.py"
}

if (
    $ForgeCli -notmatch
    'add_typer\(backend_app,\s*name="backend"\)'
) {
    throw "Backend CLI registration is missing from forge\cli.py"
}

Write-Host "M4.2 architecture validation passed." -ForegroundColor Green