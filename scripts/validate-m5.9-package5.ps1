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
    throw "M5.9 Package 5 validation must run on an approved branch. Current: '$CurrentBranch'."
}

$Required = @(
    ".\forge\general_engineering\safe_edit_adapter.py",
    ".\forge\general_engineering\execution_policy.py",
    ".\forge\general_engineering\execution_service.py",
    ".\forge\general_engineering\execution_evidence.py",
    ".\tests\test_general_engineering_execution_policy.py",
    ".\tests\test_general_engineering_safe_edit_adapter.py",
    ".\tests\test_general_engineering_execution_service.py",
    ".\tests\test_general_engineering_execution_evidence.py"
)

foreach ($Path in $Required) {
    if (-not (Test-Path $Path)) {
        throw "Missing Package 5 file: $Path"
    }
    if ((Get-Item $Path).Length -eq 0) {
        throw "Empty Package 5 file: $Path"
    }
}

$Service = Get-Content ".\forge\general_engineering\execution_service.py" -Raw

if ($Service -notmatch "SafeCodeEditingService") {
    throw "Package 5 must execute through Safe Code Editing."
}

$ForbiddenDirectMutation = Select-String `
    -Path @(
        ".\forge\general_engineering\execution_policy.py",
        ".\forge\general_engineering\execution_service.py",
        ".\forge\general_engineering\execution_evidence.py"
    ) `
    -Pattern "write_text\(|write_bytes\(|open\(.*['`"]w|unlink\(|rmtree\(" `
    -ErrorAction SilentlyContinue

if ($ForbiddenDirectMutation) {
    $ForbiddenDirectMutation
    throw "Package 5 bypasses Safe Code Editing with direct repository mutation."
}

Write-Host ""
Write-Host "M5.9 PACKAGE 5 VALIDATION PASSED" -ForegroundColor Green
Write-Host "Execution modules: 4"
Write-Host "Focused test files: 4"
Write-Host "Mutation path: SafeCodeEditingService ONLY"