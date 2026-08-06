[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$RequiredMilestoneValidators = @(
    "scripts\validate-m4.1-completion.ps1",
    "scripts\validate-m4.2-completion.ps1",
    "scripts\validate-m4.3-completion.ps1",
    "scripts\validate-m4.4-completion.ps1",
    "scripts\validate-m4.5-completion.ps1",
    "scripts\validate-m4.6-completion.ps1",
    "scripts\validate-m4.7-completion.ps1",
    "scripts\validate-m4.8-completion.ps1"
)

$RequiredDomainDirectories = @(
    "forge\domain_intelligence",
    "forge\domain_intelligence\api",
    "forge\domain_intelligence\business_domain",
    "forge\domain_intelligence\database",
    "forge\domain_intelligence\embedded",
    "forge\domain_intelligence\knowledge_loader",
    "forge\domain_intelligence\phase_validation"
)

$Missing = @()

foreach ($Path in $RequiredMilestoneValidators + $RequiredDomainDirectories) {
    if (-not (Test-Path $Path)) {
        $Missing += $Path
    }
}

if ($Missing.Count -gt 0) {
    $Missing | ForEach-Object {
        Write-Host "MISSING: $_" -ForegroundColor Red
    }

    throw "Phase 4 architecture validation failed."
}

$CliContent = Get-Content ".\forge\cli.py" -Raw

foreach ($Registration in @(
    'name="api"',
    'name="business-domain"',
    'name="embedded"',
    'name="knowledge-loader"',
    'name="phase-validation"'
)) {
    if ($CliContent -notmatch [regex]::Escape($Registration)) {
        throw "Missing CLI registration: $Registration"
    }
}

$PhaseValidationService = Get-Content `
    ".\forge\domain_intelligence\phase_validation\service.py" `
    -Raw

foreach ($Symbol in @(
    "PhaseValidationService",
    "PhaseValidationRegistry",
    "phase_validation_report_identifier"
)) {
    if ($PhaseValidationService -notmatch [regex]::Escape($Symbol)) {
        throw "Phase-validation service is missing: $Symbol"
    }
}

Write-Host "Phase 4 architecture validation passed." -ForegroundColor Green
