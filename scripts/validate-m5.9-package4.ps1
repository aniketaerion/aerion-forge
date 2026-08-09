[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$AllowedBranches = @(
    "feature/m5.9-general-engineering-agent",
    "main"
)

$CurrentBranch = git branch --show-current
if ($CurrentBranch -notin $AllowedBranches) {
    throw "M5.9 Package 4 validation must run on an approved branch. Current: '$CurrentBranch'."
}

$Required = @(
    ".\forge\general_engineering\edit_synthesis_policy.py",
    ".\forge\general_engineering\edit_evidence.py",
    ".\forge\general_engineering\edit_proposal_validator.py",
    ".\forge\general_engineering\change_set_factory.py",
    ".\forge\general_engineering\edit_synthesis_service.py",
    ".\tests\test_general_engineering_edit_synthesis_policy.py",
    ".\tests\test_general_engineering_edit_evidence.py",
    ".\tests\test_general_engineering_change_set_factory.py",
    ".\tests\test_general_engineering_edit_proposal_validator.py",
    ".\tests\test_general_engineering_edit_synthesis_service.py"
)

foreach ($Path in $Required) {
    if (-not (Test-Path $Path)) {
        throw "Missing Package 4 file: $Path"
    }
    if ((Get-Item $Path).Length -eq 0) {
        throw "Empty Package 4 file: $Path"
    }
}

$Core = $Required[0..4]

$ForbiddenAuthority = Select-String `
    -Path $Core `
    -Pattern "subprocess|os\.system|Popen|write_text\(|write_bytes\(|unlink\(|rmtree\(" `
    -ErrorAction SilentlyContinue

if ($ForbiddenAuthority) {
    $ForbiddenAuthority
    throw "Package 4 contains forbidden execution or repository mutation authority."
}

$TaskSpecific = Select-String `
    -Path $Core `
    -Pattern "calculator|subtract|multiply|divide|PurchaseOrder|customer_service|shipment_service|delivery_service" `
    -ErrorAction SilentlyContinue

if ($TaskSpecific) {
    $TaskSpecific
    throw "Package 4 contains acceptance-task-specific synthesis logic."
}

$Service = Get-Content ".\forge\general_engineering\edit_synthesis_service.py" -Raw
$Validator = Get-Content ".\forge\general_engineering\edit_proposal_validator.py" -Raw

if ($Service -notmatch "provider\.synthesize_edits") {
    throw "Package 4 does not delegate reasoning to EngineeringProvider."
}

if ($Validator -notmatch "validate_generated_change_set") {
    throw "Package 4 change-set validator is missing."
}

Write-Host ""
Write-Host "M5.9 PACKAGE 4 VALIDATION PASSED" -ForegroundColor Green
Write-Host "Edit-synthesis modules: 5"
Write-Host "Focused test files: 5"
Write-Host "Repository mutation authority: NONE"