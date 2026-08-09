[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$AllowedBranches = @("feature/m5.9-general-engineering-agent", "main")
$CurrentBranch = git branch --show-current
if ($CurrentBranch -notin $AllowedBranches) {
    throw "M5.9 Package 3 validation must run on an approved branch. Current: '$CurrentBranch'."
}

$Required = @(
    ".\forge\general_engineering\planning_policy.py",
    ".\forge\general_engineering\validation_planner.py",
    ".\forge\general_engineering\change_planner.py",
    ".\forge\general_engineering\plan_validator.py",
    ".\forge\general_engineering\planning_service.py",
    ".\tests\test_general_engineering_planning_policy.py",
    ".\tests\test_general_engineering_validation_planner.py",
    ".\tests\test_general_engineering_change_planner.py",
    ".\tests\test_general_engineering_plan_validator.py",
    ".\tests\test_general_engineering_planning_service.py"
)

foreach ($Path in $Required) {
    if (-not (Test-Path $Path)) { throw "Missing Package 3 file: $Path" }
    if ((Get-Item $Path).Length -eq 0) { throw "Empty Package 3 file: $Path" }
}

$Core = $Required[0..4]
$ForbiddenAuthority = Select-String `
    -Path $Core `
    -Pattern "subprocess|os\.system|Popen|write_text\(|write_bytes\(|unlink\(|rmtree\(" `
    -ErrorAction SilentlyContinue

if ($ForbiddenAuthority) {
    $ForbiddenAuthority
    throw "Package 3 contains forbidden execution or repository mutation authority."
}

$TaskSpecific = Select-String `
    -Path $Core `
    -Pattern "calculator|subtract|multiply|divide|PurchaseOrder|customer_service|shipment_service" `
    -ErrorAction SilentlyContinue

if ($TaskSpecific) {
    $TaskSpecific
    throw "Package 3 contains acceptance-task-specific planning logic."
}

$Planner = Get-Content ".\forge\general_engineering\change_planner.py" -Raw
$Validator = Get-Content ".\forge\general_engineering\plan_validator.py" -Raw

if ($Planner -notmatch "def build_change_plan\(") {
    throw "Package 3 change-plan builder is missing."
}
if ($Validator -notmatch "def validate_change_plan\(") {
    throw "Package 3 plan validator is missing."
}

Write-Host ""
Write-Host "M5.9 PACKAGE 3 VALIDATION PASSED" -ForegroundColor Green
Write-Host "Planning modules: 5"
Write-Host "Focused test files: 5"
Write-Host "Repository mutation authority: NONE"