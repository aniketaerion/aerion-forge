[CmdletBinding()]
param([string]$RepositoryRoot = (Resolve-Path ".").Path)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$RequiredFiles = @(
    "forge/safe_code_editing/__init__.py",
    "forge/safe_code_editing/errors.py",
    "forge/safe_code_editing/identifiers.py",
    "forge/safe_code_editing/models.py",
    "forge/safe_code_editing/policies.py",
    "forge/safe_code_editing/loader.py",
    "forge/safe_code_editing/operations.py",
    "forge/safe_code_editing/transaction.py",
    "forge/safe_code_editing/service.py",
    "forge/safe_code_editing/cli.py",
    "docs/safe_code_editing/ARCHITECTURE.md",
    "docs/safe_code_editing/SPECIFICATION.md",
    "docs/safe_code_editing/DATA_MODEL.md",
    "docs/safe_code_editing/SECURITY_AND_TRANSACTION_MODEL.md",
    "docs/safe_code_editing/ACCEPTANCE_CRITERIA.md"
)

foreach ($File in $RequiredFiles) {
    if (-not (Test-Path $File -PathType Leaf)) {
        throw "Missing required M3.3 file: $File"
    }
    if ((Get-Item $File).Length -eq 0) {
        throw "Empty required M3.3 file: $File"
    }
}

python -c "from forge.safe_code_editing import SafeCodeEditingService, SafeEditPolicy, SafeEditRequest"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "M3.3 architecture validation passed." -ForegroundColor Green