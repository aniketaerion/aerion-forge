[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$RequiredFiles = @(
    "forge\domain_intelligence\business_domain\__init__.py",
    "forge\domain_intelligence\business_domain\cli.py",
    "forge\domain_intelligence\business_domain\crm.py",
    "forge\domain_intelligence\business_domain\entities.py",
    "forge\domain_intelligence\business_domain\erp.py",
    "forge\domain_intelligence\business_domain\errors.py",
    "forge\domain_intelligence\business_domain\identifiers.py",
    "forge\domain_intelligence\business_domain\manifest.py",
    "forge\domain_intelligence\business_domain\models.py",
    "forge\domain_intelligence\business_domain\ontology.py",
    "forge\domain_intelligence\business_domain\plugin.py",
    "forge\domain_intelligence\business_domain\policies.py",
    "forge\domain_intelligence\business_domain\registry.py",
    "forge\domain_intelligence\business_domain\reporting.py",
    "forge\domain_intelligence\business_domain\rules.py",
    "forge\domain_intelligence\business_domain\service.py",
    "forge\domain_intelligence\business_domain\workflows.py",
    "docs\domain_intelligence\business_domain\ARCHITECTURE.md",
    "docs\domain_intelligence\business_domain\SPECIFICATION.md",
    "docs\domain_intelligence\business_domain\DATA_MODEL.md",
    "docs\domain_intelligence\business_domain\SECURITY_MODEL.md",
    "docs\domain_intelligence\business_domain\ACCEPTANCE_CRITERIA.md"
)

$Missing = @($RequiredFiles | Where-Object { -not (Test-Path $_) })

if ($Missing.Count -gt 0) {
    $Missing | ForEach-Object {
        Write-Host "MISSING: $_" -ForegroundColor Red
    }
    throw "M4.5 architecture validation failed."
}

$CliContent = Get-Content ".\forge\cli.py" -Raw

if ($CliContent -notmatch 'business_domain_app') {
    throw "M4.5 CLI is not registered in forge/cli.py."
}

if ($CliContent -notmatch 'name="business-domain"') {
    throw "M4.5 business-domain command is not registered."
}

Write-Host "M4.5 architecture validation passed." -ForegroundColor Green