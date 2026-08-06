[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$RequiredDocs = @(
    ".\docs\autonomous_execution\ARCHITECTURE.md",
    ".\docs\autonomous_execution\SPECIFICATION.md",
    ".\docs\autonomous_execution\DATA_MODEL.md",
    ".\docs\autonomous_execution\STATE_MACHINE.md",
    ".\docs\autonomous_execution\TOOL_GATEWAY.md",
    ".\docs\autonomous_execution\FAILURE_MODEL.md",
    ".\docs\autonomous_execution\ACCEPTANCE_CRITERIA.md",
    ".\docs\autonomous_execution\DECISIONS.md"
)

$RequiredModules = @(
    ".\forge\autonomous_execution\models.py",
    ".\forge\autonomous_execution\policies.py",
    ".\forge\autonomous_execution\dependency_graph.py",
    ".\forge\autonomous_execution\planner.py",
    ".\forge\autonomous_execution\tool_registry.py",
    ".\forge\autonomous_execution\tool_gateway.py",
    ".\forge\autonomous_execution\execution_transitions.py",
    ".\forge\autonomous_execution\runtime.py",
    ".\forge\autonomous_execution\reporting.py",
    ".\forge\autonomous_execution\cli.py"
)

foreach ($Path in @($RequiredDocs + $RequiredModules)) {
    if (-not (Test-Path $Path)) {
        throw "Required M5.2 artifact is missing: $Path"
    }

    if ((Get-Item $Path).Length -eq 0) {
        throw "Required M5.2 artifact is empty: $Path"
    }
}

$Placeholders = Get-ChildItem `
    ".\docs\autonomous_execution" `
    -File |
    Select-String -Pattern "_To be completed\._"

if ($Placeholders) {
    throw "M5.2 architecture documents contain placeholders."
}

Write-Host "M5.2 architecture validation passed." -ForegroundColor Green