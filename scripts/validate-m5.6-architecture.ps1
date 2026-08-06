[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$RequiredModules = @(
    ".\forge\autonomous_planning\__init__.py",
    ".\forge\autonomous_planning\models.py",
    ".\forge\autonomous_planning\policies.py",
    ".\forge\autonomous_planning\graph.py",
    ".\forge\autonomous_planning\graph_builder.py",
    ".\forge\autonomous_planning\analysis.py",
    ".\forge\autonomous_planning\step_synthesis.py",
    ".\forge\autonomous_planning\plan_generation.py",
    ".\forge\autonomous_planning\validation.py",
    ".\forge\autonomous_planning\approval.py",
    ".\forge\autonomous_planning\repository.py",
    ".\forge\autonomous_planning\service.py",
    ".\forge\autonomous_planning\reporting.py",
    ".\forge\autonomous_planning\cli.py"
)

foreach ($Path in $RequiredModules) {
    if (-not (Test-Path $Path)) {
        throw "Missing M5.6 module: $Path"
    }

    if ((Get-Item $Path).Length -eq 0) {
        throw "Empty M5.6 module: $Path"
    }
}

Write-Host "M5.6 architecture validation passed." `
    -ForegroundColor Green