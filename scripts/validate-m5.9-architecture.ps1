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
    throw "Unable to read current Git branch."
}

if ($CurrentBranch -notin $AllowedBranches) {
    throw "M5.9 architecture validation must run on an approved branch: $($AllowedBranches -join ', '). Current branch: '$CurrentBranch'."
}

git merge-base --is-ancestor forge-v0.2-m5.8 HEAD
if ($LASTEXITCODE -ne 0) {
    throw "M5.9 architecture validation requires the forge-v0.2-m5.8 release baseline."
}

$ArchitectureFiles = @(
    ".\docs\general_engineering_agent\ARCHITECTURE.md",
    ".\docs\general_engineering_agent\SPECIFICATION.md",
    ".\docs\general_engineering_agent\DATA_MODEL.md",
    ".\docs\general_engineering_agent\CHANGE_PLAN_MODEL.md",
    ".\docs\general_engineering_agent\EDIT_MODEL.md",
    ".\docs\general_engineering_agent\VALIDATION_AND_REPAIR_MODEL.md",
    ".\docs\general_engineering_agent\PROVIDER_MODEL.md",
    ".\docs\general_engineering_agent\ACCEPTANCE_CRITERIA.md",
    ".\docs\general_engineering_agent\DECISIONS.md"
)

$ContractFiles = @(
    ".\forge\general_engineering\__init__.py",
    ".\forge\general_engineering\errors.py",
    ".\forge\general_engineering\states.py",
    ".\forge\general_engineering\identifiers.py",
    ".\forge\general_engineering\models.py",
    ".\forge\general_engineering\policies.py",
    ".\forge\general_engineering\protocols.py"
)

$TestFiles = @(
    ".\tests\test_general_engineering_identifiers.py",
    ".\tests\test_general_engineering_states.py",
    ".\tests\test_general_engineering_models.py",
    ".\tests\test_general_engineering_policies.py",
    ".\tests\test_general_engineering_protocols.py"
)

foreach ($Path in $ArchitectureFiles + $ContractFiles + $TestFiles) {
    if (-not (Test-Path $Path)) {
        throw "Missing required M5.9 Package 0 file: $Path"
    }

    if ((Get-Item $Path).Length -eq 0) {
        throw "M5.9 Package 0 file is empty: $Path"
    }
}

$CoreFiles = @(
    ".\forge\general_engineering\errors.py",
    ".\forge\general_engineering\states.py",
    ".\forge\general_engineering\identifiers.py",
    ".\forge\general_engineering\models.py",
    ".\forge\general_engineering\policies.py",
    ".\forge\general_engineering\protocols.py"
)

$ForbiddenProviderDependencies = Select-String `
    -Path $CoreFiles `
    -Pattern "openai|ollama|anthropic|google\.generativeai|litellm" `
    -ErrorAction SilentlyContinue

if ($ForbiddenProviderDependencies) {
    $ForbiddenProviderDependencies
    throw "M5.9 core contracts contain provider-specific dependencies."
}

$ForbiddenExecutionAuthority = Select-String `
    -Path $CoreFiles `
    -Pattern "subprocess|os\.system|Popen|write_text\(|write_bytes\(|open\(.*['`"]w|unlink\(|rmtree\(" `
    -ErrorAction SilentlyContinue

if ($ForbiddenExecutionAuthority) {
    $ForbiddenExecutionAuthority
    throw "M5.9 core contracts contain forbidden direct execution or filesystem mutation authority."
}

$ForbiddenTaskSpecificLogic = Select-String `
    -Path $CoreFiles `
    -Pattern "calculator|subtract|multiply|divide|PurchaseOrder|customer_service" `
    -ErrorAction SilentlyContinue

if ($ForbiddenTaskSpecificLogic) {
    $ForbiddenTaskSpecificLogic
    throw "M5.9 core contracts contain acceptance-task-specific logic."
}

$ProtocolContent = Get-Content ".\forge\general_engineering\protocols.py" -Raw

foreach ($RequiredMethod in @(
    "understand_request",
    "propose_change_plan",
    "synthesize_edits",
    "propose_repair"
)) {
    if ($ProtocolContent -notmatch "def $RequiredMethod\(") {
        throw "EngineeringProvider protocol is missing '$RequiredMethod'."
    }
}

foreach ($ForbiddenMethod in @(
    "write_file",
    "run_shell",
    "approve",
    "release"
)) {
    if ($ProtocolContent -match "def $ForbiddenMethod\(") {
        throw "EngineeringProvider exposes forbidden authority: '$ForbiddenMethod'."
    }
}

$Policies = Get-Content ".\forge\general_engineering\policies.py" -Raw

if ($Policies -notmatch "max_repair_attempts.*default=3") {
    throw "M5.9 repair bound is missing from EngineeringLimits."
}

if ($Policies -notmatch "allow_direct_provider_file_writes: bool = False") {
    throw "M5.9 provider direct-write prohibition is missing."
}

if ($Policies -notmatch "allow_arbitrary_shell_execution: bool = False") {
    throw "M5.9 arbitrary shell prohibition is missing."
}

Write-Host ""
Write-Host "M5.9 ARCHITECTURE VALIDATION PASSED" -ForegroundColor Green
Write-Host "Architecture documents: $($ArchitectureFiles.Count)"
Write-Host "General engineering contract files: $($ContractFiles.Count)"
Write-Host "Package 0 focused tests: $($TestFiles.Count)"