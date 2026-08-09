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
if ($LASTEXITCODE -ne 0) {
    throw "Unable to read current branch."
}

if ($CurrentBranch -notin $AllowedBranches) {
    throw "M5.9 Package 1 validation must run on an approved branch: $($AllowedBranches -join ', '). Current branch: '$CurrentBranch'."
}

$RequiredFiles = @(
    ".\forge\general_engineering\normalization.py",
    ".\forge\general_engineering\requirement_extractor.py",
    ".\forge\general_engineering\request_builder.py",
    ".\forge\general_engineering\request_understanding.py",
    ".\tests\test_general_engineering_normalization.py",
    ".\tests\test_general_engineering_requirement_extractor.py",
    ".\tests\test_general_engineering_request_builder.py",
    ".\tests\test_general_engineering_request_understanding.py"
)

foreach ($Path in $RequiredFiles) {
    if (-not (Test-Path $Path)) {
        throw "Missing M5.9 Package 1 file: $Path"
    }
    if ((Get-Item $Path).Length -eq 0) {
        throw "M5.9 Package 1 file is empty: $Path"
    }
}

$Package1Core = @(
    ".\forge\general_engineering\normalization.py",
    ".\forge\general_engineering\requirement_extractor.py",
    ".\forge\general_engineering\request_builder.py",
    ".\forge\general_engineering\request_understanding.py"
)

$ForbiddenAuthority = Select-String `
    -Path $Package1Core `
    -Pattern "subprocess|os\.system|Popen|write_text\(|write_bytes\(|unlink\(|rmtree\(" `
    -ErrorAction SilentlyContinue

if ($ForbiddenAuthority) {
    $ForbiddenAuthority
    throw "M5.9 Package 1 contains forbidden execution or repository mutation authority."
}

$ForbiddenTaskSpecificLogic = Select-String `
    -Path $Package1Core `
    -Pattern "calculator|subtract|multiply|divide|PurchaseOrder|customer_service" `
    -ErrorAction SilentlyContinue

if ($ForbiddenTaskSpecificLogic) {
    $ForbiddenTaskSpecificLogic
    throw "M5.9 Package 1 contains task-specific acceptance logic."
}

$Builder = Get-Content ".\forge\general_engineering\request_builder.py" -Raw
$Understanding = Get-Content ".\forge\general_engineering\request_understanding.py" -Raw

if ($Builder -notmatch "def build_engineering_request\(") {
    throw "Package 1 request builder entrypoint is missing."
}

if ($Understanding -notmatch "class EngineeringRequestUnderstandingService") {
    throw "Package 1 request-understanding service is missing."
}

Write-Host ""
Write-Host "M5.9 PACKAGE 1 VALIDATION PASSED" -ForegroundColor Green
Write-Host "Behavior modules: 4"
Write-Host "Focused test files: 4"
Write-Host "Repository mutation authority: NONE"