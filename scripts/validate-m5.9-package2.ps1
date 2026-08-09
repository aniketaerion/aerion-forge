[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$AllowedBranches = @("feature/m5.9-general-engineering-agent", "main")
$CurrentBranch = git branch --show-current
if ($CurrentBranch -notin $AllowedBranches) {
    throw "M5.9 Package 2 validation must run on an approved branch. Current: '$CurrentBranch'."
}

$Files = @(
    ".\forge\general_engineering\repository_scanner.py",
    ".\forge\general_engineering\symbol_discovery.py",
    ".\forge\general_engineering\relevance.py",
    ".\forge\general_engineering\context_builder.py",
    ".\forge\general_engineering\repository_grounding.py",
    ".\tests\test_general_engineering_repository_scanner.py",
    ".\tests\test_general_engineering_symbol_discovery.py",
    ".\tests\test_general_engineering_relevance.py",
    ".\tests\test_general_engineering_context_builder.py",
    ".\tests\test_general_engineering_repository_grounding.py"
)
foreach ($Path in $Files) {
    if (-not (Test-Path $Path)) { throw "Missing Package 2 file: $Path" }
    if ((Get-Item $Path).Length -eq 0) { throw "Empty Package 2 file: $Path" }
}

$Core = $Files[0..4]
$Forbidden = Select-String -Path $Core -Pattern "subprocess|os\.system|Popen|write_text\(|write_bytes\(|unlink\(|rmtree\(" -ErrorAction SilentlyContinue
if ($Forbidden) {
    $Forbidden
    throw "Package 2 contains forbidden mutation/execution authority."
}

$Specific = Select-String -Path $Core -Pattern "calculator|subtract|multiply|divide|PurchaseOrder|customer_service|shipment_service" -ErrorAction SilentlyContinue
if ($Specific) {
    $Specific
    throw "Package 2 contains task-specific acceptance logic."
}

Write-Host ""
Write-Host "M5.9 PACKAGE 2 VALIDATION PASSED" -ForegroundColor Green
Write-Host "Grounding modules: 5"
Write-Host "Focused test files: 5"
Write-Host "Repository mutation authority: NONE"