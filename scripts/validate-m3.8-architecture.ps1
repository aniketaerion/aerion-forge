[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$RequiredProduction = @(
    ".\forge\agent_runtime\__init__.py",
    ".\forge\agent_runtime\errors.py",
    ".\forge\agent_runtime\identifiers.py",
    ".\forge\agent_runtime\models.py",
    ".\forge\agent_runtime\policies.py",
    ".\forge\agent_runtime\registry.py",
    ".\forge\agent_runtime\state.py",
    ".\forge\agent_runtime\executor.py",
    ".\forge\agent_runtime\service.py",
    ".\forge\agent_runtime\store.py",
    ".\forge\agent_runtime\recovery.py",
    ".\forge\agent_runtime\reporting.py",
    ".\forge\agent_runtime\telemetry.py",
    ".\forge\agent_runtime\cli.py"
)

$RequiredTests = @(
    ".\tests\test_agent_runtime_identifiers.py",
    ".\tests\test_agent_runtime_models.py",
    ".\tests\test_agent_runtime_policies.py",
    ".\tests\test_agent_runtime_registry.py",
    ".\tests\test_agent_runtime_state.py",
    ".\tests\test_agent_runtime_executor.py",
    ".\tests\test_agent_runtime_service.py",
    ".\tests\test_agent_runtime_store.py",
    ".\tests\test_agent_runtime_recovery.py",
    ".\tests\test_agent_runtime_reporting.py",
    ".\tests\test_agent_runtime_telemetry.py",
    ".\tests\test_agent_runtime_cli.py",
    ".\tests\test_agent_runtime_end_to_end.py"
)

$RequiredDocs = @(
    ".\docs\agent_runtime\ARCHITECTURE.md",
    ".\docs\agent_runtime\SPECIFICATION.md",
    ".\docs\agent_runtime\DATA_MODEL.md",
    ".\docs\agent_runtime\STATE_MACHINE.md",
    ".\docs\agent_runtime\SECURITY_MODEL.md",
    ".\docs\agent_runtime\CAPABILITY_INTEGRATION.md",
    ".\docs\agent_runtime\ACCEPTANCE_CRITERIA.md"
)

foreach ($Path in $RequiredProduction + $RequiredTests + $RequiredDocs) {
    if (-not (Test-Path $Path -PathType Leaf)) {
        throw "Missing M3.8 architecture file: $Path"
    }

    if ((Get-Item $Path).Length -le 0) {
        throw "Empty M3.8 architecture file: $Path"
    }
}

$Cli = Get-Content ".\forge\cli.py" -Raw

if ($Cli -notmatch 'agent_app') {
    throw "M3.8 agent CLI is not registered in forge\cli.py"
}

Write-Host "M3.8 architecture validation passed." -ForegroundColor Green