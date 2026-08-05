[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$RequiredProductionFiles = @(
    ".\forge\domain_intelligence\database\__init__.py",
    ".\forge\domain_intelligence\database\errors.py",
    ".\forge\domain_intelligence\database\identifiers.py",
    ".\forge\domain_intelligence\database\models.py",
    ".\forge\domain_intelligence\database\policies.py",
    ".\forge\domain_intelligence\database\postgres.py",
    ".\forge\domain_intelligence\database\configuration.py",
    ".\forge\domain_intelligence\database\discovery.py",
    ".\forge\domain_intelligence\database\registry.py",
    ".\forge\domain_intelligence\database\schema.py",
    ".\forge\domain_intelligence\database\constraints.py",
    ".\forge\domain_intelligence\database\indexes.py",
    ".\forge\domain_intelligence\database\relationships.py",
    ".\forge\domain_intelligence\database\queries.py",
    ".\forge\domain_intelligence\database\risk.py",
    ".\forge\domain_intelligence\database\reporting.py",
    ".\forge\domain_intelligence\database\service.py",
    ".\forge\domain_intelligence\database\cli.py"
)

$RequiredTests = @(
    ".\tests\test_domain_intelligence_database_identifiers.py",
    ".\tests\test_domain_intelligence_database_models.py",
    ".\tests\test_domain_intelligence_database_policies.py",
    ".\tests\test_domain_intelligence_database_postgres.py",
    ".\tests\test_domain_intelligence_database_configuration.py",
    ".\tests\test_domain_intelligence_database_discovery.py",
    ".\tests\test_domain_intelligence_database_registry.py",
    ".\tests\test_domain_intelligence_database_schema.py",
    ".\tests\test_domain_intelligence_database_constraints.py",
    ".\tests\test_domain_intelligence_database_indexes.py",
    ".\tests\test_domain_intelligence_database_relationships.py",
    ".\tests\test_domain_intelligence_database_queries.py",
    ".\tests\test_domain_intelligence_database_risk.py",
    ".\tests\test_domain_intelligence_database_reporting.py",
    ".\tests\test_domain_intelligence_database_service.py",
    ".\tests\test_domain_intelligence_database_cli.py"
)

$RequiredDocumentation = @(
    ".\docs\domain_intelligence\database\ARCHITECTURE.md",
    ".\docs\domain_intelligence\database\SPECIFICATION.md",
    ".\docs\domain_intelligence\database\DATA_MODEL.md",
    ".\docs\domain_intelligence\database\SECURITY_MODEL.md",
    ".\docs\domain_intelligence\database\ACCEPTANCE_CRITERIA.md"
)

foreach (
    $Path in
    $RequiredProductionFiles +
    $RequiredTests +
    $RequiredDocumentation
) {
    if (-not (Test-Path $Path -PathType Leaf)) {
        throw "Missing M4.3 architecture file: $Path"
    }

    if ((Get-Item $Path).Length -le 0) {
        throw "Empty M4.3 architecture file: $Path"
    }
}

$DatabaseCli = Get-Content `
    ".\forge\domain_intelligence\database\cli.py" `
    -Raw

if ($DatabaseCli -notmatch 'database_app\s*=\s*typer\.Typer') {
    throw "Database Typer application is missing."
}

$ForgeCli = Get-Content ".\forge\cli.py" -Raw

if (
    $ForgeCli -notmatch
    'from forge\.domain_intelligence\.database\.cli import database_app'
) {
    throw "Database CLI import is missing from forge\cli.py"
}

if (
    $ForgeCli -notmatch
    'add_typer\(database_app,\s*name="database"\)'
) {
    throw "Database CLI registration is missing from forge\cli.py"
}

Write-Host "M4.3 architecture validation passed." -ForegroundColor Green