[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$RequiredProduction = @(
    ".\forge\build_verification\__init__.py",
    ".\forge\build_verification\errors.py",
    ".\forge\build_verification\identifiers.py",
    ".\forge\build_verification\models.py",
    ".\forge\build_verification\policies.py",
    ".\forge\build_verification\providers\__init__.py",
    ".\forge\build_verification\providers\base.py",
    ".\forge\build_verification\providers\python.py",
    ".\forge\build_verification\providers\node.py",
    ".\forge\build_verification\registry.py",
    ".\forge\build_verification\runner.py",
    ".\forge\build_verification\pipeline.py",
    ".\forge\build_verification\evidence.py",
    ".\forge\build_verification\decision.py",
    ".\forge\build_verification\service.py",
    ".\forge\build_verification\store.py",
    ".\forge\build_verification\reporting.py",
    ".\forge\build_verification\cli.py"
)

$RequiredTests = @(
    ".\tests\test_build_verification_identifiers.py",
    ".\tests\test_build_verification_models.py",
    ".\tests\test_build_verification_policies.py",
    ".\tests\test_build_verification_registry.py",
    ".\tests\test_build_verification_python_provider.py",
    ".\tests\test_build_verification_node_provider.py",
    ".\tests\test_build_verification_runner.py",
    ".\tests\test_build_verification_pipeline.py",
    ".\tests\test_build_verification_evidence.py",
    ".\tests\test_build_verification_decision.py",
    ".\tests\test_build_verification_service.py",
    ".\tests\test_build_verification_store.py",
    ".\tests\test_build_verification_reporting.py",
    ".\tests\test_build_verification_cli.py"
)

$RequiredDocs = @(
    ".\docs\build_verification\ARCHITECTURE.md",
    ".\docs\build_verification\SPECIFICATION.md",
    ".\docs\build_verification\DATA_MODEL.md",
    ".\docs\build_verification\SECURITY_MODEL.md",
    ".\docs\build_verification\RELEASE_GATE.md",
    ".\docs\build_verification\STATE_MACHINE.md",
    ".\docs\build_verification\ACCEPTANCE_CRITERIA.md"
)

foreach ($Path in $RequiredProduction + $RequiredTests + $RequiredDocs) {
    if (-not (Test-Path $Path -PathType Leaf)) {
        throw "Missing M3.7 architecture file: $Path"
    }

    if ((Get-Item $Path).Length -le 0) {
        throw "Empty M3.7 architecture file: $Path"
    }
}

$Cli = Get-Content ".\forge\cli.py" -Raw

if ($Cli -notmatch 'build_verification_app') {
    throw "M3.7 CLI is not registered in forge\cli.py"
}

Write-Host "M3.7 architecture validation passed." -ForegroundColor Green