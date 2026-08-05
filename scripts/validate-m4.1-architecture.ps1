[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$RequiredProductionFiles = @(
    ".\forge\domain_intelligence\errors.py",
    ".\forge\domain_intelligence\identifiers.py",
    ".\forge\domain_intelligence\models.py",
    ".\forge\domain_intelligence\policies.py",
    ".\forge\domain_intelligence\frontend\__init__.py",
    ".\forge\domain_intelligence\frontend\react.py",
    ".\forge\domain_intelligence\frontend\vite.py",
    ".\forge\domain_intelligence\frontend\nextjs.py",
    ".\forge\domain_intelligence\frontend\registry.py",
    ".\forge\domain_intelligence\frontend\components.py",
    ".\forge\domain_intelligence\frontend\routing.py",
    ".\forge\domain_intelligence\frontend\hooks.py",
    ".\forge\domain_intelligence\frontend\state_management.py",
    ".\forge\domain_intelligence\frontend\styling.py",
    ".\forge\domain_intelligence\frontend\service.py",
    ".\forge\domain_intelligence\frontend\reporting.py",
    ".\forge\domain_intelligence\frontend\cli.py"
)

$RequiredTests = @(
    ".\tests\test_domain_intelligence_identifiers.py",
    ".\tests\test_domain_intelligence_models.py",
    ".\tests\test_domain_intelligence_policies.py",
    ".\tests\test_domain_intelligence_frontend_react.py",
    ".\tests\test_domain_intelligence_frontend_vite.py",
    ".\tests\test_domain_intelligence_frontend_nextjs.py",
    ".\tests\test_domain_intelligence_frontend_registry.py",
    ".\tests\test_domain_intelligence_frontend_components.py",
    ".\tests\test_domain_intelligence_frontend_routing.py",
    ".\tests\test_domain_intelligence_frontend_hooks.py",
    ".\tests\test_domain_intelligence_frontend_state_management.py",
    ".\tests\test_domain_intelligence_frontend_styling.py",
    ".\tests\test_domain_intelligence_frontend_service.py",
    ".\tests\test_domain_intelligence_frontend_reporting.py",
    ".\tests\test_domain_intelligence_frontend_cli.py"
)

$RequiredDocumentation = @(
    ".\docs\domain_intelligence\ARCHITECTURE.md",
    ".\docs\domain_intelligence\SPECIFICATION.md",
    ".\docs\domain_intelligence\DATA_MODEL.md",
    ".\docs\domain_intelligence\SECURITY_MODEL.md",
    ".\docs\domain_intelligence\ACCEPTANCE_CRITERIA.md",
    ".\docs\domain_intelligence\frontend\ARCHITECTURE.md",
    ".\docs\domain_intelligence\frontend\SPECIFICATION.md",
    ".\docs\domain_intelligence\frontend\DATA_MODEL.md",
    ".\docs\domain_intelligence\frontend\SECURITY_MODEL.md",
    ".\docs\domain_intelligence\frontend\ACCEPTANCE_CRITERIA.md"
)

foreach (
    $Path in
    $RequiredProductionFiles +
    $RequiredTests +
    $RequiredDocumentation
) {
    if (-not (Test-Path $Path -PathType Leaf)) {
        throw "Missing M4.1 architecture file: $Path"
    }

    if ((Get-Item $Path).Length -le 0) {
        throw "Empty M4.1 architecture file: $Path"
    }
}

$FrontendCli = Get-Content `
    ".\forge\domain_intelligence\frontend\cli.py" `
    -Raw

if ($FrontendCli -notmatch 'frontend_app\s*=\s*typer\.Typer') {
    throw "Frontend Typer application is missing."
}

$ForgeCli = Get-Content ".\forge\cli.py" -Raw

if (
    $ForgeCli -notmatch
    'from forge\.domain_intelligence\.frontend\.cli import frontend_app'
) {
    throw "Frontend CLI import is missing from forge\cli.py"
}

if (
    $ForgeCli -notmatch
    'add_typer\(frontend_app,\s*name="frontend"\)'
) {
    throw "Frontend CLI registration is missing from forge\cli.py"
}

Write-Host "M4.1 architecture validation passed." -ForegroundColor Green