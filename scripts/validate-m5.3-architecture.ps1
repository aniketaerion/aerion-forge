[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$RequiredDocs = @(
    ".\docs\autonomous_orchestration\ARCHITECTURE.md",
    ".\docs\autonomous_orchestration\SPECIFICATION.md",
    ".\docs\autonomous_orchestration\DATA_MODEL.md",
    ".\docs\autonomous_orchestration\STATE_MACHINE.md",
    ".\docs\autonomous_orchestration\STOP_MODEL.md",
    ".\docs\autonomous_orchestration\RESUME_MODEL.md",
    ".\docs\autonomous_orchestration\ACCEPTANCE_CRITERIA.md",
    ".\docs\autonomous_orchestration\DECISIONS.md"
)

$RequiredModules = @(
    ".\forge\autonomous_orchestration\models.py",
    ".\forge\autonomous_orchestration\policies.py",
    ".\forge\autonomous_orchestration\transitions.py",
    ".\forge\autonomous_orchestration\session_service.py",
    ".\forge\autonomous_orchestration\plan_loader.py",
    ".\forge\autonomous_orchestration\coordinator.py",
    ".\forge\autonomous_orchestration\iteration_service.py",
    ".\forge\autonomous_orchestration\orchestrator.py",
    ".\forge\autonomous_orchestration\reporting.py",
    ".\forge\autonomous_orchestration\cli.py"
)

foreach ($Path in @($RequiredDocs + $RequiredModules)) {
    if (-not (Test-Path $Path)) {
        throw "Required M5.3 artifact is missing: $Path"
    }

    if ((Get-Item $Path).Length -eq 0) {
        throw "Required M5.3 artifact is empty: $Path"
    }
}

$Placeholders = Get-ChildItem `
    ".\docs\autonomous_orchestration" `
    -File |
    Select-String -Pattern "_To be completed\._"

if ($Placeholders) {
    throw "M5.3 architecture documents contain placeholders."
}

Write-Host "M5.3 architecture validation passed." -ForegroundColor Green