[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

function Assert-Exists {
    param([Parameter(Mandatory)][string]$Path)

    if (-not (Test-Path $Path)) {
        throw "Missing required M5.8 artifact: $Path"
    }

    if ((Get-Item $Path).Length -eq 0) {
        throw "Required M5.8 artifact is empty: $Path"
    }
}

$ExpectedBranch = "feature/m5.8-autonomous-agent-runtime"
$CurrentBranch = git branch --show-current

if ($LASTEXITCODE -ne 0) {
    throw "Unable to read current Git branch."
}

if ($CurrentBranch -ne $ExpectedBranch) {
    throw "M5.8 architecture validation must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

$ArchitectureFiles = @(
    ".\docs\mission_runtime\ARCHITECTURE.md",
    ".\docs\mission_runtime\SPECIFICATION.md",
    ".\docs\mission_runtime\DATA_MODEL.md",
    ".\docs\mission_runtime\STATE_MACHINE.md",
    ".\docs\mission_runtime\INTEGRATION_MODEL.md",
    ".\docs\mission_runtime\APPROVAL_MODEL.md",
    ".\docs\mission_runtime\CAPABILITY_MODEL.md",
    ".\docs\mission_runtime\VERIFICATION_MODEL.md",
    ".\docs\mission_runtime\RECOVERY_MODEL.md",
    ".\docs\mission_runtime\ACCEPTANCE_CRITERIA.md",
    ".\docs\mission_runtime\DECISIONS.md"
)

$RuntimeFiles = @(
    ".\forge\mission_runtime\__init__.py",
    ".\forge\mission_runtime\errors.py",
    ".\forge\mission_runtime\states.py",
    ".\forge\mission_runtime\identifiers.py",
    ".\forge\mission_runtime\policies.py",
    ".\forge\mission_runtime\models.py",
    ".\forge\mission_runtime\context.py",
    ".\forge\mission_runtime\technology_detection.py",
    ".\forge\mission_runtime\workspace_context.py",
    ".\forge\mission_runtime\capability_resolution.py",
    ".\forge\mission_runtime\context_builder.py",
    ".\forge\mission_runtime\integration.py",
    ".\forge\mission_runtime\memory_integration.py",
    ".\forge\mission_runtime\planning_integration.py",
    ".\forge\mission_runtime\approval.py",
    ".\forge\mission_runtime\planning_orchestrator.py",
    ".\forge\mission_runtime\execution_conversion.py",
    ".\forge\mission_runtime\execution_authority.py",
    ".\forge\mission_runtime\execution_preparation.py",
    ".\forge\mission_runtime\execution_orchestrator.py",
    ".\forge\mission_runtime\verification.py",
    ".\forge\mission_runtime\state_machine.py",
    ".\forge\mission_runtime\repository.py",
    ".\forge\mission_runtime\reporting.py",
    ".\forge\mission_runtime\service.py",
    ".\forge\mission_runtime\cli.py"
)

$PackageScripts = @(
    ".\scripts\author-m5.8-architecture.ps1",
    ".\scripts\implement-m5.8-package0.ps1",
    ".\scripts\implement-m5.8-package1.ps1",
    ".\scripts\implement-m5.8-package2.ps1",
    ".\scripts\implement-m5.8-package3.ps1",
    ".\scripts\implement-m5.8-package4.ps1"
)

foreach ($Path in $ArchitectureFiles + $RuntimeFiles + $PackageScripts) {
    Assert-Exists $Path
}

$Architecture = Get-Content ".\docs\mission_runtime\ARCHITECTURE.md" -Raw
$Integration = Get-Content ".\docs\mission_runtime\INTEGRATION_MODEL.md" -Raw
$Acceptance = Get-Content ".\docs\mission_runtime\ACCEPTANCE_CRITERIA.md" -Raw
$Decisions = Get-Content ".\docs\mission_runtime\DECISIONS.md" -Raw
$RootCli = Get-Content ".\forge\cli.py" -Raw

$RequiredArchitectureTerms = @(
    "Mission Runtime",
    "repository",
    "capability",
    "planning",
    "approval",
    "execution",
    "verification",
    "recovery"
)

foreach ($Term in $RequiredArchitectureTerms) {
    if ($Architecture -notmatch [regex]::Escape($Term)) {
        throw "ARCHITECTURE.md is missing required architectural concept: $Term"
    }
}

foreach ($Term in @("M5.5", "M5.6", "M5.7")) {
    if ($Integration -notmatch [regex]::Escape($Term)) {
        throw "INTEGRATION_MODEL.md does not explicitly integrate $Term."
    }
}

if ($Decisions -notmatch "general-purpose") {
    throw "M5.8 decisions do not preserve Forge as a general-purpose engineering platform."
}

if ($Decisions -notmatch "multi-agent") {
    throw "M5.8 decisions do not explicitly defer multi-agent scope."
}

if ($Acceptance -notmatch "real external Aerion repository") {
    throw "M5.8 acceptance criteria do not require a real-project acceptance mission before v1.0."
}

if ($RootCli -notmatch 'mission_runtime_app') {
    throw "Root Forge CLI does not import the M5.8 mission runtime."
}

if ($RootCli -notmatch 'name="mission-runtime"') {
    throw "Root Forge CLI does not register the mission-runtime command group."
}

$ForbiddenRuntimeImports = Select-String `
    -Path ".\forge\mission_runtime\*.py" `
    -Pattern "from forge\.agent_runtime|from forge\.agents|multi_agent|multi-agent" `
    -ErrorAction SilentlyContinue

if ($ForbiddenRuntimeImports) {
    $ForbiddenRuntimeImports
    throw "M5.8 Mission Runtime contains forbidden multi-agent/runtime coupling."
}

Write-Host ""
Write-Host "M5.8 ARCHITECTURE VALIDATION PASSED" -ForegroundColor Green
Write-Host "Architecture documents: $($ArchitectureFiles.Count)"
Write-Host "Mission runtime modules: $($RuntimeFiles.Count)"
Write-Host "Implementation scripts: $($PackageScripts.Count)"