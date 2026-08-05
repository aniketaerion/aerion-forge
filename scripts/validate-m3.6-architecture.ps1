[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$RequiredProduction = @(
    ".\forge\mission_orchestration\__init__.py",
    ".\forge\mission_orchestration\identifiers.py",
    ".\forge\mission_orchestration\models.py",
    ".\forge\mission_orchestration\errors.py",
    ".\forge\mission_orchestration\policies.py",
    ".\forge\mission_orchestration\stages.py",
    ".\forge\mission_orchestration\registry.py",
    ".\forge\mission_orchestration\workflow.py",
    ".\forge\mission_orchestration\store.py",
    ".\forge\mission_orchestration\executor.py",
    ".\forge\mission_orchestration\service.py",
    ".\forge\mission_orchestration\recovery.py",
    ".\forge\mission_orchestration\reporting.py",
    ".\forge\mission_orchestration\cli.py"
)

$RequiredTests = @(
    ".\tests\test_mission_orchestration_identifiers.py",
    ".\tests\test_mission_orchestration_models.py",
    ".\tests\test_mission_orchestration_policies.py",
    ".\tests\test_mission_orchestration_stages.py",
    ".\tests\test_mission_orchestration_registry.py",
    ".\tests\test_mission_orchestration_workflow.py",
    ".\tests\test_mission_orchestration_store.py",
    ".\tests\test_mission_orchestration_executor.py",
    ".\tests\test_mission_orchestration_service.py",
    ".\tests\test_mission_orchestration_recovery.py",
    ".\tests\test_mission_orchestration_reporting.py",
    ".\tests\test_mission_orchestration_cli.py"
)

$RequiredDocs = @(
    ".\docs\mission_orchestration\ARCHITECTURE.md",
    ".\docs\mission_orchestration\SPECIFICATION.md",
    ".\docs\mission_orchestration\DATA_MODEL.md",
    ".\docs\mission_orchestration\STATE_MACHINE.md",
    ".\docs\mission_orchestration\FAILURE_AND_RECOVERY.md",
    ".\docs\mission_orchestration\SECURITY_MODEL.md",
    ".\docs\mission_orchestration\ACCEPTANCE_CRITERIA.md"
)

foreach ($Path in $RequiredProduction + $RequiredTests + $RequiredDocs) {
    if (-not (Test-Path $Path -PathType Leaf)) {
        throw "Missing M3.6 architecture file: $Path"
    }

    if ((Get-Item $Path).Length -le 0) {
        throw "Empty M3.6 architecture file: $Path"
    }
}

$Cli = Get-Content ".\forge\cli.py" -Raw

if ($Cli -notmatch 'mission_orchestration_app') {
    throw "M3.6 CLI is not registered in forge\cli.py"
}

Write-Host "M3.6 architecture validation passed." -ForegroundColor Green