[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$RequiredProductionFiles = @(
    ".\forge\domain_intelligence\api\__init__.py",
    ".\forge\domain_intelligence\api\errors.py",
    ".\forge\domain_intelligence\api\identifiers.py",
    ".\forge\domain_intelligence\api\models.py",
    ".\forge\domain_intelligence\api\policies.py",
    ".\forge\domain_intelligence\api\rest.py",
    ".\forge\domain_intelligence\api\openapi.py",
    ".\forge\domain_intelligence\api\discovery.py",
    ".\forge\domain_intelligence\api\registry.py",
    ".\forge\domain_intelligence\api\graphql.py",
    ".\forge\domain_intelligence\api\dependencies.py",
    ".\forge\domain_intelligence\api\versioning.py",
    ".\forge\domain_intelligence\api\compatibility.py",
    ".\forge\domain_intelligence\api\security.py",
    ".\forge\domain_intelligence\api\contracts.py",
    ".\forge\domain_intelligence\api\reporting.py",
    ".\forge\domain_intelligence\api\service.py",
    ".\forge\domain_intelligence\api\cli.py"
)

$RequiredTests = @(
    ".\tests\test_domain_intelligence_api_identifiers.py",
    ".\tests\test_domain_intelligence_api_models.py",
    ".\tests\test_domain_intelligence_api_policies.py",
    ".\tests\test_domain_intelligence_api_rest.py",
    ".\tests\test_domain_intelligence_api_openapi.py",
    ".\tests\test_domain_intelligence_api_discovery.py",
    ".\tests\test_domain_intelligence_api_registry.py",
    ".\tests\test_domain_intelligence_api_graphql.py",
    ".\tests\test_domain_intelligence_api_dependencies.py",
    ".\tests\test_domain_intelligence_api_versioning.py",
    ".\tests\test_domain_intelligence_api_compatibility.py",
    ".\tests\test_domain_intelligence_api_security.py",
    ".\tests\test_domain_intelligence_api_contracts.py",
    ".\tests\test_domain_intelligence_api_reporting.py",
    ".\tests\test_domain_intelligence_api_service.py",
    ".\tests\test_domain_intelligence_api_cli.py"
)

$RequiredDocumentation = @(
    ".\docs\domain_intelligence\api\ARCHITECTURE.md",
    ".\docs\domain_intelligence\api\SPECIFICATION.md",
    ".\docs\domain_intelligence\api\DATA_MODEL.md",
    ".\docs\domain_intelligence\api\SECURITY_MODEL.md",
    ".\docs\domain_intelligence\api\ACCEPTANCE_CRITERIA.md"
)

foreach (
    $Path in
    $RequiredProductionFiles +
    $RequiredTests +
    $RequiredDocumentation
) {
    if (-not (Test-Path $Path -PathType Leaf)) {
        throw "Missing M4.4 architecture file: $Path"
    }

    if ((Get-Item $Path).Length -le 0) {
        throw "Empty M4.4 architecture file: $Path"
    }
}

$ApiCli = Get-Content `
    ".\forge\domain_intelligence\api\cli.py" `
    -Raw

if ($ApiCli -notmatch 'api_app\s*=\s*typer\.Typer') {
    throw "API Typer application is missing."
}

$ForgeCli = Get-Content ".\forge\cli.py" -Raw

if (
    $ForgeCli -notmatch
    'from forge\.domain_intelligence\.api\.cli import api_app'
) {
    throw "API CLI import is missing from forge\cli.py"
}

if (
    $ForgeCli -notmatch
    'add_typer\(api_app,\s*name="api"\)'
) {
    throw "API CLI registration is missing from forge\cli.py"
}

Write-Host "M4.4 architecture validation passed." -ForegroundColor Green