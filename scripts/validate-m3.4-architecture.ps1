[CmdletBinding()]
param([string]$RepositoryRoot = (Resolve-Path ".").Path)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$RequiredFiles = @(
    "forge/validation_repair/__init__.py",
    "forge/validation_repair/errors.py",
    "forge/validation_repair/identifiers.py",
    "forge/validation_repair/models.py",
    "forge/validation_repair/policies.py",
    "forge/validation_repair/parser.py",
    "forge/validation_repair/runner.py",
    "forge/validation_repair/planner.py",
    "forge/validation_repair/service.py",
    "forge/validation_repair/cli.py",
    "docs/validation_repair/ARCHITECTURE.md",
    "docs/validation_repair/SPECIFICATION.md",
    "docs/validation_repair/DATA_MODEL.md",
    "docs/validation_repair/OPERATIONS.md",
    "docs/validation_repair/ACCEPTANCE_CRITERIA.md"
)

foreach ($File in $RequiredFiles) {
    if (-not (Test-Path $File -PathType Leaf)) {
        throw "Missing required M3.4 file: $File"
    }
    if ((Get-Item $File).Length -eq 0) {
        throw "Empty required M3.4 file: $File"
    }
}

python -c "from forge.validation_repair import ValidationRepairPolicy, ValidationCommand, RepairSession"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "M3.4 architecture validation passed." -ForegroundColor Green