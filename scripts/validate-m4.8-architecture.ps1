[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$RequiredFiles = @(
    "forge\domain_intelligence\phase_validation\__init__.py",
    "forge\domain_intelligence\phase_validation\acceptance.py",
    "forge\domain_intelligence\phase_validation\architecture.py",
    "forge\domain_intelligence\phase_validation\cli.py",
    "forge\domain_intelligence\phase_validation\compatibility.py",
    "forge\domain_intelligence\phase_validation\coverage.py",
    "forge\domain_intelligence\phase_validation\errors.py",
    "forge\domain_intelligence\phase_validation\identifiers.py",
    "forge\domain_intelligence\phase_validation\models.py",
    "forge\domain_intelligence\phase_validation\policies.py",
    "forge\domain_intelligence\phase_validation\registry.py",
    "forge\domain_intelligence\phase_validation\release.py",
    "forge\domain_intelligence\phase_validation\reporting.py",
    "forge\domain_intelligence\phase_validation\service.py",
    "docs\domain_intelligence\phase_validation\ARCHITECTURE.md",
    "docs\domain_intelligence\phase_validation\SPECIFICATION.md",
    "docs\domain_intelligence\phase_validation\DATA_MODEL.md",
    "docs\domain_intelligence\phase_validation\SECURITY_MODEL.md",
    "docs\domain_intelligence\phase_validation\ACCEPTANCE_CRITERIA.md"
)

$Missing = @(
    $RequiredFiles |
        Where-Object { -not (Test-Path $_) }
)

if ($Missing.Count -gt 0) {
    $Missing | ForEach-Object {
        Write-Host "MISSING: $_" -ForegroundColor Red
    }

    throw "M4.8 architecture validation failed."
}

$CliContent = Get-Content ".\forge\cli.py" -Raw

if ($CliContent -notmatch 'phase_validation_app') {
    throw "M4.8 phase-validation CLI is not registered."
}

if ($CliContent -notmatch 'name="phase-validation"') {
    throw "M4.8 phase-validation command is not registered."
}

$ServiceContent = Get-Content `
    ".\forge\domain_intelligence\phase_validation\service.py" `
    -Raw

foreach ($RequiredSymbol in @(
    "PhaseValidationService",
    "PhaseValidationRegistry",
    "phase_validation_report_identifier"
)) {
    if ($ServiceContent -notmatch [regex]::Escape($RequiredSymbol)) {
        throw "M4.8 service is missing $RequiredSymbol."
    }
}

Write-Host "M4.8 architecture validation passed." -ForegroundColor Green