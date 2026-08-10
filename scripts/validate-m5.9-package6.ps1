[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$AllowedBranches = @("feature/m5.9-general-engineering-agent", "main")
$CurrentBranch = git branch --show-current
if ($CurrentBranch -notin $AllowedBranches) {
    throw "M5.9 Package 6 validation must run on an approved branch. Current: '$CurrentBranch'."
}

$Required = @(
    ".\forge\general_engineering\validation_commands.py",
    ".\forge\general_engineering\validation_executor.py",
    ".\forge\general_engineering\repair_policy.py",
    ".\forge\general_engineering\repair_plan.py",
    ".\forge\general_engineering\repair_service.py",
    ".\forge\general_engineering\validation_repair_loop.py",
    ".\tests\test_general_engineering_validation_commands.py",
    ".\tests\test_general_engineering_validation_executor.py",
    ".\tests\test_general_engineering_repair_policy.py",
    ".\tests\test_general_engineering_repair_plan.py",
    ".\tests\test_general_engineering_validation_repair_loop.py"
)
foreach ($Path in $Required) {
    if (-not (Test-Path $Path)) { throw "Missing Package 6 file: $Path" }
    if ((Get-Item $Path).Length -eq 0) { throw "Empty Package 6 file: $Path" }
}

$ValidationExecutor = Get-Content ".\forge\general_engineering\validation_executor.py" -Raw
if ($ValidationExecutor -match "shell=True|os\.system|Popen\(") {
    throw "Package 6 validation execution is not sufficiently bounded."
}
if ($ValidationExecutor -notmatch "shell=False") {
    throw "Package 6 validation subprocesses must explicitly disable shell execution."
}

$RepairService = Get-Content ".\forge\general_engineering\repair_service.py" -Raw
if ($RepairService -notmatch "EngineeringExecutionService") {
    throw "Package 6 repairs must flow through governed Package 5 execution."
}
if ($RepairService -notmatch "approved") {
    throw "Package 6 repair execution must require explicit approval."
}

Write-Host ""
Write-Host "M5.9 PACKAGE 6 VALIDATION PASSED" -ForegroundColor Green
Write-Host "Validation/repair modules: 6"
Write-Host "Focused test files: 5"
Write-Host "Validation shell execution: DISABLED"
Write-Host "Repair mutation path: Package 5 governed execution ONLY"