[CmdletBinding()]
param([string]$RepositoryRoot = (Resolve-Path ".").Path)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$RequiredFiles = @(
    "forge/autonomous_repair/__init__.py",
    "forge/autonomous_repair/errors.py",
    "forge/autonomous_repair/identifiers.py",
    "forge/autonomous_repair/models.py",
    "forge/autonomous_repair/policies.py",
    "forge/autonomous_repair/registry.py",
    "forge/autonomous_repair/state.py",
    "forge/autonomous_repair/executor.py",
    "forge/autonomous_repair/service.py",
    "forge/autonomous_repair/reporting.py",
    "forge/autonomous_repair/cli.py",
    "forge/autonomous_repair/providers/__init__.py",
    "forge/autonomous_repair/providers/base.py",
    "forge/autonomous_repair/providers/exact_patch.py",
    "forge/autonomous_repair/providers/ruff_fix.py",
    "docs/autonomous_repair/ARCHITECTURE.md",
    "docs/autonomous_repair/SPECIFICATION.md",
    "docs/autonomous_repair/DATA_MODEL.md",
    "docs/autonomous_repair/PROVIDER_CONTRACT.md",
    "docs/autonomous_repair/SECURITY_MODEL.md",
    "docs/autonomous_repair/STATE_MACHINE.md",
    "docs/autonomous_repair/ACCEPTANCE_CRITERIA.md"
)

foreach ($File in $RequiredFiles) {
    if (-not (Test-Path $File -PathType Leaf)) {
        throw "Missing required M3.5 file: $File"
    }
    if ((Get-Item $File).Length -eq 0) {
        throw "Empty required M3.5 file: $File"
    }
}

python -c "from forge.autonomous_repair import AutonomousRepairPolicy, RepairInput, RepairExecutionSession"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "M3.5 architecture validation passed." -ForegroundColor Green