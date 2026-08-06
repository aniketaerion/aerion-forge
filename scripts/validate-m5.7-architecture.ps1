[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$RequiredFiles = @(
    ".\docs\autonomous_execution_v2\ARCHITECTURE.md",
    ".\docs\autonomous_execution_v2\SPECIFICATION.md",
    ".\docs\autonomous_execution_v2\DATA_MODEL.md",
    ".\docs\autonomous_execution_v2\STATE_MACHINE.md",
    ".\docs\autonomous_execution_v2\AUTHORITY_MODEL.md",
    ".\docs\autonomous_execution_v2\RECOVERY_MODEL.md",
    ".\docs\autonomous_execution_v2\EVIDENCE_MODEL.md",
    ".\docs\autonomous_execution_v2\ACCEPTANCE_CRITERIA.md",
    ".\forge\autonomous_execution_v2\models.py",
    ".\forge\autonomous_execution_v2\graph.py",
    ".\forge\autonomous_execution_v2\scheduler.py",
    ".\forge\autonomous_execution_v2\coordinator.py",
    ".\forge\autonomous_execution_v2\repository.py",
    ".\forge\autonomous_execution_v2\service.py",
    ".\forge\autonomous_execution_v2\reporting.py",
    ".\forge\autonomous_execution_v2\cli.py"
)

foreach ($Path in $RequiredFiles) {
    if (-not (Test-Path $Path)) {
        throw "Missing M5.7 architecture file: $Path"
    }

    if ((Get-Item $Path).Length -eq 0) {
        throw "Empty M5.7 architecture file: $Path"
    }
}

$CliContent = Get-Content ".\forge\cli.py" -Raw

if (
    -not $CliContent.Contains(
        'name="autonomous-execution-v2"'
    )
) {
    throw "M5.7 CLI registration is missing."
}

Write-Host "M5.7 architecture validation passed." `
    -ForegroundColor Green